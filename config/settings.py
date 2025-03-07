##############################################################################################
##                            GLOBAL SETTINGS - VARIABLES (g_)                              ##
##############################################################################################
from datetime import datetime, timedelta

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
g_time_shift=-2                 # Broker time shift from GMT 0
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





#--------------------------------------- Risk management variables -----------------------------------#
g_correlation_period = 20       # Correlation period (Num of days for a rolling window)
g_volatility_period = 10        # Volatility period (Num of days for a rolling window)
g_confidence_level = 0.95       # Percent to be covered in statistics
g_risk_threshold = 0.10         # Risk threshold for accepting new positions (10%)


#------------------------------------------ Technicals (Default values) -----------------------------------#
g_fast_ma = 12
g_slow_ma = 50
g_ma_type = "EMA"
g_df_col = "Close"
g_rsi_period = 15
g_willpct_period = 6
g_adr_period = 10
g_strength_lookback_period = 144


#------------------------------------------    Trading Settings  -------------------------------------------#
g_mt5_initialized = False

# Trading Hours Settings
g_use_trading_hours = False               # Limit trading hours
g_trading_hour_start = 7              # Trading start hour (Broker server hour)
g_trading_hour_end = 19                # Trading end hour (Broker server hour)

# Risk Management Settings
g_risk_default_size = "RISK_DEFAULT_FIXED"  # Position size mode
g_risk_base = "RISK_BASE_BALANCE"             # Risk base
g_risk_base_amount = 50083                    # Manual fix to balance I want to calculate risk from
g_max_risk_per_trade = 2                     # Percentage to risk each trade
g_default_lot_size = 0.01                     # Position size (if fixed or if no stop loss defined)
g_min_lot_size = 0.01                        # Minimum position size allowed
g_max_lot_size = 100                         # Maximum position size allowed
g_max_positions = 1                          # Maximum number of positions for this EA

# Stop-Loss and Take-Profit Settings
g_stop_loss_mode = "SL_FIXED"                # Stop-loss mode
g_stop_adr_ratio = 4                          # Stop loss ratio level using ADR
g_default_stop_loss = 0                      # Default stop-loss in points (0 = no stop-loss)
g_min_stop_loss = 0                          # Minimum allowed stop-loss in points
g_max_stop_loss = 5000                       # Maximum allowed stop-loss in points
g_take_profit_mode = "TP_FIXED"              # Take-profit mode
g_default_take_profit = 0                    # Default take-profit in points (0 = no take-profit)
g_min_take_profit = 0                        # Minimum allowed take-profit in points
g_max_take_profit = 5000                     # Maximum allowed take-profit in points

# Partial Close Settings
g_use_partial_close = False                # Use partial close
g_partial_close_perc = 50                    # Partial close percentage
g_atr_multiplier_pc = 1                      # ATR multiplier for partial close

# Additional Settings
g_magic_number = 0                           # Magic number
g_comment = "HaruQuant"                      # Comment for orders
g_slippage = 10                               # Slippage in points
g_max_spread = 50                            # Maximum allowed spread to trade, in points



