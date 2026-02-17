from apps.simulation.replay_hooks import compare_replay_runs, replay_fingerprint


def test_replay_fingerprint_stable_for_identical_sequences():
    seq_a = [
        {"timestamp": "2026-01-01T00:00:00Z", "symbol": "EURUSD", "side": "BUY", "price": 1.1000, "volume": 0.1},
        {"timestamp": "2026-01-01T00:01:00Z", "symbol": "EURUSD", "side": "SELL", "price": 1.1005, "volume": 0.1},
    ]
    seq_b = list(seq_a)

    assert replay_fingerprint(seq_a) == replay_fingerprint(seq_b)
    ok, message = compare_replay_runs(seq_a, seq_b)
    assert ok
    assert "Replay consistent" in message


def test_replay_fingerprint_detects_sequence_difference():
    baseline = [
        {"timestamp": "2026-01-01T00:00:00Z", "symbol": "EURUSD", "side": "BUY", "price": 1.1000, "volume": 0.1},
        {"timestamp": "2026-01-01T00:01:00Z", "symbol": "EURUSD", "side": "SELL", "price": 1.1005, "volume": 0.1},
    ]
    changed = [
        {"timestamp": "2026-01-01T00:00:00Z", "symbol": "EURUSD", "side": "BUY", "price": 1.1000, "volume": 0.1},
        {"timestamp": "2026-01-01T00:01:00Z", "symbol": "EURUSD", "side": "SELL", "price": 1.1008, "volume": 0.1},
    ]

    ok, message = compare_replay_runs(baseline, changed)
    assert not ok
    assert "Replay mismatch" in message

