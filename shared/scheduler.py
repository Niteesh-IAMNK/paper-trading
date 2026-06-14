import threading
import time

from .logger import (
    log_info,
    log_error
)


class RepeatedTask:
    """
    Runs a function repeatedly
    at a fixed interval.
    """

    def __init__(
        self,
        interval_seconds,
        function,
        *args,
        **kwargs
    ):
        self.interval = interval_seconds
        self.function = function
        self.args = args
        self.kwargs = kwargs

        self.running = False
        self.thread = None

    def _run(self):
        while self.running:
            try:
                self.function(
                    *self.args,
                    **self.kwargs
                )

            except Exception as e:
                log_error(
                    f"Scheduler error: {e}"
                )

            time.sleep(
                self.interval
            )

    def start(self):
        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.thread.start()

        log_info(
            f"Started task every "
            f"{self.interval} seconds."
        )

    def stop(self):
        self.running = False

        log_info(
            "Task stopped."
        )