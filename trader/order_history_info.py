import MetaTrader5 as mt5
from datetime import datetime
from .order_enums import OrderType, OrderState, OrderTypeFilling, OrderTypeTime




class OrderHistoryInfo:
    """
    Class for accessing history order information.
    Python equivalent of MQL5's CHistoryOrderInfo class.
    """
    
    def __init__(self):
        """Constructor"""
        self.m_ticket = 0
    
    def get_ticket(self, ticket=None):
        """Get or set the ticket of history order"""
        if ticket is not None:
            self.m_ticket = ticket
        return self.m_ticket
    
    def get_time_setup(self):
        """Get the property value 'ORDER_TIME_SETUP'"""
        return datetime.fromtimestamp(mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_TIME_SETUP))
    
    def get_time_setup_msc(self):
        """Get the property value 'ORDER_TIME_SETUP_MSC'"""
        return mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_TIME_SETUP_MSC)
    
    def get_time_done(self):
        """Get the property value 'ORDER_TIME_DONE'"""
        return datetime.fromtimestamp(mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_TIME_DONE))
    
    def get_time_done_msc(self):
        """Get the property value 'ORDER_TIME_DONE_MSC'"""
        return mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_TIME_DONE_MSC)
    
    def get_order_type(self):
        """Get the property value 'ORDER_TYPE'"""
        return OrderType(mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_TYPE))
    
    def get_type_description(self):
        """Get the property value 'ORDER_TYPE' as string"""
        return self.format_type(self.get_order_type().value)
    
    def get_state(self):
        """Get the property value 'ORDER_STATE'"""
        return OrderState(mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_STATE))
    
    def get_state_description(self):
        """Get the property value 'ORDER_STATE' as string"""
        return self.format_status(self.state().value)
    
    def get_time_expiration(self):
        """Get the property value 'ORDER_TIME_EXPIRATION'"""
        expiration_time = mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_TIME_EXPIRATION)
        if expiration_time:
            return datetime.fromtimestamp(expiration_time)
        return None
    
    def get_type_filling(self):
        """Get the property value 'ORDER_TYPE_FILLING'"""
        return OrderTypeFilling(mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_TYPE_FILLING))
    
    def get_type_filling_description(self):
        """Get the property value 'ORDER_TYPE_FILLING' as string"""
        return self.format_type_filling(self.type_filling().value)
    
    def get_type_time(self):
        """Get the property value 'ORDER_TYPE_TIME'"""
        return OrderTypeTime(mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_TYPE_TIME))
    
    def get_type_time_description(self):
        """Get the property value 'ORDER_TYPE_TIME' as string"""
        return self.format_type_time(self.type_time().value)
    
    def get_magic_number(self):
        """Get the property value 'ORDER_MAGIC'"""
        return mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_MAGIC)
    
    def get_position_id(self):
        """Get the property value 'ORDER_POSITION_ID'"""
        return mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_POSITION_ID)
    
    def get_position_by_id(self):
        """Get the property value 'ORDER_POSITION_BY_ID'"""
        return mt5.history_order_get_integer(self.m_ticket, mt5.ORDER_POSITION_BY_ID)
    
    def get_volume_initial(self):
        """Get the property value 'ORDER_VOLUME_INITIAL'"""
        return mt5.history_order_get_double(self.m_ticket, mt5.ORDER_VOLUME_INITIAL)
    
    def get_volume_current(self):
        """Get the property value 'ORDER_VOLUME_CURRENT'"""
        return mt5.history_order_get_double(self.m_ticket, mt5.ORDER_VOLUME_CURRENT)
    
    def get_open_price(self):
        """Get the property value 'ORDER_PRICE_OPEN'"""
        return mt5.history_order_get_double(self.m_ticket, mt5.ORDER_PRICE_OPEN)
    
    def get_stop_loss(self):
        """Get the property value 'ORDER_SL'"""
        return mt5.history_order_get_double(self.m_ticket, mt5.ORDER_SL)
    
    def get_take_profit(self):
        """Get the property value 'ORDER_TP'"""
        return mt5.history_order_get_double(self.m_ticket, mt5.ORDER_TP)
    
    def get_price_current(self):
        """Get the property value 'ORDER_PRICE_CURRENT'"""
        return mt5.history_order_get_double(self.m_ticket, mt5.ORDER_PRICE_CURRENT)
    
    def get_price_stop_limit(self):
        """Get the property value 'ORDER_PRICE_STOPLIMIT'"""
        return mt5.history_order_get_double(self.m_ticket, mt5.ORDER_PRICE_STOPLIMIT)
    
    def get_symbol(self):
        """Get the property value 'ORDER_SYMBOL'"""
        return mt5.history_order_get_string(self.m_ticket, mt5.ORDER_SYMBOL)
    
    def get_comment(self):
        """Get the property value 'ORDER_COMMENT'"""
        return mt5.history_order_get_string(self.m_ticket, mt5.ORDER_COMMENT)
    
    def get_external_id(self):
        """Get the property value 'ORDER_EXTERNAL_ID'"""
        return mt5.history_order_get_string(self.m_ticket, mt5.ORDER_EXTERNAL_ID)
    
    def get_info_integer(self, prop_id):
        """Access functions OrderGetInteger(...)"""
        return mt5.history_order_get_integer(self.m_ticket, prop_id)
    
    def get_info_double(self, prop_id):
        """Access functions OrderGetDouble(...)"""
        return mt5.history_order_get_double(self.m_ticket, prop_id)
    
    def get_info_string(self, prop_id):
        """Access functions OrderGetString(...)"""
        return mt5.history_order_get_string(self.m_ticket, prop_id)
    
    def get_type(self, order_type):
        """Converts the order type to text"""
        types = {
            0: "buy",
            1: "sell",
            2: "buy limit",
            3: "sell limit",
            4: "buy stop",
            5: "sell stop",
            6: "buy stop limit",
            7: "sell stop limit",
            8: "close by"
        }
        return types.get(order_type, f"unknown order type {order_type}")
    
    def get_status(self, status):
        """Converts the order status to text"""
        statuses = {
            0: "started",
            1: "placed",
            2: "canceled",
            3: "partial",
            4: "filled",
            5: "rejected",
            6: "expired"
        }
        return statuses.get(status, f"unknown order status {status}")
    
    def get_type_filling_str(self, filling_type):
        """Converts the order filling type to text"""
        filling_types = {
            0: "FOK",
            1: "IOC",
            2: "return"
        }
        return filling_types.get(filling_type, f"unknown filling type {filling_type}")
    
    def get_type_time_str(self, time_type):
        """Converts the order time type to text"""
        time_types = {
            0: "GTC",
            1: "day",
            2: "specified",
            3: "specified day"
        }
        return time_types.get(time_type, f"unknown time type {time_type}")
    
    def get_order_str(self):
        """Format order information as a string"""
        return (f"Ticket: {self.m_ticket}, Symbol: {self.get_symbol()}, "
                f"Type: {self.get_type_description()}, Volume: {self.get_volume_initial()}, "
                f"Price: {self.get_open_price()}, SL: {self.get_stop_loss()}, TP: {self.get_take_profit()}, "
                f"State: {self.get_state_description()}")
    
    def get_price_str(self, price_order, price_trigger, digits):
        """Format price information as a string"""
        if price_trigger:
            return f"{price_order:.{digits}f} ({price_trigger:.{digits}f})"
        return f"{price_order:.{digits}f}"
    
    def select_by_index(self, index):
        """Select a history order by its index"""
        # Get all history orders
        from_date = 0  # From the beginning
        to_date = int(datetime.now().timestamp())  # Until now
        
        # Get history orders
        history_orders = mt5.history_orders_get(from_date, to_date)
        if history_orders is None or len(history_orders) <= index:
            return False
        
        # Set the ticket
        self.m_ticket = history_orders[index].ticket
        return True