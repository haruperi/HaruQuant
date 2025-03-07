import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
from enum import Enum

class OrderType(Enum):
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_BUY_STOP_LIMIT = 6
    ORDER_TYPE_SELL_STOP_LIMIT = 7
    ORDER_TYPE_CLOSE_BY = 8


class OrderState(Enum):
    ORDER_STATE_STARTED = 0
    ORDER_STATE_PLACED = 1
    ORDER_STATE_CANCELED = 2
    ORDER_STATE_PARTIAL = 3
    ORDER_STATE_FILLED = 4
    ORDER_STATE_REJECTED = 5
    ORDER_STATE_EXPIRED = 6
    ORDER_STATE_REQUEST_ADD = 7
    ORDER_STATE_REQUEST_MODIFY = 8
    ORDER_STATE_REQUEST_CANCEL = 9


class OrderTypeFilling(Enum):
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2


class OrderTypeTime(Enum):
    ORDER_TIME_GTC = 0
    ORDER_TIME_DAY = 1
    ORDER_TIME_SPECIFIED = 2
    ORDER_TIME_SPECIFIED_DAY = 3

class OrderInfo:
    """
    Class for access to order info.
    Python equivalent of MQL5's COrderInfo class and CHistoryOrderInfo all of them combined.

    Returned Tuple structure attributes: (ticket, time_setup, time_setup_msc, time_done, time_done_msc, time_expiration,
     type, type_time, type_filling, state, magic, position_id, position_by_id, reason, volume_initial, volume_current
     price_open, price_current, price_stoplimit, symbol, comment, external_id)
    """

    def __init__(self):
        """Constructor"""
        # Core order identification
        self.m_ticket = 0
        self.m_symbol = ""
        self.m_comment = ""
        self.m_external_id = ""

        # Order type and state
        self.m_type = None
        self.m_state = None
        self.m_type_time = None
        self.m_type_filling = None
        self.m_reason = 0

        # Time attributes
        self.m_time_setup = 0
        self.m_time_setup_msc = 0
        self.m_time_done = 0
        self.m_time_done_msc = 0
        self.m_expiration = 0  # time_expiration

        # Volume and price attributes
        self.m_volume_initial = 0.0
        self.m_volume_curr = 0.0  # volume_current
        self.m_price_open = 0.0
        self.m_price_current = 0.0
        self.m_price_stoplimit = 0.0
        self.m_stop_loss = 0.0  # sl
        self.m_take_profit = 0.0  # tp

        # Position related attributes
        self.m_position_id = 0
        self.m_position_by_id = 0
        self.m_magic = 0

        # Get broker timezone offset
        self.broker_timezone_offset = 0

#####################################    Populating of all attributes    ###############################################
    
    def select(self, category="current", ticket=None, index=None):
        """Select an order for further work"""

        if category == "current" and ticket is None:
            orders = mt5.orders_get()
            if orders is None or len(orders) == 0:
                return False
            self.store_state(orders[-1])
        elif category == "current" and ticket is not None:
            order = mt5.orders_get(ticket = ticket)
            if order is None or len(order) == 0:
                raise Exception(f"Order with ticket {ticket} not found.")
            else:
                self.store_state(order)
        elif category == "history" and ticket is not None:
            order = mt5.history_orders_get(ticket = ticket)
            if order is None or len(order) == 0:
                raise Exception(f"Order with ticket {ticket} not found.")
            else:
                self.store_state(order)
        elif category == "history":
            # Get all history orders
            from_date = 0  # From the beginning
            to_date = int(datetime.now().timestamp())  # Until now

            # Get history orders
            orders = mt5.history_orders_get(from_date, to_date)
            if orders is None:
                return False
            elif index is not None and len(orders) <= index:
                return False
            elif index is not None:
                self.store_state(orders[index])
            else:
                self.store_state(orders[-1])
        else: return False

        return True


    def store_state(self, order):
        """Store order state"""

        # Core order identification
        self.m_ticket = order.ticket
        self.m_symbol = order.symbol
        self.m_comment = order.comment
        self.m_external_id = order.external_id

        # Order type and state
        self.m_type = OrderType(order.type)
        self.m_state = OrderState(order.state)
        self.m_type_time = OrderTypeTime(order.type_time)
        self.m_type_filling = OrderTypeFilling(order.type_filling)
        self.m_reason = order.reason

        # Time attributes - convert to broker time
        self.m_time_setup = self._convert_to_broker_time(order.time_setup)
        self.m_time_setup_msc = order.time_setup_msc
        self.m_time_done = self._convert_to_broker_time(order.time_done)
        self.m_time_done_msc = order.time_done_msc
        self.m_expiration = self._convert_to_broker_time(order.time_expiration)

        # Volume and price attributes
        self.m_volume_initial = order.volume_initial
        self.m_volume_curr = order.volume_current
        self.m_price_open = order.price_open
        self.m_price_current = order.price_current
        self.m_price_stoplimit = order.price_stoplimit
        self.m_stop_loss = order.sl
        self.m_take_profit = order.tp

        # Position related attributes
        self.m_magic = order.magic
        self.m_position_id = order.position_id
        self.m_position_by_id = order.position_by_id


