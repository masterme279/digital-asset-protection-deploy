from __future__ import annotations

from queue import Empty, Queue

from ai_pipeline.platform.models import IngestionJob


class JobQueue:
    def __init__(self) -> None:
        self._queue: Queue[IngestionJob] = Queue()

    def put(self, job: IngestionJob) -> None:
        self._queue.put(job)

    def get(self, timeout: float = 0.5) -> IngestionJob:
        return self._queue.get(timeout=timeout)

    def task_done(self) -> None:
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()

    def get_nowait(self) -> IngestionJob:
        return self._queue.get_nowait()

    def drain(self) -> int:
        count = 0
        while True:
            try:
                self.get_nowait()
                self.task_done()
                count += 1
            except Empty:
                break
        return count
