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




