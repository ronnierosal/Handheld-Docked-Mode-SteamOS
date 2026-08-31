"""Narrow POSIX signal adapter for future approved process release.

The Decky plugin does not construct or expose this adapter.  The application
must consume an approval and freshly revalidate the target before every call.
"""

from __future__ import annotations

import os
import signal
from collections.abc import Callable

from ...domain.process_release import ProcessReleaseTarget
from ...ports.process_signal import (
    ProcessSignalAction,
    ProcessSignalResult,
)


class PosixProcessSignalAdapter:
    def __init__(
        self,
        kill: Callable[[int, int], None] = os.kill,
        platform_name: str = os.name,
    ) -> None:
        self._kill = kill
        self._platform_name = platform_name

    def signal(
        self, target: ProcessReleaseTarget, action: ProcessSignalAction
    ) -> ProcessSignalResult:
        if self._platform_name != "posix":
            return ProcessSignalResult(False, "signal.platform_unsupported")
        signal_number = {
            ProcessSignalAction.GRACEFUL_TERMINATE: int(
                getattr(signal, "SIGTERM", 15)
            ),
            ProcessSignalAction.FORCE_TERMINATE: int(
                getattr(signal, "SIGKILL", 9)
            ),
        }[action]
        try:
            self._kill(target.pid, signal_number)
        except ProcessLookupError:
            return ProcessSignalResult(True, "signal.process_absent")
        except PermissionError:
            return ProcessSignalResult(False, "signal.permission_denied")
        except OSError:
            return ProcessSignalResult(False, "signal.os_error")
        return ProcessSignalResult(True, "signal.accepted")
