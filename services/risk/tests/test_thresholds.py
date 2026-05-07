from services.risk.config.thresholds import load_risk_thresholds, validate_config_hash, validate_threshold_schema


def test_thresholds_load_and_validate():
    config = load_risk_thresholds()
    assert validate_threshold_schema(config) is True
    assert validate_config_hash(config, config["config_hash"]) is True

