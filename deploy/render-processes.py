import logging
import os
import pwd
import signal
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


def _request_shutdown(signum, _frame):
    global shutdown_signal
    shutdown_signal = signum


def _start_processes(processes):
    specs = (
        (
            "supervisord",
            ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"],
        ),
        (
            "celery-worker-1",
            [
                "/usr/local/bin/celery",
                "-A",
                "config",
                "worker",
                "--loglevel=info",
                "--concurrency=2",
                "--hostname=worker1@%h",
            ],
        ),
        (
            "celery-worker-2",
            [
                "/usr/local/bin/celery",
                "-A",
                "config",
                "worker",
                "--loglevel=info",
                "--concurrency=2",
                "--hostname=worker2@%h",
            ],
        ),
        (
            "celery-beat",
            [
                "/usr/local/bin/celery",
                "-A",
                "config",
                "beat",
                "--loglevel=info",
                "--schedule=/var/lib/celerybeat/celerybeat-schedule",
            ],
        ),
    )
    for name, command in specs:
        if shutdown_signal is not None:
            break
        options = {
            "cwd": "/app/backend",
            "start_new_session": True,
        }
        logger.info("Starting %s", name)
        process = subprocess.Popen(command, **options)
        processes.append((name, process))
        logger.info("Started %s with pid %s", name, process.pid)


def _drop_privileges():
    app_user = pwd.getpwnam("app")
    if os.geteuid() == 0:
        os.initgroups(app_user.pw_name, app_user.pw_gid)
        os.setgid(app_user.pw_gid)
        os.setuid(app_user.pw_uid)
    elif os.geteuid() != app_user.pw_uid:
        raise PermissionError("The container launcher must run as root or app.")
    os.environ["HOME"] = app_user.pw_dir
    logger.info(
        "Running managed processes as app (uid=%s gid=%s)",
        app_user.pw_uid,
        app_user.pw_gid,
    )


def _stop_processes(processes):
    for name, process in reversed(processes):
        if process.poll() is None:
            logger.info("Stopping %s", name)
            process.terminate()
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    deadline = time.monotonic() + 60
    for name, process in reversed(processes):
        if process.poll() is not None:
            continue
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            logger.error("%s did not stop gracefully; terminating it", name)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                process.kill()
            process.wait()


def main():
    global shutdown_signal
    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)
    processes = []
    exit_code = 0
    try:
        _drop_privileges()
        _start_processes(processes)
        while shutdown_signal is None:
            for name, process in processes:
                status = process.poll()
                if status is not None:
                    logger.error("%s exited unexpectedly with status %s", name, status)
                    exit_code = status if status > 0 else 1
                    shutdown_signal = signal.SIGTERM
                    break
            time.sleep(0.5)
    except OSError:
        logger.exception("Could not start a managed process")
        exit_code = 1
    finally:
        if shutdown_signal is not None:
            logger.info("Received shutdown signal %s", shutdown_signal)
        _stop_processes(processes)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
