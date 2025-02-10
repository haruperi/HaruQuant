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


    def run(self):
        # Get Data from MT5
        symbols = list(self.get_positions().keys())
        self.get_data(symbols)

        # Calculate returns for all positions
        self.calculate_returns()






