
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

    os.environ["HOME"] = user.pw_dir


def wait_for_port(port, timeout=90):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                logger.info("HTTP server port %s is listening", port)
                return True
        except OSError:
            time.sleep(2)

    logger.error("No HTTP server became available on port %s", port)
    return False


def main():
    global shutdown_signal

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    processes = []

    specs = [
        ("supervisord", [
            "/usr/bin/supervisord", "-n",
            "-c", "/etc/supervisor/supervisord.conf"
        ]),
        ("celery-worker-1", [
            "/usr/local/bin/celery", "-A", "config",
            "worker", "--loglevel=info",
            "--concurrency=2", "--hostname=worker1@%h"
        ]),
        ("celery-worker-2", [
            "/usr/local/bin/celery", "-A", "config",
            "worker", "--loglevel=info",
            "--concurrency=2", "--hostname=worker2@%h"
        ]),
        ("celery-beat", [
            "/usr/local/bin/celery", "-A", "config",
            "beat", "--loglevel=info",
            "--schedule=/var/lib/celerybeat/celerybeat-schedule"
        ]),
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

        port = int(os.environ.get("PORT", "10000"))

        if not wait_for_port(port):
            exit_code = 1
            return exit_code

        while shutdown_signal is None:
            for name, process in processes:
                status = process.poll()

                if status is not None:
                    logger.error(
                        "%s exited unexpectedly: %s", name, status
                    )
                    exit_code = status if status > 0 else 1
                    shutdown_signal = signal.SIGTERM
                    break

            time.sleep(1)

    except Exception:
        logger.exception("Container startup failed")
        exit_code = 1

    finally:
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

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
