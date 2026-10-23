"""Standalone document-processing worker, for production.

    uv run python -m app.worker

Set RUN_WORKER_IN_API=false on the API when running this. Several workers can run at once:
job claiming uses SELECT ... FOR UPDATE SKIP LOCKED, so no job is processed twice.
"""

import logging
import signal
import threading

from app.services.processing import run_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())  # finish the current job, then exit
    run_worker(stop)


if __name__ == "__main__":
    main()
