"""Fixed-boundary support bundle file export."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..application.support_bundle import SupportBundle


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class SupportBundleSaveResult:
    relative_path: str
    size_bytes: int


class SupportBundleFileWriter:
    def __init__(
        self,
        *,
        allowed_home_parent: Path = Path("/home"),
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._allowed_home_parent = allowed_home_parent.resolve()
        self._clock = clock

    def save(self, raw_home: Path, bundle: SupportBundle) -> SupportBundleSaveResult:
        if not raw_home.is_absolute():
            raise ValueError("Decky user home is unavailable")
        home = raw_home.resolve(strict=True)
        if home.parent != self._allowed_home_parent or home.name in {"", ".", ".."}:
            raise ValueError("Decky user home is outside the supported SteamOS boundary")

        downloads = home / "Downloads"
        downloads.mkdir(mode=0o700, exist_ok=True)
        resolved_downloads = downloads.resolve(strict=True)
        if resolved_downloads.parent != home:
            raise ValueError("Downloads directory resolves outside the Decky user home")

        timestamp = self._clock().astimezone(timezone.utc).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )
        filename = f"HDM-support-{timestamp}.json"
        target = resolved_downloads / filename
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(target, flags, 0o600)
        try:
            if hasattr(os, "fchown"):
                owner = home.stat()
                os.fchown(fd, owner.st_uid, owner.st_gid)
            data = bundle.json_text.encode("utf-8")
            offset = 0
            while offset < len(data):
                written = os.write(fd, data[offset:])
                if written <= 0:
                    raise OSError("support bundle write made no progress")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
        return SupportBundleSaveResult(
            relative_path=f"Downloads/{filename}",
            size_bytes=bundle.size_bytes,
        )
