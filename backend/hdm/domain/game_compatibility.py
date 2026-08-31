"""Typed game save/sleep compatibility values; no automatic verification."""

from __future__ import annotations

from enum import StrEnum


class GameSaveCapability(StrEnum):
    UNTESTED = "untested"
    VERIFIED_TRIGGERABLE_AUTOSAVE = "verified_triggerable_autosave"
    VERIFIED_SAVE_ON_EXIT = "verified_save_on_exit"
    GRACEFUL_EXIT_VERIFIED = "graceful_exit_verified"
    MANUAL_SAVE_RECOMMENDED = "manual_save_recommended"
    MANUAL_SAVE_REQUIRED = "manual_save_required"
    UNSAFE_UNKNOWN = "unsafe_unknown"


def save_warning_required(capability: GameSaveCapability) -> bool:
    return capability in {
        GameSaveCapability.UNTESTED,
        GameSaveCapability.MANUAL_SAVE_RECOMMENDED,
        GameSaveCapability.MANUAL_SAVE_REQUIRED,
        GameSaveCapability.UNSAFE_UNKNOWN,
    }