#####################################    Getters for all attributes    #################################################
    
    def get_ticket(self):
        return self.m_ticket

    def get_symbol(self):
        return self.m_symbol

    def get_comment(self):
        return self.m_comment

    def get_external_id(self):
        return self.m_external_id

    def get_type(self):
        return self.m_type

    def get_state(self):
        return self.m_state

    def get_type_time(self):
        return self.m_type_time

    def get_type_filling(self):
        return self.m_type_filling

    def get_reason(self):
        return self.m_reason

    def get_time_setup(self):
        return self.m_time_setup

    def get_time_setup_msc(self):
        return self.m_time_setup_msc

    def get_time_done(self):
        return self.m_time_done

    def get_time_done_msc(self):
        return self.m_time_done_msc

    def get_expiration(self):
        return self.m_expiration

    def get_volume_initial(self):
        return self.m_volume_initial

    def get_volume_curr(self):
        return self.m_volume_curr

    def get_price_open(self):
        return self.m_price_open

    def get_price_current(self):
        return self.m_price_current

    def get_price_stoplimit(self):
        return self.m_price_stoplimit

    def get_stop_loss(self):
        return self.m_stop_loss

    def get_take_profit(self):
        return self.m_take_profit

    def get_position_id(self):
        return self.m_position_id

    def get_position_by_id(self):
        return self.m_position_by_id

    def get_magic(self):
        return self.m_magic


#####################################    Getters with descriptions    #################################################

    def get_type_description(self):
        """Get order type as string"""
        if self.m_type is None:
            return "Unknown order type: order details not found."
        return self.format_type(self.m_type.value)


    def get_state_description(self):
        """Get order state as string"""
        if self.m_state is None:
            return "Unknown order state: order details not found."
        return self.format_status(self.m_state.value)


    def get_type_filling_description(self):
        """Get order filling type as string"""
        if self.m_type_filling is None:
            return "Unknown order filling type: order details not found."
        return self.format_type_filling(self.m_type_filling.value)

    def get_type_time_description(self):
        """Get order lifetime type as string"""
        if self.m_type_time is None:
            return "Unknown order lifetime type: order details not found."
        return self.format_type_time(self.m_type_time.value)
    
    def get_order_description(self):
        """Get order description in string format"""
        return f"{self.get_type_description()} {self.m_symbol} {self.m_volume_curr} at {self.m_price_open} sl: {self.m_stop_loss} tp: {self.m_take_profit}"

#####################################    Formating descriptions    #################################################

    @staticmethod
    def format_type(type_val):
        """Format the order type as string"""
        order_types = {
            0: "Buy",
            1: "Sell",
            2: "Buy Limit",
            3: "Sell Limit",
            4: "Buy Stop",
            5: "Sell Stop",
            6: "Buy Stop Limit",
            7: "Sell Stop Limit",
            8: "Close By"
        }
        return order_types.get(type_val, "Unknown")

    @staticmethod
    def format_status(status):
        """Format the order status as string"""
        order_states = {
            0: "Started",
            1: "Placed",
            2: "Canceled",
            3: "Partial",
            4: "Filled",
            5: "Rejected",
            6: "Expired",
            7: "Request Add",
            8: "Request Modify",
            9: "Request Cancel"
        }
        return order_states.get(status, "Unknown")

    @staticmethod
    def format_type_filling(type_val):
        """Format the order filling type as string"""
        filling_types = {
            0: "Fill or Kill",
            1: "Immediate or Cancel",
            2: "Return"
        }
        return filling_types.get(type_val, "Unknown")

    @staticmethod
    def format_type_time(type_val):
        """Format the order lifetime as string"""
        time_types = {
            0: "GTC",
            1: "Day",
            2: "Specified",
            3: "Specified Day"
        }
        return time_types.get(type_val, "Unknown")

    

    @staticmethod
    def format_price(price_order, price_trigger, digits):
        """Format the order price"""
        if price_trigger:
            return f"{price_order:.{digits}f} ({price_trigger:.{digits}f})"
        return f"{price_order:.{digits}f}"

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
    
