"""Tenda model/firmware compatibility registry.

Profiles are deliberately conservative: a matching family is not proof that
every endpoint works. Write capabilities remain disabled until verified on
that exact hardware revision and firmware.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class TendaProfile:
    profile_id: str
    label: str
    model_patterns: tuple[str, ...]
    firmware_patterns: tuple[str, ...]
    api_family: str
    confidence: str
    notes: str
    capabilities: dict[str, str]


PROFILES = (
    TendaProfile(
        profile_id="f3-v12-legacy",
        label="Tenda F3 / legacy V12 firmware",
        model_patterns=(r"\bF3\b",),
        firmware_patterns=(r"V12\.01\.",),
        api_family="legacy-goform-v12",
        confidence="candidate",
        notes="F3-specific protocol profile; endpoint and parameter compatibility must be verified on-device.",
        capabilities={
            "device_list": "candidate_unverified",
            "device_block": "candidate_unverified",
            "speed_limit": "candidate_unverified",
            "website_block": "candidate_unverified",
            "wifi_settings": "candidate_unverified",
            "scheduled_reboot": "candidate_unverified",
            "admin_password": "candidate_unverified",
            "dns": "candidate_unverified",
            "vpn": "candidate_unverified",
            "usage_history": "unsupported_until_counter_verified",
        },
    ),
    TendaProfile(
        profile_id="rtl-v15-ac10",
        label="Tenda AC10 RTL / V15 firmware",
        model_patterns=(r"\bAC10\b",),
        firmware_patterns=(r"V15\.03\.06\.50",),
        api_family="rtl-v15-goform",
        confidence="reference_only",
        notes="Based on reverse-engineered AC10 V1.0 reference; do not assume compatibility with other AC models.",
        capabilities={
            "device_list": "reference_available",
            "device_block": "reference_available",
            "speed_limit": "reference_available",
            "website_block": "reference_available",
            "wifi_settings": "documented_unverified",
            "scheduled_reboot": "documented_unverified",
            "admin_password": "not_implemented",
            "dns": "manual_wan_dns_only",
            "vpn": "model_firmware_dependent",
            "usage_history": "not_verified",
        },
    ),
    TendaProfile(
        profile_id="legacy-goform-family",
        label="Tenda legacy goform family (unclassified)",
        model_patterns=(),
        firmware_patterns=(),
        api_family="legacy-goform-unknown",
        confidence="unknown",
        notes="Tenda web UI detected, but model/firmware is not positively identified.",
        capabilities={k: "disabled_until_verified" for k in (
            "device_list", "device_block", "speed_limit", "website_block",
            "wifi_settings", "scheduled_reboot", "admin_password", "dns",
            "vpn", "usage_history",
        )},
    ),
)


def identify_profile(model_text: str = "", firmware_text: str = "") -> dict:
    model_text = model_text or ""
    firmware_text = firmware_text or ""
    combined = f"{model_text}\n{firmware_text}"
    for profile in PROFILES[:2]:
        model_match = any(re.search(p, model_text, re.I) for p in profile.model_patterns)
        firmware_match = any(re.search(p, firmware_text, re.I) for p in profile.firmware_patterns)
        if model_match and firmware_match:
            result = asdict(profile)
            result["detected_model"] = model_text.strip() or None
            result["detected_firmware"] = firmware_text.strip() or None
            return result
    result = asdict(PROFILES[2])
    result["detected_model"] = model_text.strip() or None
    result["detected_firmware"] = firmware_text.strip() or None
    result["confidence"] = "unknown"
    result["notes"] += " A model or firmware string alone is insufficient to enable write operations."
    return result
