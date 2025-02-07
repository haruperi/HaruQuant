##############################################################################################
##                            GLOBAL SETTINGS - VARIABLES (g_)                              ##
##############################################################################################
from datetime import timedelta, datetime
from controllers.data import *


#--------------------------------------- Credentials data -----------------------------------#


g_credentials_filepath = "./config/credentials.json"


#--------------------------------------- Symbols Data -----------------------------------#


g_symbols_forex = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
    "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
    "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
    "USDCHF", "USDCAD", "USDJPY"]
g_symbols_commodities = ["XAUUSD", "XAUEUR", "XAUGBP", "XAUJPY", "XAUAUD", "XAUCHF", "XAGUSD"]
g_symbols_indices = ["US500", "US30", "UK100", "GER40", "NAS100", "USDX", "EURX"]


#--------------------------------------- Data variables -----------------------------------------#


g_interval_minutes = 5          # Trading timeframe minutes
g_time_shift=-3                 # Broker time shift from GMT 0
g_trading_timeframe = f'M{g_interval_minutes}'
g_core_timeframe = "D1"
g_start_pos=0                   # Data retrieval index starting point
g_end_pos=300                   # Data retrieval index ending point
g_end_pos_htf=200               # Data retrieval index ending point for a higher timeframe (if any)
g_end_pos_d1=30                 # Data retrieval index ending point for daily timeframe (whole last month)
g_range_start = datetime.now().strftime("%Y-%m-%d")         # Data retrieval range starting point
g_range_end = (datetime.now() - timedelta(days=g_end_pos_d1)).strftime("%Y-%m-%d")  # Data retrieval index starting point
g_start_date = "2024-06-01"     # Data retrieval date starting point
g_end_date = "2024-07-31"       # Data retrieval date ending point
g_test_symbol = "EURUSD"        # Random symbol for testing purposes


#--------------------------------------- Risk Variables --------------------------------------------#


g_stop_adr_ratio = 3            # Stop loss ratio level using ADR
g_max_risk_per_trade = 5
g_risk_base_amount = 276        # Manual fix to balance I want to calculate risk from


#--------------------------------------- Risk management variables -----------------------------------#


g_correlation_period = 20       # Correlation period (Num of days for a rolling window)
g_volatility_period = 10        # Volatility period (Num of days for a rolling window)
g_confidence_level = 0.95       # Percent to be covered in statistics
g_risk_threshold = 0.10         # Risk threshold for accepting new positions (10%)


#------------------------------------------ Technicals (Default values) -----------------------------------#


g_fast_ma = 12
g_slow_ma = 50
g_ma_type = "ema"
g_df_col = "Close"
g_rsi_period = 12
g_willpct_period = 6
g_adr_period = 10
g_strength_lookback_period = 144


#--------------------------------------- GLOBAL INIT -----------------------------------#


g_project_settings = get_project_settings(g_credentials_filepath)              # Import settings
g_init_mt5 = initialize_mt5(g_project_settings)                                # Start MT5
g_init_symbols = enable_all_symbols(g_symbols_forex)                       # Initialize Symbols
g_token = g_project_settings['telegram']['token']
g_chat_id = g_project_settings['telegram']['chat_id']



