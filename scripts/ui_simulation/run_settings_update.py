"""Temporary script to run settings update with complex JSON data."""

import os
import sys

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from scripts.ui_simulation.settings import update_settings  # noqa: E402


def run():
    """Execute the settings update simulation."""
    username = "haruperi"

    broker_credentials = {
        "accounts": [
            {
                "id": "acc_1766057545740",
                "name": "Pepperstone Demo",
                "description": "My Pepperstone Demo",
                "login": "61450707",
                "password": "qmotWcgh3$",
                "server": "Pepperstone-Demo",
                "environment": "demo",
                "terminalPath": "C:\\Program Files\\Pepperstone MetaTrader 5\\terminal64.exe",
                "isDefault": True,
                "type": "MT5",
            },
            {
                "id": "acc_1766064935191",
                "name": "Pepperstone Live",
                "description": "My Pepperstone Live",
                "login": "51307472",
                "password": "gJ!ZsxJ062ZXM%%L",
                "server": "Pepperstone-MT5-Live01",
                "environment": "live",
                "terminalPath": "C:\\Program Files\\Pepperstone MetaTrader 5\\terminal64.exe",
                "isDefault": False,
                "type": "MT5",
            },
            {
                "id": "acc_1766065008367",
                "name": "Dukascopy Demo ",
                "description": "My Dukascopy Demo",
                "login": "1724642629",
                "password": "HAv!_z-0",
                "server": "Dukascopy-demo-mt5-1",
                "environment": "demo",
                "terminalPath": "C:\\Program Files\\Dukascopy MetaTrader 5\\terminal64.exe",
                "isDefault": False,
                "type": "MT5",
            },
        ]
    }

    trading_preferences = {
        "riskManagementActive": True,
        "activeBrokerAccount": "acc_1766057545740",
        "magicNumber": "1988",
        "maxDeviation": "5",
        "maxSlippage": "3",
        "maxSpread": "10",
        "leverage": "400",
        "initialCapital": "10000",
        "defaultLotSize": "0.1",
        "riskPerTrade": "1",
        "riskThreshold": "10",
        "correlationPeriod": "10",
        "adrPeriod": "10",
        "volatilityPeriod": "5",
        "confidenceLevel": "0.95",
        "chartBackground": "#161A25",
        "bullishCandle": "#26A69A",
        "bearishCandle": "#EF5350",
        "forexSymbols": "AUDCAD,AUDCHF,AUDJPY,AUDNZD,AUDUSD,CADCHF,CADJPY,CHFJPY,EURAUD,EURCAD,EURCHF,EURGBP,EURJPY,EURNZD,EURUSD,GBPAUD,GBPCAD,GBPCHF,GBPJPY,GBPNZD,GBPUSD,NZDCAD,NZDCHF,NZDJPY,NZDUSD,USDCHF,USDCAD,USDJPY",
        "commoditySymbols": "XAUUSD,XAUEUR,XAUGBP,XAUJPY,XAUAUD,XAUCHF,XAGUSD",
        "indicesSymbols": "US500,US30,UK100,GER40,NAS100,USDX,EURX",
        "maxDailyLoss": "5000",
        "maxDrawdown": "10",
        "maxExposure": "100000",
        "maxPositionSize": "1",
        "maxPositions": "10",
        "minMarginLevel": "100",
        "autoKillDailyLoss": True,
        "autoKillDrawdown": True,
    }

    notifications = {
        "channels": [
            {
                "id": "ch_1766057720434",
                "name": "TelegramBot",
                "type": "telegram",
                "enabled": True,
                "config": {
                    "botToken": "7364825288:AAGA-xxXNJYMGxcxOy4MrmonyoSsA1USAtw",
                    "chatIds": "5398524142",
                    "soundOn": True,
                    "protectContent": True,
                },
            }
        ]
    }

    alert_triggers = {
        "tradeOpened": True,
        "tradeClosed": True,
        "systemErrors": True,
        "warnings": True,
        "stopLossHit": True,
        "takeProfitHit": True,
    }

    success = update_settings(
        username=username,
        theme="system",
        language="en",
        timezone="local",
        log_verbosity="debug",
        performance_mode="balanced",
        broker_credentials=broker_credentials,
        trading_preferences=trading_preferences,
        notifications=notifications,
        alert_triggers=alert_triggers,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    run()
