"""Exact read-only GPD G1 DRM render binding resolver."""

from __future__ import annotations

import re
import stat
from collections.abc import Callable
from pathlib import Path

from ...domain.game_render_activity import DrmRenderBinding
from ...domain.models import ObservedSnapshot
from ...profiles.gpd_g1 import match_gpd_g1
from ...profiles.registry import resolve_runtime_profiles
from .drm import DrmDiscovery
from .pci import PciUsb4Discovery


RENDER_NODE_NAME_RE = re.compile(r"^renderD[0-9]+$")


def _character_device(path: Path) -> bool:
    try:
        return stat.S_ISCHR(path.stat().st_mode)
    except OSError:
        return False


class GpdG1DrmRenderBindingResolver:
    """Re-observe exact certified topology before deriving a private node."""

    def __init__(
        self,
        *,
        drm: DrmDiscovery | None = None,
        pci_usb4: PciUsb4Discovery | None = None,
        pci_path_resolver: Callable[[str], Path] = (
            lambda bdf: Path("/sys/bus/pci/devices") / bdf
        ),
        dri_root: Path = Path("/dev/dri"),
        node_validator: Callable[[Path], bool] = _character_device,
    ) -> None:
        self._drm = drm or DrmDiscovery()
        self._pci_usb4 = pci_usb4 or PciUsb4Discovery()
        self._pci_path_resolver = pci_path_resolver
        self._dri_root = dri_root
        self._node_validator = node_validator

    def resolve(self, snapshot: ObservedSnapshot) -> DrmRenderBinding | None:
        profiles = resolve_runtime_profiles(snapshot)
        readiness = snapshot.disconnect_readiness
        if (
            not profiles.exact_host
            or not profiles.exact_egpu
            or not readiness.applicable
            or readiness.egpu_stable_id != profiles.egpu_stable_id
        ):
            return None
        try:
            cards = self._drm.scan()
            pci = self._pci_usb4.scan_pci()
            usb4 = self._pci_usb4.scan_usb4()
            matched = match_gpd_g1(cards, pci, usb4)
            if (
                not matched.verified
                or matched.stable_id != profiles.egpu_stable_id
                or not matched.gpu_bdf
            ):
                return None
            exact_cards = tuple(
                card
                for card in cards
                if card.pci_bdf == matched.gpu_bdf
                and card.driver == "amdgpu"
            )
            if len(exact_cards) != 1:
                return None
            drm_directory = self._pci_path_resolver(matched.gpu_bdf) / "drm"
            render_names = tuple(
                sorted(
                    entry.name
                    for entry in drm_directory.iterdir()
                    if RENDER_NODE_NAME_RE.fullmatch(entry.name)
                )
            )
            if len(render_names) != 1:
                return None
            node = self._dri_root / render_names[0]
            if not self._node_validator(node):
                return None
            return DrmRenderBinding(
                matched.stable_id,
                matched.gpu_bdf.casefold(),
                "/".join(str(node).split("\\")),
            )
        except Exception:
            return None
