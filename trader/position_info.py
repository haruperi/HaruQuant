import MetaTrader5 as mt5
from .order_enums import EnumPositionType, EnumPositionPropertyInteger, EnumPositionPropertyDouble, EnumPositionPropertyString, EnumAccountMarginMode
from datetime import datetime



class CPositionInfo:
    def __init__(self):
        self.m_type = EnumPositionType.WRONG_VALUE
        self.m_volume = 0.0
        self.m_price = 0.0
        self.m_stop_loss = 0.0
        self.m_take_profit = 0.0

    def get_ticket(self):
        """Get the property value position ticket"""
        return mt5.positions_get()[0].ticket if mt5.positions_total() > 0 else 0

    def get_time_setup(self):
        """Get the property value position setup"""
        return mt5.positions_get()[0].time if mt5.positions_total() > 0 else 0

    def get_time_setup_msc(self):
        """Get the property value position setup_msc"""
        return mt5.positions_get()[0].time_msc if mt5.positions_total() > 0 else 0

    def get_time_update(self):
        """Get the property value position update"""
        return mt5.positions_get()[0].time_update if mt5.positions_total() > 0 else 0

    def get_time_update_msc(self):
        """Get the property value position update_msc"""
        return mt5.positions_get()[0].time_update_msc if mt5.positions_total() > 0 else 0

    def get_position_type(self):
        """Get the property value position type"""
        if mt5.positions_total() > 0:
            pos_type = mt5.positions_get()[0].type
            return EnumPositionType.POSITION_TYPE_BUY if pos_type == 0 else EnumPositionType.POSITION_TYPE_SELL
        return EnumPositionType.WRONG_VALUE

    def get_type_description(self):
        """Get the property value position type as string"""
        str_type = ""
        return self.get_type(str_type, self.get_position_type())

    def get_magic_number(self):
        """Get the property value position magic_number"""
        return mt5.positions_get()[0].magic if mt5.positions_total() > 0 else 0

    def get_identifier(self):
        """Get the property value position identifier"""
        return mt5.positions_get()[0].identifier if mt5.positions_total() > 0 else 0

    def get_volume(self):
        """Get the property value position volume"""
        return mt5.positions_get()[0].volume if mt5.positions_total() > 0 else 0.0

    def get_open_price(self):
        """Get the property value position open_price"""
        return mt5.positions_get()[0].price_open if mt5.positions_total() > 0 else 0.0

    def get_stop_loss(self):
        """Get the property value position stop_loss"""
        return mt5.positions_get()[0].sl if mt5.positions_total() > 0 else 0.0

    def get_take_profit(self):
        """Get the property value position take_profit"""
        return mt5.positions_get()[0].tp if mt5.positions_total() > 0 else 0.0

    def get_current_price(self):
        """Get the property value position current_price"""
        return mt5.positions_get()[0].price_current if mt5.positions_total() > 0 else 0.0

    def get_commission(self):
        """Get the property value position commission"""
        return mt5.positions_get()[0].commission if mt5.positions_total() > 0 else 0.0

    def get_swap(self):
        """Get the property value position swap"""
        return mt5.positions_get()[0].swap if mt5.positions_total() > 0 else 0.0

    def get_profit(self):
        """Get the property value position profit"""
        return mt5.positions_get()[0].profit if mt5.positions_total() > 0 else 0.0

    def get_symbol(self):
        """Get the property value position symbol"""
        return mt5.positions_get()[0].symbol if mt5.positions_total() > 0 else ""

    def get_comment(self):
        """Get the property value position comment"""
        return mt5.positions_get()[0].comment if mt5.positions_total() > 0 else ""

    def get_info_integer(self, prop_id, var):
        """Access functions PositionGetInteger(...)"""
        if mt5.positions_total() > 0:
            position = mt5.positions_get()[0]
            if prop_id == EnumPositionPropertyInteger.POSITION_TICKET:
                var = position.ticket
            elif prop_id == EnumPositionPropertyInteger.POSITION_TIME:
                var = position.time
            elif prop_id == EnumPositionPropertyInteger.POSITION_TIME_MSC:
                var = position.time_msc
            elif prop_id == EnumPositionPropertyInteger.POSITION_TIME_UPDATE:
                var = position.time_update
            elif prop_id == EnumPositionPropertyInteger.POSITION_TIME_UPDATE_MSC:
                var = position.time_update_msc
            elif prop_id == EnumPositionPropertyInteger.POSITION_TYPE:
                var = position.type
            elif prop_id == EnumPositionPropertyInteger.POSITION_MAGIC:
                var = position.magic
            elif prop_id == EnumPositionPropertyInteger.POSITION_IDENTIFIER:
                var = position.identifier
            else:
                return False
            return True
        return False

    def get_info_double(self, prop_id, var):
        """Access functions PositionGetDouble(...)"""
        if mt5.positions_total() > 0:
            position = mt5.positions_get()[0]
            if prop_id == EnumPositionPropertyDouble.POSITION_VOLUME:
                var = position.volume
            elif prop_id == EnumPositionPropertyDouble.POSITION_PRICE_OPEN:
                var = position.price_open
            elif prop_id == EnumPositionPropertyDouble.POSITION_SL:
                var = position.sl
            elif prop_id == EnumPositionPropertyDouble.POSITION_TP:
                var = position.tp
            elif prop_id == EnumPositionPropertyDouble.POSITION_PRICE_CURRENT:
                var = position.price_current
            elif prop_id == EnumPositionPropertyDouble.POSITION_COMMISSION:
                var = position.commission
            elif prop_id == EnumPositionPropertyDouble.POSITION_SWAP:
                var = position.swap
            elif prop_id == EnumPositionPropertyDouble.POSITION_PROFIT:
                var = position.profit
            else:
                return False
            return True
        return False

    def get_info_string(self, prop_id, var):
        """Access functions PositionGetString(...)"""
        if mt5.positions_total() > 0:
            position = mt5.positions_get()[0]
            if prop_id == EnumPositionPropertyString.POSITION_SYMBOL:
                var = position.symbol
            elif prop_id == EnumPositionPropertyString.POSITION_COMMENT:
                var = position.comment
            else:
                return False
            return True
        return False

    def get_type(self, str_type, pos_type):
        """Converts the position type to text"""
        if pos_type == EnumPositionType.POSITION_TYPE_BUY:
            return "buy"
        elif pos_type == EnumPositionType.POSITION_TYPE_SELL:
            return "sell"
        else:
            return f"unknown position type {pos_type}"

    def get_position(self, str_pos):
        """Converts the position parameters to text"""
        symbol_name = self.get_symbol()
        digits = mt5.symbol_info(symbol_name).digits if mt5.symbol_info(symbol_name) else 5
        
        # Get account margin mode
        margin_mode = EnumAccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING  # Default value
        
        # Form the position description
        pos_type = self.get_type("", self.get_position_type())
        
        if margin_mode == EnumAccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:
            str_pos = f"#{self.get_ticket()} {pos_type} {self.get_volume():.2f} {symbol_name} {self.get_open_price():.{digits+3}f}"
        else:
            str_pos = f"{pos_type} {self.get_volume():.2f} {symbol_name} {self.get_open_price():.{digits+3}f}"
        
        # Add stops if there are any
        sl = self.get_stop_loss()
        tp = self.get_take_profit()
        
        if sl != 0.0:
            str_pos += f" sl: {sl:.{digits}f}"
        
        if tp != 0.0:
            str_pos += f" tp: {tp:.{digits}f}"
        
        return str_pos

    def select(self, symbol):
        """Access functions PositionSelect(...)"""
        positions = mt5.positions_get(symbol=symbol)
        return len(positions) > 0

    def select_by_magic(self, symbol, magic):
        """Access functions PositionSelect(...) by magic number"""
        positions = mt5.positions_get(symbol=symbol)
        for position in positions:
            if position.magic == magic:
                return True
        return False

    def select_by_ticket(self, ticket):
        """Access functions PositionSelectByTicket(...)"""
        positions = mt5.positions_get(ticket=ticket)
        return len(positions) > 0

    def select_by_index(self, index):
        """Select a position on the index"""
        positions = mt5.positions_get()
        if 0 <= index < len(positions):
            return True
        return False

    def store_state(self):
        """Stored position's current state"""
        self.m_type = self.get_position_type()
        self.m_volume = self.get_volume()
        self.m_price = self.get_open_price()
        self.m_stop_loss = self.get_stop_loss()
        self.m_take_profit = self.get_take_profit()

    def check_state(self):
        """Check position change"""
        if (self.m_type == self.get_position_type() and
            self.m_volume == self.get_volume() and
            self.m_price == self.get_open_price() and
            self.m_stop_loss == self.get_stop_loss() and
            self.m_take_profit == self.get_take_profit()):
            return False
        return True