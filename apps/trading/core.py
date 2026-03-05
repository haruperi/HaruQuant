"""
Core simulator components.
"""
class DotDict(dict):
    """Dictionary that supports dot notation access to attributes."""
    def __getattr__(self, item):
        if item in self:
            return self[item]
        raise AttributeError(f"No such attribute: {item}")
        
    def __setattr__(self, key, value):
        self[key] = value

class TerminalInfo(DotDict):
    """Container for Terminal information."""
    pass

class DealInfo(DotDict):
    """Container for Deal information."""
    pass
    
class PositionInfo(DotDict):
    """Container for Position information."""
    pass
    
class OrderInfo(DotDict):
    """Container for active Order information."""
    pass
    
class HistoryOrderInfo(DotDict):
    """Container for History Order information."""
    pass
    
class SymbolInfo(DotDict):
    """Container for Symbol information."""
    pass

class SimulatorState:
    """Holds the current state for the backtest simulator."""
    def __init__(self, account_info=None):
        if account_info is not None:
            if hasattr(account_info, '_asdict'):
                self.trading_account = DotDict(account_info._asdict())
            elif isinstance(account_info, dict):
                self.trading_account = DotDict(account_info)
            else:
                self.trading_account = DotDict(vars(account_info))
        else:
            self.trading_account = DotDict()
            
        self.terminal_info = TerminalInfo()
            
        self.trading_symbols = []
        self.trading_deals = []
        self.trading_history_deals = []
        self.trading_orders = []
        self.trading_history_orders = []


def history_deals_get(state: SimulatorState, date_from=None, date_to=None, group=None, ticket=None):
    """Retrieve historical deals from state."""
    deals = state.trading_history_deals
    if ticket is not None:
        deals = [d for d in deals if getattr(d, 'ticket', None) == ticket]
        return tuple(deals)
        
    if date_from is not None and date_to is not None:
        # Convert datetime to timestamp if necessary
        t_from = int(date_from.timestamp()) if hasattr(date_from, 'timestamp') else date_from
        t_to = int(date_to.timestamp()) if hasattr(date_to, 'timestamp') else date_to
        deals = [d for d in deals if t_from <= getattr(d, 'time', 0) <= t_to]
        
    if group is not None:
        suffix = group.replace('*', '')
        deals = [d for d in deals if suffix in getattr(d, 'symbol', '')]
        
    return tuple(deals)

def history_deals_total(state: SimulatorState, date_from, date_to):
    return len(history_deals_get(state, date_from, date_to))


def positions_get(state: SimulatorState, symbol=None, group=None, ticket=None):
    positions = state.trading_deals
    if ticket is not None:
        positions = [p for p in positions if getattr(p, 'ticket', None) == ticket or getattr(p, 'identifier', None) == ticket]
    elif symbol is not None:
        positions = [p for p in positions if getattr(p, 'symbol', '') == symbol]
    elif group is not None:
        suffix = group.replace('*', '')
        positions = [p for p in positions if suffix in getattr(p, 'symbol', '')]
    return tuple(positions)

def positions_total(state: SimulatorState):
    return len(state.trading_deals)


def orders_get(state: SimulatorState, symbol=None, group=None, ticket=None):
    orders = state.trading_orders
    if ticket is not None:
        orders = [o for o in orders if getattr(o, 'ticket', None) == ticket]
    elif symbol is not None:
        orders = [o for o in orders if getattr(o, 'symbol', '') == symbol]
    elif group is not None:
        suffix = group.replace('*', '')
        orders = [o for o in orders if suffix in getattr(o, 'symbol', '')]
    return tuple(orders)

def orders_total(state: SimulatorState):
    return len(state.trading_orders)


