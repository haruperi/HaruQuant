import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta

class PositionInfo:
    def __init__(self):
        """Constructor"""
        # Core position identification
        self.m_ticket = 0  # int
        self.m_identifier = 0  # int
        self.m_symbol = ""  # str
        self.m_comment = ""  # str
        self.m_external_id = ""  # str

        # Position type and reason
        self.m_type = None  # OrderType enum
        self.m_reason = 0  # int
        self.m_magic = 0  # int

        # Time attributes
        self.m_time = 0  # int (timestamp)
        self.m_time_msc = 0  # int (milliseconds)
        self.m_time_update = 0  # int (timestamp)
        self.m_time_update_msc = 0  # int (milliseconds)

        # Volume and price attributes
        self.m_volume = 0.0  # float
        self.m_price_open = 0.0  # float
        self.m_price_current = 0.0  # float
        self.m_stop_loss = 0.0  # float (sl)
        self.m_take_profit = 0.0  # float (tp)
        self.m_swap = 0.0  # float
        self.m_profit = 0.0  # float

        # Get broker timezone offset
        self.broker_timezone_offset = 0

#####################################    Populating of all attributes    ###############################################

    def select(self, category="current", ticket=None, index=None):
        """Select a position for further work"""

        if category == "current" and ticket is None:
            positions = mt5.positions_get()
            if positions is None or len(positions) == 0:
                return False
            self.store_state(positions[-1])
        elif category == "current" and ticket is not None:
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                raise Exception(f"position with ticket {ticket} not found.")
            else:
                self.store_state(position)
        elif category == "current" and index is not None:
            positions = mt5.positions_get()
            if 0 <= index < len(positions):
                self.store_state(positions[index])
        elif category == "history" and ticket is not None:
            deal = mt5.history_deals_get(ticket=ticket)
            if deal is None or len(deal) == 0:
                raise Exception(f"Deal with ticket {ticket} not found.")
            else:
                self.store_state(deal)
        elif category == "history":
            # Get all history deals
            from_date = 0  # From the beginning
            to_date = int(datetime.now().timestamp())  # Until now

            # Get history orders
            deals = mt5.history_deals_get(from_date, to_date)
            if deals is None:
                return False
            elif index is not None and len(deals) <= index:
                return False
            elif index is not None:
                self.store_state(deals[index])
            else:
                self.store_state(deals[-1])
        else:
            return False

        return True

    def store_state(self, position):
        """Store position state"""

        # Core position identification
        self.m_ticket = position.ticket
        self.m_identifier = position.identifier
        self.m_symbol = position.symbol
        self.m_comment = position.comment
        self.m_external_id = position.external_id

        # Position type and reason
        self.m_type = position.type
        self.m_reason = position.reason
        self.m_magic = position.magic

        # Time attributes
        self.m_time = self._convert_to_broker_time(position.time)
        self.m_time_msc = position.time_msc
        self.m_time_update = self._convert_to_broker_time(position.time_update)
        self.m_time_update_msc = position.time_update_msc

        # Volume and price attributes
        self.m_volume = position.volume
        self.m_price_open = position.price_open
        self.m_price_current = position.price_current
        self.m_stop_loss = position.sl
        self.m_take_profit = position.tp
        self.m_swap = position.swap
        self.m_profit = position.profit

#####################################    Getters for all attributes    #################################################

    def get_ticket(self):
        return self.m_ticket

    def get_time(self):
        return self.m_time

    def get_time_msc(self):
        return self.m_time_msc

    def get_time_update(self):
        return self.m_time_update

    def get_time_update_msc(self):
        return self.m_time_update_msc

    def get_type(self):
        return self.m_type

    def get_magic(self):
        return self.m_magic

    def get_identifier(self):
        return self.m_identifier

    def get_reason(self):
        return self.m_reason

    def get_volume(self):
        return self.m_volume

    def get_price_open(self):
        return self.m_price_open

    def get_stop_loss(self):
        return self.m_stop_loss

    def get_take_profit(self):
        return self.m_take_profit

    def get_price_current(self):
        return self.m_price_current

    def get_swap(self):
        return self.m_swap

    def get_profit(self):
        return self.m_profit

    def get_symbol(self):
        return self.m_symbol

    def get_comment(self):
        return self.m_comment

    def get_external_id(self):
        return self.m_external_id

    #####################################    Getters with descriptions    #################################################

    def get_type_description(self):
        """Get position type as string"""
        if self.m_type is None:
            return "Unknown position type: position details not found."
        return self.format_type(self.m_type)


    def get_position_description(self):
        """Get position description in string format"""
        return f"{self.get_type_description()} {self.m_symbol} {self.m_volume} at {self.m_price_open} sl: {self.m_stop_loss} tp: {self.m_take_profit}"


    @staticmethod
    def format_type(pos_type):
        """Converts the position type to text"""
        if pos_type == 0:
            return "buy"
        elif pos_type == 1:
            return "sell"
        else:
            return f"unknown position type {pos_type}"


    @staticmethod
    def select_by_symbol(symbol):
        """Access functions PositionSelect(...)"""
        positions = mt5.positions_get(symbol=symbol)
        if len(positions) > 0:
            return positions
        return None

    @staticmethod
    def select_by_magic(magic):
        """Access functions PositionSelect(...) by magic number"""
        positions = mt5.positions_get(group=magic)
        if len(positions) > 0:
            return positions
        return None


#####################################    Helper functions    #################################################

    def _convert_to_broker_time(self, timestamp):
        """Convert GMT timestamp to broker's local time"""
        if timestamp <= 0:
            return None

        # Convert timestamp to datetime in UTC
        dt_utc = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        # Apply broker timezone offset
        dt_broker = dt_utc + timedelta(hours=self.broker_timezone_offset)

        return dt_broker
