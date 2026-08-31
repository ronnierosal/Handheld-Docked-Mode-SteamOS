"""ASUS ROG Ally X host classification."""

from __future__ import annotations

from ..adapters.steamos.host import HostRecord
from ..domain.control_plane import (
    CapabilitySupport,
    EgpuTransport,
    HostCapabilities,
)


PROFILE_ID = "asus-rog-ally-x"
CAPABILITIES = HostCapabilities(
    profile_id=PROFILE_ID,
    egpu_support=CapabilitySupport.VERIFIED,
    egpu_transport=EgpuTransport.USB4,
    display_handoff=CapabilitySupport.EXPERIMENTAL,
    audio_handoff=CapabilitySupport.EXPERIMENTAL,
    internal_controller_suppression=CapabilitySupport.UNKNOWN,
    external_controller_promotion=CapabilitySupport.UNKNOWN,
    power_button_interception=CapabilitySupport.EXPERIMENTAL,
)


def matches_ally_x(host: HostRecord) -> bool:
    vendor = host.sys_vendor.casefold()
    identity = f"{host.product_name} {host.board_name}".casefold()
    return (
        ("asus" in vendor or "asustek" in vendor)
        and ("rog ally x" in identity or "rc72la" in identity)
    )
