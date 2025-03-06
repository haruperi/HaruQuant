import MetaTrader5 as mt5
from datetime import datetime
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
    Python equivalent of MQL5's COrderInfo class.
    """

    def __init__(self):
        """Constructor"""
        self.m_ticket = 0
        self.m_type = None
        self.m_state = None
        self.m_expiration = None
        self.m_volume_curr = 0.0
        self.m_price_open = 0.0
        self.m_stop_loss = 0.0
        self.m_take_profit = 0.0

    def get_ticket(self):
        """Get order ticket"""
        return self.m_ticket

    def get_time_setup(self):
        """Get order setup time"""
        return datetime.fromtimestamp(mt5.order_info(self.m_ticket).time_setup)

    def get_time_setup_msc(self):
        """Get order setup time in milliseconds"""
        return mt5.order_info(self.m_ticket).time_setup_msc

    def get_time_done(self):
        """Get order execution or cancellation time"""
        return datetime.fromtimestamp(mt5.order_info(self.m_ticket).time_done)

    def get_time_done_msc(self):
        """Get order execution or cancellation time in milliseconds"""
        return mt5.order_info(self.m_ticket).time_done_msc

    def get_order_type(self):
        """Get order type"""
        return OrderType(mt5.order_info(self.m_ticket).type)

    def get_type_description(self):
        """Get order type as string"""
        order_type = self.OrderType()
        return self.FormatType("", order_type.value)

    def get_state(self):
        """Get order state"""
        return OrderState(mt5.order_info(self.m_ticket).state)

    def get_state_description(self):
        """Get order state as string"""
        state = self.State()
        return self.FormatStatus("", state.value)

    def get_time_expiration(self):
        """Get order expiration time"""
        expiration = mt5.order_info(self.m_ticket).time_expiration
        return datetime.fromtimestamp(expiration) if expiration > 0 else None

    def get_type_filling(self):
        """Get order filling type"""
        return OrderTypeFilling(mt5.order_info(self.m_ticket).type_filling)

    def get_type_filling_description(self):
        """Get order filling type as string"""
        filling_type = self.TypeFilling()
        return self.FormatTypeFilling("", filling_type.value)

    def get_type_time(self):
        """Get order lifetime type"""
        return OrderTypeTime(mt5.order_info(self.m_ticket).type_time)

    def get_type_time_description(self):
        """Get order lifetime type as string"""
        time_type = self.TypeTime()
        return self.FormatTypeTime("", time_type.value)

    def get_magic_number(self):
        """Get order magic number"""
        return mt5.order_info(self.m_ticket).magic

    def get_position_id(self):
        """Get position identifier"""
        return mt5.order_info(self.m_ticket).position_id

    def get_position_by_id(self):
        """Get identifier of an opposite position"""
        return mt5.order_info(self.m_ticket).position_by_id

    def get_volume_initial(self):
        """Get initial order volume"""
        return mt5.order_info(self.m_ticket).volume_initial

    def get_volume_current(self):
        """Get current order volume"""
        return mt5.order_info(self.m_ticket).volume_current

    def get_open_price(self):
        """Get order price"""
        return mt5.order_info(self.m_ticket).price_open

    def get_stop_loss(self):
        """Get order stop loss"""
        return mt5.order_info(self.m_ticket).sl

    def get_take_profit(self):
        """Get order take profit"""
        return mt5.order_info(self.m_ticket).tp

    def get_current_price(self):
        """Get current price of the order symbol"""
        symbol = self.Symbol()
        return mt5.symbol_info_tick(symbol).ask if self.OrderType().value % 2 == 0 else mt5.symbol_info_tick(symbol).bid

    def get_stop_limit_price(self):
        """Get the limit order price for the StopLimit order"""
        return mt5.order_info(self.m_ticket).price_stoplimit

    def get_symbol(self):
        """Get order symbol"""
        return mt5.order_info(self.m_ticket).symbol

    def get_comment(self):
        """Get order comment"""
        return mt5.order_info(self.m_ticket).comment

    def get_external_id(self):
        """Get order identifier in an external trading system"""
        return mt5.order_info(self.m_ticket).external_id

    def is_info_integer(self, prop_id, var):
        """Get the value of an integer property"""
        try:
            result = mt5.order_get_integer(self.m_ticket, prop_id)
            if result is not None:
                var = result
                return True
            return False
        except:
            return False

    def is_info_double(self, prop_id, var):
        """Get the value of a double property"""
        try:
            result = mt5.order_get_double(self.m_ticket, prop_id)
            if result is not None:
                var = result
                return True
            return False
        except:
            return False

    def is_info_string(self, prop_id, var):
        """Get the value of a string property"""
        try:
            result = mt5.order_get_string(self.m_ticket, prop_id)
            if result is not None:
                var = result
                return True
            return False
        except:
            return False

    def get_type(self, str_val, type_val):
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

    def get_status(self, str_val, status):
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

    def get_type_filling_str(self, str_val, type_val):
        """Format the order filling type as string"""
        filling_types = {
            0: "Fill or Kill",
            1: "Immediate or Cancel",
            2: "Return"
        }
        return filling_types.get(type_val, "Unknown")

    def get_type_time_str(self, str_val, type_val):
        """Format the order lifetime as string"""
        time_types = {
            0: "GTC",
            1: "Day",
            2: "Specified",
            3: "Specified Day"
        }
        return time_types.get(type_val, "Unknown")

    def get_order(self, str_val):
        """Format the order description"""
        order_info = mt5.order_info(self.m_ticket)
        if order_info is None:
            return "Invalid order"

        order_type = self.get_type("", order_info.type)
        symbol = order_info.symbol
        volume = order_info.volume_current
        price = order_info.price_open
        sl = order_info.sl
        tp = order_info.tp

        return f"{order_type} {symbol} {volume} at {price} sl: {sl} tp: {tp}"

    def get_order_price(self, str_val, price_order, price_trigger, digits):
        """Format the order price"""
        if price_trigger:
            return f"{price_order:.{digits}f} ({price_trigger:.{digits}f})"
        return f"{price_order:.{digits}f}"

    def select(self, ticket=None):
        """Select an order for further work"""
        if ticket is None:
            # Try to select by current ticket
            if self.m_ticket == 0:
                return False
            ticket = self.m_ticket

        order_info = mt5.order_info(ticket)
        if order_info is None:
            return False

        self.m_ticket = ticket
        self.store_state()
        return True

    def select_by_index(self, index):
        """Select an order by index"""
        orders = mt5.orders_get()
        if orders is None or index >= len(orders):
            return False

        return self.select(orders[index].ticket)

    def store_state(self):
        """Store order state"""
        order_info = mt5.order_info(self.m_ticket)
        if order_info is None:
            return

        self.m_type = order_info.type
        self.m_state = order_info.state
        self.m_expiration = order_info.time_expiration
        self.m_volume_curr = order_info.volume_current
        self.m_price_open = order_info.price_open
        self.m_stop_loss = order_info.sl
        self.m_take_profit = order_info.tp

    def check_state(self):
        """Check if order state has changed Returns True if the order state has changed, False otherwise"""
        order_info = mt5.order_info(self.m_ticket)
        if order_info is None:
            return False
            
        if (self.m_type == order_info.type and
            self.m_state == order_info.state and
            self.m_expiration == order_info.time_expiration and
            self.m_volume_curr == order_info.volume_current and
            self.m_price_open == order_info.price_open and
            self.m_stop_loss == order_info.sl and
            self.m_take_profit == order_info.tp):
            return False
            
        # State has changed
        return True



