import time

from shared.scheduler import (
    RepeatedTask
)

from shared.live_market_service import (
    update_market
)

market_task = RepeatedTask(
    interval_seconds=5,
    function=update_market
)

market_task.start()

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    market_task.stop()
    print("Stopped.")