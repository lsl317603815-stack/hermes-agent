"""Regression tests for ``gateway.status.pid_alive`` on Windows.

Before the fix, ``pid_alive`` probed liveness with ``OpenProcess`` alone.
On Windows, a process's kernel Process object can outlive the actual
process whenever any other process still holds a HANDLE to it.
``OpenProcess`` succeeds on such zombie kobjs, so ``pid_alive`` would
falsely report long-dead PIDs as alive — the exact mechanism behind
the "Another local Hermes gateway is already using this Feishu app_id
(PID 84776)" stall observed after a Ctrl+C exit: the scoped lock file
pointed at the old PID, the kobj lingered because the parent shell
still held a handle, and ``pid_alive`` said "still alive → refuse to
acquire".

The fix pairs ``OpenProcess`` with ``GetExitCodeProcess`` and reports
dead unless the exit code is ``STILL_ACTIVE`` (259).
"""

import os
import subprocess
import sys

import pytest


@pytest.fixture
def zombie_kobj_pid():
    """Spawn a child that exits immediately and keep its kobj alive.

    ``subprocess.Popen`` retains the Windows process HANDLE in
    ``proc._handle`` across ``wait()``; the handle is not released until
    the Popen object is garbage-collected.  That means the child's PID
    still "exists" to ``OpenProcess`` even though the process itself is
    long gone — precisely the failure mode we need to cover.
    """
    if sys.platform != "win32":
        pytest.skip("zombie-kobj behavior is Windows-specific")
    proc = subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.exit(0)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proc.wait()
    assert proc.returncode is not None, "child must have exited before the test runs"
    try:
        yield proc.pid
    finally:
        # Dropping the reference lets Windows free the kobj.  Explicit
        # del makes the ordering unambiguous across GC implementations.
        del proc


class TestPidAliveZombieKobj:
    """Zombie kernel objects must not be mistaken for live processes."""

    def test_exited_child_with_held_handle_reported_dead(self, zombie_kobj_pid):
        from gateway.status import pid_alive

        assert pid_alive(zombie_kobj_pid) is False, (
            "pid_alive must detect that the zombie kobj's underlying process "
            "has exited — the scoped-lock false-acquire bug depends on this."
        )

    def test_treat_permission_as_alive_does_not_rescue_zombie(self, zombie_kobj_pid):
        from gateway.status import pid_alive

        # OpenProcess succeeds on the zombie, so the
        # treat_permission_as_alive branch (only consulted on
        # ACCESS_DENIED) never fires.  The exit-code check must still
        # correctly classify the zombie as dead.
        assert pid_alive(zombie_kobj_pid, treat_permission_as_alive=True) is False


class TestPidAliveLiveProcess:
    """Liveness detection must still work for actually-running processes."""

    def test_own_process_reported_alive(self):
        from gateway.status import pid_alive

        assert pid_alive(os.getpid()) is True

    def test_long_running_child_reported_alive(self):
        """Spawn a child that sleeps, confirm it's reported alive, then kill."""
        if sys.platform != "win32":
            pytest.skip("Windows-specific probe")
        from gateway.status import pid_alive

        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            assert pid_alive(proc.pid) is True
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
