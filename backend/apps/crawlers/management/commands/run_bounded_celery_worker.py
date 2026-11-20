import os
import signal
import threading

from celery.signals import task_postrun, task_received, worker_ready
from django.core.management.base import BaseCommand, CommandError

from config.celery import app

TASK_POSTRUN_UID = "nepse-bounded-worker-task-postrun"
TASK_RECEIVED_UID = "nepse-bounded-worker-task-received"
WORKER_READY_UID = "nepse-bounded-worker-ready"


class Command(BaseCommand):
    help = "Run a concurrency-one Celery worker with task and time limits."

    def add_arguments(self, parser):
        parser.add_argument("--max-tasks", type=int, default=5)
        parser.add_argument("--max-seconds", type=int, default=300)
        parser.add_argument("--idle-seconds", type=int, default=30)

    def handle(self, *args, **options):
        if os.name != "posix" or not hasattr(signal, "SIGUSR1"):
            raise CommandError(
                "The bounded worker requires a POSIX host such as GitHub Actions."
            )

        max_tasks = options["max_tasks"]
        max_seconds = options["max_seconds"]
        idle_seconds = options["idle_seconds"]
        if not 1 <= max_tasks <= 20:
            raise CommandError("--max-tasks must be between 1 and 20.")
        if not 10 <= max_seconds <= 600:
            raise CommandError("--max-seconds must be between 10 and 600.")
        if not 1 <= idle_seconds <= 120:
            raise CommandError("--idle-seconds must be between 1 and 120.")

        worker = app.Worker(
            concurrency=1,
            pool="prefork",
            queues=("celery",),
            loglevel="INFO",
            hostname="nepse-bounded@%h",
            without_gossip=True,
            without_mingle=True,
            without_heartbeat=True,
            soft_time_limit=min(150, max_seconds - 5),
            time_limit=min(180, max_seconds),
        )
        parent_pid = os.getpid()
        completed_tasks = 0
        idle_timer = None

        def request_shutdown():
            try:
                os.kill(parent_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        def reset_idle_timer(*_args, **_kwargs):
            nonlocal idle_timer
            if idle_timer is not None:
                idle_timer.cancel()
            idle_timer = threading.Timer(idle_seconds, request_shutdown)
            idle_timer.daemon = True
            idle_timer.start()

        def record_completed_task(_signum, _frame):
            nonlocal completed_tasks
            completed_tasks += 1
            if completed_tasks >= max_tasks:
                request_shutdown()
            else:
                reset_idle_timer()

        def count_task_after_run(sender=None, **_kwargs):
            if sender is not None and os.getpid() != parent_pid:
                os.kill(os.getppid(), signal.SIGUSR1)

        def note_received_task(**_kwargs):
            reset_idle_timer()

        previous_usr1_handler = signal.getsignal(signal.SIGUSR1)
        signal.signal(signal.SIGUSR1, record_completed_task)
        task_postrun.connect(
            count_task_after_run,
            weak=False,
            dispatch_uid=TASK_POSTRUN_UID,
        )
        task_received.connect(
            note_received_task,
            weak=False,
            dispatch_uid=TASK_RECEIVED_UID,
        )
        worker_ready.connect(
            reset_idle_timer,
            weak=False,
            dispatch_uid=WORKER_READY_UID,
        )
        runtime_timer = threading.Timer(max_seconds, request_shutdown)
        runtime_timer.daemon = True
        runtime_timer.start()

        self.stdout.write(
            f"Starting bounded Celery worker: concurrency=1, queue=celery, "
            f"max_tasks={max_tasks}, max_seconds={max_seconds}, "
            f"idle_seconds={idle_seconds}."
        )
        try:
            worker.start()
        finally:
            runtime_timer.cancel()
            if idle_timer is not None:
                idle_timer.cancel()
            task_postrun.disconnect(dispatch_uid=TASK_POSTRUN_UID)
            task_received.disconnect(dispatch_uid=TASK_RECEIVED_UID)
            worker_ready.disconnect(dispatch_uid=WORKER_READY_UID)
            signal.signal(signal.SIGUSR1, previous_usr1_handler)
