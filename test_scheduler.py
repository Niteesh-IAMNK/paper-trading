import time

from shared.scheduler import (
    RepeatedTask
)


def say_hello():
    print(
        "Running strategy..."
    )


task = RepeatedTask(
    2,
    say_hello
)

task.start()

time.sleep(10)

task.stop()