def history_orders_get(state: SimulatorState, date_from=None, date_to=None, group=None, ticket=None):
    orders = state.trading_history_orders
    if ticket is not None:
        orders = [o for o in orders if getattr(o, 'ticket', None) == ticket]
        return tuple(orders)
        
    if date_from is not None and date_to is not None:
        t_from = int(date_from.timestamp()) if hasattr(date_from, 'timestamp') else date_from
        t_to = int(date_to.timestamp()) if hasattr(date_to, 'timestamp') else date_to
        orders = [o for o in orders if t_from <= getattr(o, 'time_setup', 0) <= t_to]
        
    if group is not None:
        suffix = group.replace('*', '')
        orders = [o for o in orders if suffix in getattr(o, 'symbol', '')]
        
    return tuple(orders)

def history_orders_total(state: SimulatorState, date_from, date_to):
    return len(history_orders_get(state, date_from, date_to))


def symbols_get(state: SimulatorState, group=None):
    syms = state.trading_symbols
    if group is not None:
        suffix = group.replace('*', '')
        syms = [s for s in syms if suffix in getattr(s, 'name', '')]
    return tuple(syms)

def symbols_total(state: SimulatorState):
    return len(state.trading_symbols)

def symbol_info(state: SimulatorState, name: str):
    syms = [s for s in state.trading_symbols if getattr(s, 'name', '') == name]
    return syms[0] if syms else None


def monitor_positions(
    state: SimulatorState,
    verbose: bool = False,
    allow_auto_close: bool = True,
) -> None:
    """Monitor open positions, update mark-to-market fields, and close on SL/TP."""
    import time

    now = int(time.time())
    now_msc = now * 1000
    to_close = []

    for position in list(state.trading_deals):
        entry = str(getattr(position, "entry", 0))
        if entry != "0":
            continue

        symbol_name = str(getattr(position, "symbol", "") or "")
        if not symbol_name:
            continue

        sym_info = symbol_info(state, symbol_name)
        if sym_info is None:
            continue

        bid = float(getattr(sym_info, "bid", 0.0) or 0.0)
        ask = float(getattr(sym_info, "ask", 0.0) or 0.0)
        if bid <= 0.0 or ask <= 0.0:
            continue

        order_type = int(getattr(position, "type", -1) or -1)
        is_buy = order_type == 0
        is_sell = order_type == 1
        if not is_buy and not is_sell:
            continue

        entry_price = float(
            getattr(position, "price_open", getattr(position, "price", 0.0)) or 0.0
        )
        volume = float(getattr(position, "volume", 0.0) or 0.0)
        if entry_price <= 0.0 or volume <= 0.0:
            continue

        exit_price = bid if is_buy else ask

        # Approximate profit calculation for simulator consistency.
        profit = 0.0
        try:
            contract_size = float(getattr(sym_info, "trade_contract_size", 100000.0) or 100000.0)
            delta = (exit_price - entry_price) if is_buy else (entry_price - exit_price)
            profit = delta * volume * contract_size
        except Exception:
            profit = 0.0

        position.profit = float(profit)
        position.price_current = float(exit_price)
        position.time_update = now
        position.time_update_msc = now_msc

        sl = float(getattr(position, "sl", 0.0) or 0.0)
        tp = float(getattr(position, "tp", 0.0) or 0.0)
        should_close = False
        close_reason = ""

        if is_buy:
            if sl > 0.0 and bid <= sl:
                should_close = True
                close_reason = "stop_loss"
            elif tp > 0.0 and bid >= tp:
                should_close = True
                close_reason = "take_profit"
        else:
            if sl > 0.0 and ask >= sl:
                should_close = True
                close_reason = "stop_loss"
            elif tp > 0.0 and ask <= tp:
                should_close = True
                close_reason = "take_profit"

        if should_close and allow_auto_close:
            to_close.append((position, exit_price, profit, close_reason))
        elif should_close and verbose:
            print(
                f"[monitor_positions] Close condition met (dry-run) "
                f"ticket={int(getattr(position, 'ticket', 0) or 0)} reason={close_reason}"
            )

    for position, close_price, profit, close_reason in to_close:
        if position not in state.trading_deals:
            continue

        balance = float(getattr(state.trading_account, "balance", 0.0) or 0.0)
        state.trading_account.balance = balance + float(profit)

        closed_row = DealInfo(dict(position))
        closed_row.profit = float(profit)
        closed_row.price_current = float(close_price)
        closed_row.entry = 1  # DEAL_ENTRY_OUT
        closed_row.time_update = now
        closed_row.time_update_msc = now_msc
        if not getattr(closed_row, "comment", ""):
            closed_row.comment = str(close_reason)

        state.trading_history_deals.append(closed_row)
        state.trading_deals = [p for p in state.trading_deals if p is not position]

        if verbose:
            print(
                f"[monitor_positions] Closed {getattr(position, 'symbol', '')} "
                f"ticket={int(getattr(position, 'ticket', 0) or 0)} "
                f"reason={close_reason} profit={float(profit):.2f}"
            )


