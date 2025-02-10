########################################################################################################################
#                                        Risk Management Class (Portfolio)
########################################################################################################################
from .data import *
from .technicals import *
from scipy.optimize import minimize


class PortfolioRiskMan:
    def __init__(self, start_position=0, end_position=0, start_date=None, end_date=None):
        # Initialize the portfolio risk manager with necessary attributes
        self.start_position = start_position
        self.end_position = end_position
        self.start_date = start_date
        self.end_date = end_date
        self.positions = {}
        self.data = {}
        self.nominal_values = {}
        self.portfolio_std_dev = 0.0
        self.portfolio_nominal_value = 0.0
        self.position_weights = {}
        self.std_dev_returns = {}
        self.correlation_objects = {}
        self.portfolio_var = 0


    def get_data(self, symbols):
        """
        Fetches historical data from MetaTrader 5 for given symbols within a specified date range and timeframe.
        """
        all_data = {}
        for symbol in symbols:
            df = fetch_data(symbol, "D1", start_pos=0, end_pos=60)
            if df is not None:
                all_data[symbol] = df
        self.data = all_data
        return self.data


    def calculate_returns(self):
        # Method to calculate returns from the fetched data
        for symbol, df in self.data.items():
            df['log_returns'] = np.log(df['Close'] / df['Close'].shift(1))
        return self.data


    def calculate_volatility(self, volatility_period):
        # Method to calculate volatility from the returns data
        for symbol, df in self.data.items():
            if 'log_returns' not in df.columns:
                raise ValueError(f"Log returns have not been calculated for {symbol}")
            df['volatility'] = df['log_returns'].shift(1).rolling(window=volatility_period).std()
            self.std_dev_returns[symbol] = df['volatility'].iloc[-2]  # Populate std_dev_returns
        return self.data

    def calculate_correlations(self, correlation_period=20):
        # Method to calculate rolling correlation matrix based on the last N days
        combined_returns = pd.DataFrame({symbol: df['log_returns'] for symbol, df in self.data.items()})
        rolling_correlations = combined_returns.rolling(window=correlation_period).corr()
        self.correlations = rolling_correlations

        # Populate correlation_objects
        symbols = list(self.positions.keys())
        for i, pair1 in enumerate(symbols):
            for j, pair2 in enumerate(symbols):
                if i < j:
                    correlation = rolling_correlations.loc[combined_returns.index[-2], pair1][pair2]
                    self.correlation_objects.setdefault(pair1, {})[pair2] = correlation
                    self.correlation_objects.setdefault(pair2, {})[pair1] = correlation
        return self.correlations

    def get_correlations(self, date = None):
        """
        Get the correlation matrix for all pairs.
        """
        return self.correlations.loc[date] if date else self.correlations.iloc[-2]

    def get_pair_correlation(self, pair1: str, pair2: str) -> float:
        """
        Get the correlation between two pairs.
        """
        return self.correlation_objects[pair1][pair2]

    def calculate_portfolio_nominal_value(self):
        """
        Calculate the nominal value of each pair and the total portfolio nominal value.
        """
        self.nominal_values = {}
        self.portfolio_nominal_value = 0.0

        for symbol, lot_size in self.positions.items():
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                print(f"Failed to get symbol info for {symbol}")
                continue

            nominal_value_per_unit_per_lot = symbol_info.trade_tick_value / symbol_info.trade_tick_size
            current_price = mt5.symbol_info_tick(symbol).bid
            nominal_value = lot_size * nominal_value_per_unit_per_lot * current_price
            self.nominal_values[symbol] = nominal_value
            self.portfolio_nominal_value += abs(nominal_value)

        return self.nominal_values, self.portfolio_nominal_value


    def get_positions(self):
        # Method to return current positions
        return self.positions


    def add_position(self, symbol, lot_size):
        # Method to add a position to the portfolio
        if symbol in self.positions:
            self.positions[symbol] += lot_size
            if self.positions[symbol] == 0:
                self.remove_position(symbol)
        else:
            self.positions[symbol] = lot_size

    def remove_position(self, symbol):
        # Method to remove a position from the portfolio
        if symbol in self.positions:
            del self.positions[symbol]


    def run(self, volatility_period=g_volatility_period, correlation_period=g_correlation_period):
        # Get Data from MT5
        symbols = list(self.get_positions().keys())
        self.get_data(symbols)

        # Calculate returns for all positions
        self.calculate_returns()

        # Calculate volatility for all positions with specified volatility period
        self.calculate_volatility(volatility_period)

        # Calculate rolling correlations for all positions with specified correlation period
        self.calculate_correlations(correlation_period)

        # Calculate nominal values for each pair and the combined portfolio value
        self.calculate_portfolio_nominal_value()






