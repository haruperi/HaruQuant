
import apps.live

def test_exports():
    assert hasattr(apps.live, "Config")
    assert hasattr(apps.live, "StateManager")
    assert hasattr(apps.live, "BarMonitor")
    assert hasattr(apps.live, "SignalProcessor")
    assert hasattr(apps.live, "PositionManager")
    assert hasattr(apps.live, "SafetyChecker")
    assert hasattr(apps.live, "TradeExecutor")
    assert hasattr(apps.live, "EmailNotifier")
    assert hasattr(apps.live, "LiveTradingNotifier")
    assert hasattr(apps.live, "PortfolioManager")
    assert hasattr(apps.live, "MultiStrategyEngine")
    assert hasattr(apps.live, "RiskIntegratedEngine")

def test_all_list():
    expected = [
        "Config",
        "StateManager",
        "BarMonitor",
        "SignalProcessor",
        "PositionManager",
        "SafetyChecker",
        "TradeExecutor",
        "EmailNotifier",
        "LiveTradingNotifier",
        "PortfolioManager",
        "MultiStrategyEngine",
        "RiskIntegratedEngine",
    ]
    assert sorted(apps.live.__all__) == sorted(expected)
