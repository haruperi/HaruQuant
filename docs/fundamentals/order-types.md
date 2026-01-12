
# Order Types

Understanding order types is essential for proper strategy execution. Each order type has specific use cases and trade-offs.

## Market

Market orders execute immediately at the next available price, guaranteeing execution but not price.

**Advantages:**
- Guaranteed execution (in liquid markets)
- Simple to implement
- Immediate position entry
- No risk of missing the move

**Disadvantages:**
- Slippage - may receive unfavorable price, especially in fast markets
- Wider spread in low liquidity
- Can be front-run by HFTs in some markets

**Best Use Cases:**
- Highly liquid markets (major futures, forex pairs)
- When exact entry price is not critical to strategy performance
- Close of bar entry signals
- Exit orders for stop loss and profit targets

## Stop

Stop orders (buy stops, sell stops) execute when price reaches or exceeds the specified level, becoming market orders. Mostly used in breakout strategies.
**Buy Stop:** Order placed above current price. Triggers when price rises to trigger level. Used for: long breakout entries, stopping out of short positions.
**Sell Stop:** Order placed below current price. Triggers when price falls to trigger level. Used for: short breakout entries, stopping out of long positions.

**Advantages:**
- Only enters position if breakout occurs
- Confirms momentum before entry
- Perfect for breakout and momentum strategies
- Set-and-forget order placement

**Disadvantages:**
- Slippage on execution - may fill significantly away from trigger in fast markets
- Gap risk - can trigger at much worse price after overnight gap
- May enter into false breakouts
- Execution not guaranteed in extremely fast markets

**Best Practices:**
- Place stop orders 1-3 ticks beyond breakout level to confirm momentum
- Use stop-limit orders to control maximum slippage (with risk of non-execution)
- Account for typical 1-3 tick slippage in backtests
- Cancel unfilled stop orders at end of session for intraday strategies

## Limit

Limit orders are executed only at the specified price or better, guaranteeing price but not execution. Mainly used with mean reversion strategies.
**Buy Limit:** Order placed below current price. Executes at limit price or lower. Used for: buying dips, mean reversion longs, scale-in strategies.
**Sell Limit:** Order placed above current price. Executes at limit price or higher. Used for: selling rallies, mean reversion shorts, profit targets.

**Advantages:**
- Price control - never receive worse than limit price
- Often receive price improvement
- Perfect for mean reversion strategies
- Reduce transaction costs through patient execution

**Disadvantages:**
- No execution guarantee - may never fill
- May miss significant moves if price doesn't reach limit
- Partial fills possible
- Requires order management for unfilled orders

**Best Practices:**
- Place limit orders at support/resistance levels
- Use for scaling into positions - multiple limit orders at different levels
- Set order validity period to avoid stale orders
- In backtests, assume 50-70% fill rate depending on how aggressive limit placement is
