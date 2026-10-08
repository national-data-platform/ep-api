# api/tasks/leader.py
"""
One worker per Endpoint does the work that must happen once per Endpoint.

The image runs several uvicorn workers in one container, and each of them runs
the FastAPI lifespan. Work started there ran once per worker: every Endpoint
sent four identical metric reports per interval, and four workers raced to
create the ``services`` organization at startup (issue #309).

The worker that holds an exclusive lock on a file in the container's temporary
directory is the leader. The lock belongs to the process, so it is released
when that worker stops, however it stops, and a waiting worker takes over.
"""

import asyncio
import logging
import os
import tempfile
from typing import Awaitable, Callable, Optional

try:
    import fcntl
except ImportError:  # Windows: no flock, and no multi-worker container either
    fcntl = None

logger = logging.getLogger(__name__)

LOCK_PATH = os.path.join(tempfile.gettempdir(), "ndp-ep-leader.lock")
TAKEOVER_POLL_SECONDS = 30


class LeaderLock:
    """A non-blocking, process-wide exclusive lock on a file."""

    def __init__(self, path: str = LOCK_PATH):
        self.path = path
        self._fd: Optional[int] = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def try_acquire(self) -> bool:
        """Take the lock if nobody holds it. Never blocks."""
        if self._fd is not None:
            return True
        if fcntl is None:
            # Without flock there is nothing to coordinate with: this is a
            # single-process development run, which is its own leader.
            self._fd = -1
            return True

        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        if self._fd >= 0:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
        self._fd = None


async def lead_when_possible(
    lock: LeaderLock,
    work: Callable[[], Awaitable[None]],
    poll_seconds: float = TAKEOVER_POLL_SECONDS,
) -> None:
    """Wait until this worker becomes the leader, then run ``work``."""
    while not lock.try_acquire():
        await asyncio.sleep(poll_seconds)
    logger.info("This worker took over as leader (pid %s)", os.getpid())
    await work()
