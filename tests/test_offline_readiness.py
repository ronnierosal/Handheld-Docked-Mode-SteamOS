from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.domain.offline_readiness import (  # noqa: E402
    CloudSaveState,
    DownloadState,
    InstallState,
    LocalOfflineBlocker,
    OfflineReadinessEvidence,
    OfflineReadinessAssessment,
    OfflineReadinessStatus,
    OnlineCheckRequirement,
    SteamEntitlementState,
    classify_offline_readiness,
    offline_readiness_to_public_dict,
)


def ready_evidence(**changes) -> OfflineReadinessEvidence:
    value = OfflineReadinessEvidence(
        install=InstallState.INSTALLED,
        download=DownloadState.CURRENT,
        steam_entitlement=SteamEntitlementState.RECENT_SIGN_IN_AND_LICENSE,
        cloud_save=CloudSaveState.SYNCED,
    )
    return replace(value, **changes)


class OfflineReadinessTests(unittest.TestCase):
    def test_complete_local_evidence_is_ready_to_try_not_a_guarantee(self):
        assessment = classify_offline_readiness(ready_evidence())
        self.assertEqual(assessment.status, OfflineReadinessStatus.READY_TO_TRY_OFFLINE)
        self.assertEqual(assessment.reason_codes, ("local_readiness_confirmed",))

    def test_local_blockers_and_pending_data_need_attention(self):
        assessment = classify_offline_readiness(
            ready_evidence(
                download=DownloadState.PENDING_UPDATE,
                cloud_save=CloudSaveState.CONFLICT,
                local_blockers=(LocalOfflineBlocker.LOCAL_STORAGE_UNAVAILABLE,),
            )
        )
        self.assertEqual(assessment.status, OfflineReadinessStatus.NEEDS_ATTENTION)
        self.assertEqual(
            assessment.reason_codes,
            ("local_storage_unavailable", "update_pending", "cloud_save_conflict"),
        )

    def test_launcher_drm_anticheat_and_game_owned_requirements_need_online_check(self):
        assessment = classify_offline_readiness(
            ready_evidence(
                online_check_requirements=(
                    OnlineCheckRequirement.THIRD_PARTY_LAUNCHER,
                    OnlineCheckRequirement.DRM,
                    OnlineCheckRequirement.ANTI_CHEAT,
                    OnlineCheckRequirement.GAME_OWNED_ONLINE_REQUIREMENT,
                )
            )
        )
        self.assertEqual(assessment.status, OfflineReadinessStatus.ONLINE_CHECK_NEEDED)
        self.assertEqual(
            assessment.reason_codes,
            ("third_party_launcher", "drm", "anti_cheat", "game_owned_online_requirement"),
        )

    def test_unknown_or_unconfirmed_evidence_fails_closed(self):
        assessment = classify_offline_readiness(OfflineReadinessEvidence())
        self.assertEqual(assessment.status, OfflineReadinessStatus.UNKNOWN)
        self.assertIn("steam_entitlement_unknown", assessment.reason_codes)

    def test_attention_wins_over_online_check_and_unknown_evidence(self):
        assessment = classify_offline_readiness(
            OfflineReadinessEvidence(
                install=InstallState.NOT_INSTALLED,
                online_check_requirements=(OnlineCheckRequirement.DRM,),
            )
        )
        self.assertEqual(assessment.status, OfflineReadinessStatus.NEEDS_ATTENTION)
        self.assertEqual(assessment.reason_codes, ("game_not_installed",))

    def test_public_serialization_exposes_only_categorical_guidance(self):
        payload = offline_readiness_to_public_dict(classify_offline_readiness(ready_evidence()))
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "ready_to_try_offline")
        self.assertNotIn("steam_app_id", payload)
        self.assertNotIn("title", payload)
        self.assertNotIn("path", payload)

    def test_duplicate_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicated"):
            OfflineReadinessEvidence(
                local_blockers=(
                    LocalOfflineBlocker.MISSING_LOCAL_CONTENT,
                    LocalOfflineBlocker.MISSING_LOCAL_CONTENT,
                )
            )

    def test_assessment_rejects_non_public_reason_text(self):
        with self.assertRaisesRegex(ValueError, "not public"):
            OfflineReadinessAssessment(
                OfflineReadinessStatus.UNKNOWN,
                ("account-name-or-private-path",),
            )


if __name__ == "__main__":
    unittest.main()
