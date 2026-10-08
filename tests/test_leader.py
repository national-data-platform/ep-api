"""
Only one worker runs the once-per-Endpoint work (issue #309).

The image runs several uvicorn workers and every one of them ran the lifespan,
so each Endpoint sent four metric reports per interval and four workers raced
to create the ``services`` organization. ``LeaderLock`` lets exactly one
process hold the role; these tests check that a second holder is refused, that
the role passes on when the holder goes away, and that a waiting worker starts
the work once it becomes the leader.
"""

import asyncio
import os
import subprocess
import sys
import textwrap

import pytest

from api.tasks import leader as leader_module
from api.tasks.leader import LeaderLock, lead_when_possible

pytestmark = pytest.mark.skipif(
    leader_module.fcntl is None, reason="flock is POSIX-only"
)


@pytest.fixture
def lock_path(tmp_path):
    return str(tmp_path / "leader.lock")


def test_only_one_holder_at_a_time(lock_path):
    first, second = LeaderLock(lock_path), LeaderLock(lock_path)

    assert first.try_acquire()
    assert not second.try_acquire()

    first.release()
    assert second.try_acquire()
    second.release()


def test_acquiring_twice_from_the_same_holder_is_harmless(lock_path):
    lock = LeaderLock(lock_path)

    assert lock.try_acquire()
    assert lock.try_acquire()
    assert lock.held
    lock.release()
    assert not lock.held


def test_the_lock_is_released_when_the_holding_process_exits(lock_path):
    """A worker that dies, however it dies, frees the role for the others."""
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            textwrap.dedent(f"""
                import sys, time
                from api.tasks.leader import LeaderLock
                assert LeaderLock({lock_path!r}).try_acquire()
                print("held", flush=True)
                time.sleep(60)
                """),
        ],
        stdout=subprocess.PIPE,
        text=True,
        cwd=os.getcwd(),
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        assert not LeaderLock(lock_path).try_acquire()
    finally:
        holder.kill()
        holder.wait()

    survivor = LeaderLock(lock_path)
    assert survivor.try_acquire()
    survivor.release()


def test_a_waiting_worker_starts_the_work_once_it_becomes_leader(lock_path):
    current, waiting = LeaderLock(lock_path), LeaderLock(lock_path)
    assert current.try_acquire()
    runs = []

    async def work():
        runs.append("ran")

    async def scenario():
        task = asyncio.create_task(lead_when_possible(waiting, work, 0.01))
        await asyncio.sleep(0.05)
        assert runs == []  # still waiting while another worker leads
        current.release()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(scenario())

    assert runs == ["ran"]
    assert waiting.held
    waiting.release()


def test_four_workers_elect_exactly_one_leader(lock_path):
    """What happens in the container: four processes start at once."""
    script = textwrap.dedent(f"""
        import time
        from api.tasks.leader import LeaderLock
        lock = LeaderLock({lock_path!r})
        print("leader" if lock.try_acquire() else "follower", flush=True)
        time.sleep(5)
        """)
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            text=True,
            cwd=os.getcwd(),
        )
        for _ in range(4)
    ]
    roles = [w.communicate(timeout=30)[0].strip() for w in workers]

    assert sorted(roles) == ["follower", "follower", "follower", "leader"]


def test_two_workers_start_the_metrics_loop_once(lock_path, monkeypatch):
    """The lifespan in api.main only starts the loop in the leader."""
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient

    import api.main as main

    started = AsyncMock()
    monkeypatch.setattr(main, "record_system_metrics", started)
    monkeypatch.setattr(main, "ensure_services_organization", lambda: None)
    monkeypatch.setattr(
        main, "LeaderLock", lambda: LeaderLock(lock_path), raising=False
    )

    with TestClient(main.app), TestClient(main.app):
        pass

    assert started.await_count == 1
