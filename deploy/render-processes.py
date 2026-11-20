import logging
import os
import pwd
import signal
import socket
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("render-processes")

shutdown_signal = None


def request_shutdown(signum, _frame):
    global shutdown_signal
    shutdown_signal = signum


def drop_privileges():
    user = pwd.getpwnam("app")

    if os.geteuid() == 0:
        os.initgroups(user.pw_name, user.pw_gid)
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
    elif os.geteuid() != user.pw_uid:
        raise PermissionError("Process launcher must run as root or app.")

    os.environ["HOME"] = user.pw_dir

    logger.info(
        "Running processes as app (uid=%s gid=%s)",
        user.pw_uid,
        user.pw_gid,
    )


def print_diagnostic_logs():
    paths = (
        "/tmp/nginx-error.log",
        "/tmp/nginx-supervisor.log",
        "/tmp/supervisord.log",
    )

    for path in paths:
        if not os.path.exists(path):
            continue

        try:
            with open(path, "r", errors="replace") as log_file:
                content = log_file.read()

            logger.error("%s:\n%s", path, content[-12000:])

        except OSError:
            logger.exception("Could not read %s", path)


def wait_for_port(port, processes, timeout=90):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        for name, process in processes:
            status = process.poll()

            if status is not None:
                logger.error(
                    "%s exited during startup with status %s",
                    name,
                    status,
                )
                print_diagnostic_logs()
                return False

        try:
            with socket.create_connection(
                ("127.0.0.1", port),
                timeout=2,
            ):
                logger.info(
                    "HTTP server port %s is listening",
                    port,
                )
                return True

        except OSError:
            time.sleep(2)

    logger.error(
        "No HTTP server became available on port %s",
        port,
    )

    print_diagnostic_logs()

    return False


def stop_processes(processes):
    for name, process in reversed(processes):
        if process.poll() is None:
            logger.info("Stopping %s", name)

            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    for name, process in reversed(processes):
        try:
            process.wait(timeout=15)

        except subprocess.TimeoutExpired:
            logger.warning("Force stopping %s", name)

            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

            process.wait()


def main():
    global shutdown_signal

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    processes = []

    specs = [
        (
            "supervisord",
            [
                "/usr/bin/supervisord",
                "-n",
                "-c",
                "/etc/supervisor/supervisord.conf",
            ],
        ),
    ]

    exit_code = 0

    try:
        drop_privileges()

        for name, command in specs:
            logger.info("Starting %s", name)

            process = subprocess.Popen(
                command,
                cwd="/app/backend",
                start_new_session=True,
            )

            processes.append((name, process))

            logger.info(
                "Started %s with PID %s",
                name,
                process.pid,
            )

        port = int(os.environ.get("PORT", "10000"))

        if not wait_for_port(port, processes):
            exit_code = 1
            return exit_code

        logger.info("All startup checks passed.")

        while shutdown_signal is None:
            for name, process in processes:
                status = process.poll()

                if status is not None:
                    logger.error(
                        "%s exited unexpectedly with status %s",
                        name,
                        status,
                    )

                    exit_code = status if status > 0 else 1
                    shutdown_signal = signal.SIGTERM
                    break

            time.sleep(1)

    except Exception:
        logger.exception("Container startup failed")
        exit_code = 1

    finally:
        if shutdown_signal is not None:
            logger.info(
                "Received shutdown signal %s",
                shutdown_signal,
            )

        stop_processes(processes)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
