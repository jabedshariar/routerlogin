from routerly_connector.adapters import identify_profile


def test_f3_profile_requires_model_and_firmware():
    result = identify_profile("Tenda F3", "V12.01.01.48_multi")
    assert result["profile_id"] == "f3-v12-legacy"
    assert result["confidence"] == "candidate"
    assert result["capabilities"]["device_block"] == "candidate_unverified"


def test_model_without_firmware_stays_unknown():
    result = identify_profile("Tenda F3", "")
    assert result["profile_id"] == "legacy-goform-family"
    assert result["confidence"] == "unknown"


def test_ac10_profile_is_firmware_specific():
    result = identify_profile("Tenda AC10 V1.0", "V15.03.06.50_multi")
    assert result["profile_id"] == "rtl-v15-ac10"


def test_unknown_tenda_has_no_enabled_writes():
    result = identify_profile("Tenda unknown", "unknown firmware")
    assert all(v == "disabled_until_verified" for v in result["capabilities"].values())
