"""Constrained subprocess mechanisms with exact, shell-free command shapes."""

from __future__ import annotations

import os
import re
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


@dataclass(frozen=True, slots=True)
class ManagedProcessStatus:
    running: bool
    error: str = ""


class SleepInhibitorProcess:
    """Own the exact systemd-inhibit process used by the G1 sleep guard."""

    STARTUP_GRACE_SECONDS = 0.25
    STOP_TIMEOUT_SECONDS = 2.0
    PYTHON = "/usr/bin/python"
    EXCLUDED_ENVIRONMENT = frozenset(
        {"LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONHOME", "PYTHONPATH"}
    )

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None

    @staticmethod
    def argv() -> tuple[str, ...]:
        guard = Path(__file__).with_name("inhibitor_guard.py")
        return (SleepInhibitorProcess.PYTHON, str(guard), "--guard", str(os.getpid()))

    @classmethod
    def environment(cls) -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key not in cls.EXCLUDED_ENVIRONMENT
        }

    def start(self) -> ManagedProcessStatus:
        status = self.status()
        if status.running:
            return status
        argv = self.argv()
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=self.environment(),
                shell=False,
                text=True,
            )
            self._process = process
            try:
                process.wait(timeout=self.STARTUP_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                return ManagedProcessStatus(True)
            detail = (process.stderr.read() if process.stderr else "").strip()[:512]
            self._process = None
            return ManagedProcessStatus(
                False,
                detail or f"systemd-inhibit exited with status {process.returncode}",
            )
        except (OSError, subprocess.SubprocessError) as error:
            self._process = None
            return ManagedProcessStatus(False, str(error))

    def stop(self) -> ManagedProcessStatus:
        process = self._process
        self._process = None
        if process is None or process.poll() is not None:
            return ManagedProcessStatus(False)
        try:
            process.terminate()
            process.wait(timeout=self.STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=self.STOP_TIMEOUT_SECONDS)
        except OSError as error:
            return ManagedProcessStatus(False, str(error))
        return ManagedProcessStatus(False)

    def status(self) -> ManagedProcessStatus:
        process = self._process
        if process is None:
            return ManagedProcessStatus(False)
        returncode = process.poll()
        if returncode is None:
            return ManagedProcessStatus(True)
        detail = (process.stderr.read() if process.stderr else "").strip()[:512]
        self._process = None
        return ManagedProcessStatus(
            False,
            detail or f"systemd-inhibit exited with status {returncode}",
        )


class ReadOnlyCommandRunner:
    """Run a small allowlist without a shell or mutation-shaped arguments."""

    SYSTEMCTL_SCOPE_QUERY = (
        "--user",
        "list-units",
        "--type=scope",
        "--state=running",
        "--plain",
        "--no-legend",
        "--no-pager",
    )
    SAFE_USERNAME = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*[$]?")
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
        forbidden = cls.FORBIDDEN_ARGUMENTS.intersection(
            part.lower() for part in normalized[1:]
        )
        if forbidden:
            raise ValueError(
                "Mutation-shaped command arguments are forbidden: "
                + ", ".join(sorted(forbidden))
            )
        if (
            Path(normalized[0]).name.lower() == "systemctl"
            and normalized[1:] == cls.SYSTEMCTL_SCOPE_QUERY
        ):
            return normalized
        if cls._is_user_systemctl_scope_query(normalized):
            return normalized
        raise ValueError("Command is not approved as a read-only discovery query")

    @classmethod
    def _is_user_systemctl_scope_query(cls, argv: tuple[str, ...]) -> bool:
        prefix_length = 8
        if len(argv) != prefix_length + len(cls.SYSTEMCTL_SCOPE_QUERY):
            return False
        runuser, user_flag, username, separator, env, runtime, bus, systemctl = argv[:8]
        if (
            runuser != "/usr/bin/runuser"
            or user_flag != "-u"
            or not cls.SAFE_USERNAME.fullmatch(username)
            or separator != "--"
            or env != "/usr/bin/env"
            or systemctl != "/usr/bin/systemctl"
            or argv[8:] != cls.SYSTEMCTL_SCOPE_QUERY
        ):
            return False
        runtime_match = re.fullmatch(r"XDG_RUNTIME_DIR=/run/user/([0-9]+)", runtime)
        bus_match = re.fullmatch(
            r"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/([0-9]+)/bus", bus
        )
        return bool(
            runtime_match
            and bus_match
            and runtime_match.group(1) == bus_match.group(1)
        )

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
