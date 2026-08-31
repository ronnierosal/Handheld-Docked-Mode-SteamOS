"""Constrained subprocess execution for read-only discovery commands."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True, slots=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.error


class ReadOnlyCommandRunner:
    """Run a small allowlist without a shell or mutation-shaped arguments."""

    ALLOWED_EXECUTABLES = frozenset({"systemctl"})
    FORBIDDEN_ARGUMENTS = frozenset(
        {
            "daemon-reload",
            "disable",
            "edit",
            "enable",
            "isolate",
            "kill",
            "mask",
            "reenable",
            "reload",
            "reset-failed",
            "restart",
            "set-default",
            "set-environment",
            "set-property",
            "start",
            "stop",
            "unmask",
            "unset-environment",
        }
    )

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._timeout_seconds = timeout_seconds

    @classmethod
    def validate(cls, argv: Sequence[str]) -> tuple[str, ...]:
        normalized = tuple(str(part) for part in argv)
        if not normalized:
            raise ValueError("Command argv must not be empty")
        executable = Path(normalized[0]).name.lower()
        if executable not in cls.ALLOWED_EXECUTABLES:
            raise ValueError(f"Executable is not approved for discovery: {executable}")
        forbidden = cls.FORBIDDEN_ARGUMENTS.intersection(part.lower() for part in normalized[1:])
        if forbidden:
            raise ValueError(
                "Mutation-shaped command arguments are forbidden: "
                + ", ".join(sorted(forbidden))
            )
        return normalized

    def run(self, argv: Sequence[str]) -> CommandResult:
        normalized = self.validate(argv)
        try:
            completed = subprocess.run(
                normalized,
                capture_output=True,
                check=False,
                shell=False,
                text=True,
                timeout=self._timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return CommandResult(normalized, None, "", "", str(error))
        return CommandResult(
            normalized,
            completed.returncode,
            completed.stdout,
            completed.stderr,
        )
