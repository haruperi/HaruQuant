import MetaTrader5 as mt5
from datetime import datetime
from .order_enums import OrderType, OrderState, OrderTypeFilling, OrderTypeTime


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
        self.m_comment = ""
        self.m_magic = 0

    def get_ticket(self):
        """Get order ticket"""
        return self.m_ticket

    def get_time_setup(self):
        """Get order setup time"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return datetime.fromtimestamp(orders[0].time_setup)

    def get_time_done(self):
        """Get order execution or cancellation time"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return datetime.fromtimestamp(orders[0].time_done)

    def get_order_type(self):
        """Get order type"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        else:
            self.m_type = OrderType(orders[0].type)
        return self.m_type

    def get_type_description(self):
        """Get order type as string"""
        if self.m_type is None:
            self.get_order_type()  # This will update self.m_type from mt5.orders_get
        return self.format_type(self.m_type.value)

    def get_state(self):
        """Get order state"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        else:
            self.m_state = OrderState(orders[0].state)
        return self.m_state

    def get_state_description(self):
        """Get order state as string"""
        if self.m_state is None:
            self.get_state()  # This will update self.m_state from mt5.orders_get
            # Check again if m_state is still None
            if self.m_state is None:
                return "Unknown order state: order details not found."
        return self.format_status(self.m_state.value)

    def get_time_expiration(self):
        """Get order expiration time"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        expiration = orders[0].time_expiration
        if expiration > 0:
            self.m_expiration = datetime.fromtimestamp(expiration)

        return self.m_expiration

    def get_type_filling(self):
        """Get order filling type"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return OrderTypeFilling(orders[0].type_filling)

    def get_type_filling_description(self):
        """Get order filling type as string"""
        filling_type = self.get_type_filling()
        return self.format_type_filling(filling_type.value)

    def get_type_time(self):
        """Get order lifetime type"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return OrderTypeTime(orders[0].type_time)

    def get_type_time_description(self):
        """Get order lifetime type as string"""
        time_type = self.get_type_time()
        return self.format_type_time(time_type.value)

    def set_magic(self, magic):
        """Set order magic number"""
        self.m_magic = magic

    def get_magic_number(self):
        """Get order magic number"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return orders[0].magic

    def get_position_id(self):
        """Get position identifier"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return orders[0].position_id

    def get_position_by_id(self):
        """Get identifier of an opposite position"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return orders[0].position_by_id

    def get_volume_initial(self):
        """Get initial order volume"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return orders[0].volume_initial

    def get_volume_current(self):
        """Get current order volume"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        else:
            self.m_volume_curr = orders[0].volume_current
        return self.m_volume_curr

    def get_open_price(self):
        """Get order price"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        else:
            self.m_price_open = orders[0].price_open
        return self.m_price_open

    def get_stop_loss(self):
        """Get order stop loss"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        else:
            self.m_stop_loss = orders[0].sl
        return self.m_stop_loss

    def get_take_profit(self):
        """Get order take profit"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        else:
            self.m_take_profit = orders[0].tp
        return self.m_take_profit

    def get_current_price(self):
        """Get current price of the order symbol"""
        symbol = self.get_symbol()
        tick = mt5.symbol_info_tick(symbol)

        if self.m_type is None:
            self.get_order_type()

        return tick.ask if self.m_type.value % 2 == 0 else tick.bid

    def get_symbol(self):
        """Get order symbol"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return orders[0].symbol

    def set_comment(self, comment):
        """Set order comment"""
        self.m_comment = comment

    def get_comment(self):
        """Get order comment"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None or len(orders) == 0:
            raise Exception(f"Order with ticket {self.m_ticket} not found.")
        return orders[0].comment

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

    def get_order(self):
        """Get order description in string format"""
        orders = mt5.orders_get(ticket=self.m_ticket)
        if orders is None:
            return "Invalid order"

        order_type = self.get_type_description()
        symbol = orders[0].symbol
        volume = orders[0].volume_current
        price = orders[0].price_open
        sl = orders[0].sl
        tp = orders[0].tp

        return f"{order_type} {symbol} {volume} at {price} sl: {sl} tp: {tp}"

    @staticmethod
    def format_price(price_order, price_trigger, digits):
        """Format the order price"""
        if price_trigger:
            return f"{price_order:.{digits}f} ({price_trigger:.{digits}f})"
        return f"{price_order:.{digits}f}"

    def select(self, ticket=None):
        """Select an order for further work"""
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
        orders_get = mt5.orders_get(self.m_ticket)
        if orders_get is None:
            return

        self.m_type = orders_get.type
        self.m_state = orders_get.state
        self.m_expiration = orders_get.time_expiration
        self.m_volume_curr = orders_get.volume_current
        self.m_price_open = orders_get.price_open
        self.m_stop_loss = orders_get.sl
        self.m_take_profit = orders_get.tp

    def check_state(self):
        """Check if order state has changed Returns True if the order state has changed, False otherwise"""
        orders_get = mt5.orders_get(self.m_ticket)
        if orders_get is None:
            return False

        if (self.m_type == orders_get.type and
                self.m_state == orders_get.state and
                self.m_expiration == orders_get.time_expiration and
                self.m_volume_curr == orders_get.volume_current and
                self.m_price_open == orders_get.price_open and
                self.m_stop_loss == orders_get.sl and
                self.m_take_profit == orders_get.tp):
            return False

        # State has changed
        return True
