"""ASUS ROG Ally X host classification."""

from __future__ import annotations

from ..adapters.steamos.host import HostRecord


PROFILE_ID = "asus-rog-ally-x"


def matches_ally_x(host: HostRecord) -> bool:
    vendor = host.sys_vendor.casefold()
    identity = f"{host.product_name} {host.board_name}".casefold()
    return (
        ("asus" in vendor or "asustek" in vendor)
        and ("rog ally x" in identity or "rc72la" in identity)
    )