def monitor_pending_orders(
    state: SimulatorState,
    verbose: bool = False,
    allow_auto_trigger: bool = True,
    allow_auto_expire: bool = True,
) -> None:
    """Monitor pending orders, expire them, and trigger matched entries."""
    import time

    now = int(time.time())
    now_msc = now * 1000

    to_expire = []
    to_trigger = []

    def utc_day_key(ts: int) -> int:
        if ts <= 0:
            return 0
        return int(ts // 86400)

    for order in list(state.trading_orders):
        if str(getattr(order, "action", "")) != "order_open":
            continue

        pending_type = int(getattr(order, "type", -1) or -1)
        is_buy_limit = pending_type == 2
        is_sell_limit = pending_type == 3
        is_buy_stop = pending_type == 4
        is_sell_stop = pending_type == 5
        if not (is_buy_limit or is_sell_limit or is_buy_stop or is_sell_stop):
            continue

        type_time = int(getattr(order, "type_time", 0) or 0)
        expiration = int(getattr(order, "time_expiration", 0) or 0)
        expired = False
        if type_time == 1:  # DAY
            setup = int(getattr(order, "time_setup", 0) or 0)
            expired = utc_day_key(setup) > 0 and utc_day_key(setup) != utc_day_key(now)
        elif type_time in (2, 3):  # SPECIFIED / SPECIFIED_DAY
            expired = expiration > 0 and now >= expiration

        if expired:
            to_expire.append(order)
            continue

        symbol_name = str(getattr(order, "symbol", "") or "")
        if not symbol_name:
            continue
        sym_info = symbol_info(state, symbol_name)
        if sym_info is None:
            continue

        bid = float(getattr(sym_info, "bid", 0.0) or 0.0)
        ask = float(getattr(sym_info, "ask", 0.0) or 0.0)
        if bid <= 0.0 or ask <= 0.0:
            continue

        trigger_price = float(
            getattr(order, "price_open", getattr(order, "price_current", 0.0)) or 0.0
        )
        if trigger_price <= 0.0:
            continue

        triggered = False
        if is_buy_limit:
            triggered = ask <= trigger_price
        elif is_sell_limit:
            triggered = bid >= trigger_price
        elif is_buy_stop:
            triggered = ask >= trigger_price
        elif is_sell_stop:
            triggered = bid <= trigger_price

        if triggered:
            to_trigger.append(order)

    if not allow_auto_expire and verbose and to_expire:
        for order in to_expire:
            print(
                f"[monitor_pending_orders] Expire condition met (dry-run) "
                f"ticket={int(getattr(order, 'ticket', 0) or 0)}"
            )

    for order in to_expire:
        if not allow_auto_expire:
            continue
        if order not in state.trading_orders:
            continue
        hist_row = HistoryOrderInfo(dict(order))
        hist_row.state = 6  # ORDER_STATE_EXPIRED
        hist_row.time_done = now
        hist_row.time_done_msc = now_msc
        state.trading_history_orders.append(hist_row)
        state.trading_orders = [o for o in state.trading_orders if o is not order]
        if verbose:
            print(
                f"[monitor_pending_orders] Expired order "
                f"ticket={int(getattr(order, 'ticket', 0) or 0)}"
            )

    if not allow_auto_trigger and verbose and to_trigger:
        for order in to_trigger:
            print(
                f"[monitor_pending_orders] Trigger condition met (dry-run) "
                f"ticket={int(getattr(order, 'ticket', 0) or 0)}"
            )

    processed_tickets = set()
    for order in to_trigger:
        if not allow_auto_trigger:
            continue
        if order not in state.trading_orders:
            continue

        ticket = int(getattr(order, "ticket", 0) or 0)
        if ticket in processed_tickets:
            continue
        processed_tickets.add(ticket)

        pending_type = int(getattr(order, "type", -1) or -1)
        deal_side = 0 if pending_type in (2, 4) else 1

        volume = float(getattr(order, "volume_current", 0.0) or 0.0)
        if volume <= 0.0:
            volume = float(getattr(order, "volume_initial", 0.0) or 0.0)
        symbol_name = str(getattr(order, "symbol", "") or "")
        if volume <= 0.0 or not symbol_name:
            continue

        request = DotDict(
            action=1,  # TRADE_ACTION_DEAL
            magic=int(getattr(order, "magic", 0) or 0),
            symbol=symbol_name,
            volume=volume,
            type=deal_side,
            price=0.0,
            sl=float(getattr(order, "sl", 0.0) or 0.0),
            tp=float(getattr(order, "tp", 0.0) or 0.0),
            type_filling=int(getattr(order, "type_filling", 0) or 0),
            type_time=int(getattr(order, "type_time", 0) or 0),
            comment=str(getattr(order, "comment", "") or ""),
        )

        result = order_send(state, request)

        hist_row = HistoryOrderInfo(dict(order))
        hist_row.time_done = now
        hist_row.time_done_msc = now_msc
        hist_row.state = 4 if int(getattr(result, "retcode", 0) or 0) == 10009 else 5
        state.trading_history_orders.append(hist_row)
        state.trading_orders = [o for o in state.trading_orders if o is not order]

        if verbose:
            print(
                f"[monitor_pending_orders] Triggered order "
                f"ticket={ticket} retcode={int(getattr(result, 'retcode', 0) or 0)}"
            )


def monitor_account(state: SimulatorState, verbose: bool = False) -> None:
    """Monitor account aggregates from open positions."""
    total_unrealized_profit = 0.0
    used_margin = 0.0

    for position in state.trading_deals:
        entry = str(getattr(position, "entry", 0))
        if entry != "0":
            continue
        total_unrealized_profit += float(getattr(position, "profit", 0.0) or 0.0)
        used_margin += float(getattr(position, "margin_required", 0.0) or 0.0)

    balance = float(getattr(state.trading_account, "balance", 0.0) or 0.0)
    equity = balance + total_unrealized_profit
    margin_free = equity - used_margin
    margin_level = (equity / used_margin) * 100.0 if used_margin > 0.0 else 0.0

    state.trading_account.profit = float(total_unrealized_profit)
    state.trading_account.equity = float(equity)
    state.trading_account.margin = float(used_margin)
    state.trading_account.margin_free = float(margin_free)
    state.trading_account.margin_level = float(margin_level)

    if verbose:
        print(
            "sim -> account | "
            f"balance {balance} | "
            f"profit {total_unrealized_profit} | "
            f"equity {equity} | "
            f"margin {used_margin} | "
            f"margin_free {margin_free} | "
            f"margin_level {margin_level}"
        )


def order_send(state: SimulatorState, request) -> DotDict:
    """
    Python port of C++ BacktestSimulator::order_send().
    Processes a TradeRequest (represented as an object with attributes or dict keys)
    and updates the SimulatorState, returning a TradeResult-like dictionary.
    """
    import time
    
    req_get = request.get if isinstance(request, dict) else lambda k, d=None: getattr(request, k, d)
    
    result = DotDict(
        request=request,
        volume=req_get('volume', 0.0),
        retcode=10009,
        deal=0,
        order=0,
        price=0.0,
        comment="Request executed",
        bid=0.0,
        ask=0.0
    )

    action = req_get('action', 0)
    if action == 0:
        action = 1  # TRADE_ACTION_DEAL
        
    is_market_deal = (action == 1)
    is_pending = (action == 5)
    is_sltp = (action == 6)
    is_modify = (action == 7)
    is_remove = (action == 8)
    
    if not is_market_deal and not is_pending and not is_sltp and not is_modify and not is_remove:
        result.retcode = 10013
        result.comment = "Unsupported trade action in tester order_send()"
        return result

    if is_sltp:
        position_ticket = int(req_get('position', 0) or 0)
        symbol_name = req_get('symbol', '')
        sl_value = float(req_get('sl', 0.0))
        tp_value = float(req_get('tp', 0.0))

        positions = state.trading_deals
        if position_ticket > 0:
            positions = [
                p for p in positions
                if getattr(p, 'ticket', None) == position_ticket
                or getattr(p, 'position_id', None) == position_ticket
                or getattr(p, 'identifier', None) == position_ticket
            ]
        if symbol_name:
            positions = [p for p in positions if getattr(p, 'symbol', '') == symbol_name]

        if not positions:
            result.retcode = 10013
            result.comment = "Position not found"
            return result

        now = int(time.time())
        for position in positions:
            position.sl = sl_value
            position.tp = tp_value
            position.time_update = now
            position.time_update_msc = now * 1000

        first = positions[0]
        result.retcode = 10009
        result.deal = int(getattr(first, 'ticket', 0))
        result.order = int(getattr(first, 'order', 0))
        result.price = float(getattr(first, 'price_current', getattr(first, 'price', 0.0)))
        result.comment = "Request executed"
        return result

    if is_modify:
        order_ticket = int(req_get('order', 0) or 0)
        if order_ticket <= 0:
            result.retcode = 10013
            result.comment = "Order ticket is required"
            return result

        pending_order = next((o for o in state.trading_orders if int(getattr(o, 'ticket', 0)) == order_ticket), None)
        if pending_order is None:
            result.retcode = 10013
            result.comment = "Order not found"
            return result

        price = req_get('price', None)
        sl = req_get('sl', None)
        tp = req_get('tp', None)
        stoplimit = req_get('stoplimit', None)
        expiration = req_get('expiration', None)
        type_time = req_get('type_time', None)

        if price is not None:
            pending_order.price_open = float(price)
            pending_order.price_current = float(price)
        if sl is not None:
            pending_order.sl = float(sl)
        if tp is not None:
            pending_order.tp = float(tp)
        if stoplimit is not None:
            pending_order.price_stoplimit = float(stoplimit)
        if expiration is not None:
            pending_order.time_expiration = int(expiration)
        if type_time is not None:
            pending_order.type_time = int(type_time)

        result.retcode = 10009
        result.order = order_ticket
        result.price = float(getattr(pending_order, 'price_open', 0.0))
        result.comment = "Request executed"
        return result

    if is_remove:
        order_ticket = int(req_get('order', 0) or 0)
        if order_ticket <= 0:
            result.retcode = 10013
            result.comment = "Order ticket is required"
            return result

        pending_order = next((o for o in state.trading_orders if int(getattr(o, 'ticket', 0)) == order_ticket), None)
        if pending_order is None:
            result.retcode = 10013
            result.comment = "Order not found"
            return result

        state.trading_orders = [o for o in state.trading_orders if int(getattr(o, 'ticket', 0)) != order_ticket]
        result.retcode = 10009
        result.order = order_ticket
        result.comment = "Request executed"
        return result

    symbol_name = req_get('symbol', '')
    sym_info = symbol_info(state, symbol_name)
    if not sym_info:
        result.retcode = 10013
        result.comment = "Unknown symbol"
        return result

    if result.volume <= 0.0:
        result.retcode = 10014
        result.comment = "Volume must be > 0"
        return result

    bid = getattr(sym_info, 'bid', 0.0)
    ask = getattr(sym_info, 'ask', 0.0)
    last = getattr(sym_info, 'last', 0.0)
    result.bid = bid
    result.ask = ask

    order_type = req_get('type', 0)
    is_buy = (order_type == 0)
    is_sell = (order_type == 1)

    def next_ticket(item_list) -> int:
        if not item_list:
            return 1
        return max((int(getattr(x, 'ticket', 0)) for x in item_list), default=0) + 1

    if is_pending:
        if order_type not in (2, 3, 4, 5):  # BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP
            result.retcode = 10013
            result.comment = "Only BUY_LIMIT/SELL_LIMIT/BUY_STOP/SELL_STOP are supported"
            return result

        pending_price = req_get('price', 0.0)
        if pending_price <= 0.0:
            pending_price = req_get('stoplimit', 0.0)
        if pending_price <= 0.0:
            result.retcode = 10015
            result.comment = "Pending price is invalid"
            return result

        now = int(time.time())
        order_ticket = next_ticket(state.trading_orders)

        # Approximate margin calculation in python (simple fallback)
        margin_required = 0.0

        order_row = OrderInfo(
            action="order_open",
            ticket=order_ticket,
            time_setup=now,
            time_setup_msc=now * 1000,
            time_done=0,
            time_done_msc=0,
            time_expiration=req_get('expiration', 0),
            type=order_type,
            type_time=req_get('type_time', 0),
            type_filling=req_get('type_filling', 0),
            state=1,  # ORDER_STATE_PLACED
            magic=req_get('magic', 0),
            reason=0,
            position_id=0,
            position_by_id=0,
            volume_initial=result.volume,
            volume_current=result.volume,
            price_open=pending_price,
            sl=req_get('sl', 0.0),
            tp=req_get('tp', 0.0),
            price_current=pending_price,
            price_stoplimit=req_get('stoplimit', 0.0),
            symbol=symbol_name,
            comment=req_get('comment', ''),
            external_id="",
            margin_required=margin_required
        )
        
        state.trading_orders.append(order_row)
        
        result.retcode = 10008
        result.order = order_ticket
        result.price = pending_price
        result.comment = "Order placed"
        return result

    close_position_ticket = int(req_get('position', 0) or 0)
    if close_position_ticket > 0:
        open_positions = [
            p for p in state.trading_deals
            if int(getattr(p, 'ticket', 0)) == close_position_ticket
            or int(getattr(p, 'position_id', 0)) == close_position_ticket
            or int(getattr(p, 'identifier', 0)) == close_position_ticket
        ]
        if not open_positions:
            result.retcode = 10013
            result.comment = "Position not found"
            return result

        position = open_positions[0]
        close_volume = float(req_get('volume', 0.0))
        current_volume = float(getattr(position, 'volume', 0.0))
        if close_volume <= 0.0 or close_volume > current_volume:
            result.retcode = 10014
            result.comment = "Volume must be > 0 and <= position volume"
            return result

        exec_price = req_get('price', 0.0)
        if exec_price <= 0.0:
            exec_price = ask if is_buy else bid
        if exec_price <= 0.0:
            exec_price = last
        if exec_price <= 0.0:
            result.retcode = 10015
            result.comment = "Price is invalid and no market quote is available"
            return result

        now = int(time.time())
        order_ticket = next_ticket(state.trading_orders) + next_ticket(state.trading_history_orders)
        deal_ticket = next_ticket(state.trading_deals) + next_ticket(state.trading_history_deals)

        history_order = HistoryOrderInfo(
            ticket=order_ticket,
            time_setup=now,
            time_setup_msc=now * 1000,
            time_done=now,
            time_done_msc=now * 1000,
            time_expiration=req_get('expiration', 0),
            type=order_type,
            type_time=req_get('type_time', 0),
            type_filling=req_get('type_filling', 0),
            state=4,
            magic=req_get('magic', 0),
            reason=0,
            position_id=int(getattr(position, 'position_id', getattr(position, 'ticket', 0))),
            position_by_id=req_get('position_by', 0),
            volume_initial=close_volume,
            volume_current=0.0,
            price_open=exec_price,
            sl=req_get('sl', getattr(position, 'sl', 0.0)),
            tp=req_get('tp', getattr(position, 'tp', 0.0)),
            price_current=exec_price,
            price_stoplimit=req_get('stoplimit', 0.0),
            symbol=symbol_name,
            comment=req_get('comment', ''),
            external_id="",
            margin_required=0.0
        )
        state.trading_history_orders.append(history_order)

        close_deal = DealInfo(
            ticket=deal_ticket,
            order=order_ticket,
            time=now,
            time_msc=now * 1000,
            time_update=now,
            time_update_msc=now * 1000,
            type=order_type,
            entry=1, # DEAL_ENTRY_OUT
            magic=req_get('magic', 0),
            reason=0,
            position_id=int(getattr(position, 'position_id', getattr(position, 'ticket', 0))),
            volume=close_volume,
            price=exec_price,
            price_open=float(getattr(position, 'price_open', getattr(position, 'price', exec_price))),
            price_current=exec_price,
            sl=float(getattr(position, 'sl', 0.0)),
            tp=float(getattr(position, 'tp', 0.0)),
            margin_required=0.0,
            commission=0.0,
            swap=0.0,
            profit=0.0,
            fee=0.0,
            symbol=symbol_name,
            comment=req_get('comment', ''),
            external_id=""
        )
        state.trading_history_deals.append(close_deal)

        remaining = current_volume - close_volume
        if remaining <= 0.0:
            state.trading_deals = [p for p in state.trading_deals if p is not position]
        else:
            position.volume = remaining
            position.time_update = now
            position.time_update_msc = now * 1000

        result.retcode = 10009
        result.deal = deal_ticket
        result.order = order_ticket
        result.price = exec_price
        result.comment = "Request executed"
        return result

    if not is_buy and not is_sell:
        result.retcode = 10013
        result.comment = "Only BUY/SELL are supported in tester order_send()"
        return result

    exec_price = req_get('price', 0.0)
    if exec_price <= 0.0:
        exec_price = ask if is_buy else bid
    if exec_price <= 0.0:
        exec_price = last
    if exec_price <= 0.0:
        result.retcode = 10015
        result.comment = "Price is invalid and no market quote is available"
        return result

    now = int(time.time())
    
    order_ticket = next_ticket(state.trading_orders) + next_ticket(state.trading_history_orders)
    deal_ticket = next_ticket(state.trading_deals) + next_ticket(state.trading_history_deals)
    position_ticket = deal_ticket

    margin_required = 0.0

    order_row = HistoryOrderInfo(
        ticket=order_ticket,
        time_setup=now,
        time_setup_msc=now * 1000,
        time_done=now,
        time_done_msc=now * 1000,
        time_expiration=req_get('expiration', 0),
        type=order_type,
        type_time=req_get('type_time', 0),
        type_filling=req_get('type_filling', 0),
        state=4,  # ORDER_STATE_FILLED
        magic=req_get('magic', 0),
        reason=0,
        position_id=position_ticket,
        position_by_id=req_get('position_by', 0),
        volume_initial=result.volume,
        volume_current=0.0,
        price_open=exec_price,
        sl=req_get('sl', 0.0),
        tp=req_get('tp', 0.0),
        price_current=exec_price,
        price_stoplimit=req_get('stoplimit', 0.0),
        symbol=symbol_name,
        comment=req_get('comment', ''),
        external_id="",
        margin_required=margin_required
    )
    
    state.trading_history_orders.append(order_row)

    deal_row = DealInfo(
        ticket=deal_ticket,
        order=order_ticket,
        time=now,
        time_msc=now * 1000,
        time_update=now,
        time_update_msc=now * 1000,
        type=order_type,
        entry=0, # DEAL_ENTRY_IN
        magic=req_get('magic', 0),
        reason=0,
        position_id=position_ticket,
        volume=result.volume,
        price=exec_price,
        price_open=exec_price,
        price_current=exec_price,
        sl=req_get('sl', 0.0),
        tp=req_get('tp', 0.0),
        margin_required=margin_required,
        commission=0.0,
        swap=0.0,
        profit=0.0,
        fee=0.0,
        symbol=symbol_name,
        comment=req_get('comment', ''),
        external_id=""
    )
    
    state.trading_deals.append(deal_row)

    result.retcode = 10009
    result.deal = deal_ticket
    result.order = order_ticket
    result.price = exec_price
    result.comment = "Request executed"
    return result
