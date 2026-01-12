
# Things to Keep an Eye On

Successful traders stay informed about market infrastructure, data quality, and regulatory changes that can impact strategy performance.

## Major Reports

Economic reports create volatility and can invalidate technical setups. Be aware of scheduled releases.

**Critical US Economic Reports:**
- **FOMC Announcements**: 8 per year. 2:00 PM ET. Extreme volatility. Many traders avoid entirely or use wide stops
- **Non-Farm Payrolls (NFP)**: First Friday of month, 8:30 AM ET. Major market mover. 30-100 point ES moves common
- **CPI (Inflation)**: Monthly, typically second week. 8:30 AM ET. Increased importance post-2021
- **GDP**: Quarterly. 8:30 AM ET. Major revision potential
- **Retail Sales**: Monthly mid-month. 8:30 AM ET

**Central Bank Decisions:**
- ECB, Bank of England, Bank of Japan - follow if trading currencies or international indices

**Risk Management:**
- Option 1: Don't trade 30 minutes before and after major releases
- Option 2: Widen stops significantly during high-impact news
- Option 3: Close positions before major events
Keep economic calendar visible: www.forexfactory.com or www.investing.com/economic-calendar

## Data Providers

Data quality directly impacts backtest reliability and live trading execution.

**Quality Data Providers:**
- **Premium**: CQG, IQFeed, Rithmic - Expensive ($100-500/month) but highest quality. Recommended for serious trading
- **Good**: Interactive Brokers, TradeStation - Included with account. Decent quality for most purposes
- **Budget**: Kinetick, Google Finance, Yahoo Finance - Cheap/free but quality concerns. OK for learning, not for serious trading

**Data Quality Checks:**
- Compare data across providers for suspicious bars
- Check for gaps in historical data
- Verify contract roll dates for futures
- Watch for bad ticks - outliers that don't match order flow
- For stocks: Check dividend/split adjustments are correct

## Testing Platforms

Platform selection impacts development speed, testing quality, and strategy deployment.

**Popular Platforms:**
- **TradeStation**: EasyLanguage. User-friendly. Good for beginners. Limited flexibility. US customers only
- **MultiCharts**: EasyLanguage compatible. More flexible than TradeStation. Better broker integration. One-time purchase
- **NinjaTrader**: C# based. Free to use, fee for live trading. Popular for futures. Strong community
- **AmiBroker**: AFL language. Fast portfolio backtesting. Budget-friendly ($300 one-time)
- **Python**: Maximum flexibility. Backtrader, Zipline, VectorBT frameworks. Requires programming knowledge
- **Strategy Quant X**: Strategy development and testing. Multiple asset classes. Institutional-grade infrastructure

**Selection Criteria:**
- Asset classes you'll trade
- Programming skill level
- Budget (one-time vs subscription)
- Broker integration availability
- Backtesting speed and capabilities
- Live trading automation support

## Brokers

Monitor broker health and service quality. Be prepared to switch if needed.

**Warning Signs:**
- Frequent platform outages
- Widening spreads or slippage increases
- Delayed withdrawals or fund transfer issues
- Regulatory warnings or investigations
- Sudden policy changes
- Deteriorating customer service

**Best Practice**: Have backup broker account set up and tested. Can switch quickly if primary broker has issues. Keep only necessary trading capital with broker - withdraw excess regularly.

## New Markets

New markets provide fresh opportunities and diversification.

**Emerging Opportunities:**
- Micro futures contracts (MES, MNQ, M2K) - Accessible to smaller accounts
- New crypto derivatives - BTC, ETH futures on CME
- Carbon credits futures
- Battery metals (lithium, cobalt)
- New currency pairs as countries develop

**Evaluation Process:**
- Wait 6-12 months after launch for liquidity to develop
- Monitor volume and open interest growth
- Check bid-ask spreads during target trading hours
- Verify sufficient historical data for backtesting (minimum 2-3 years)
Test strategies on small size before full deployment

##New Regulations

Regulatory changes can dramatically impact strategy viability.

**Recent Impactful Changes:**
- PDT rule (2001) - $25k minimum for day trading stocks
- ESMA restrictions (2018) - Reduced leverage for EU retail traders
- Volcker Rule - Limits proprietary trading by banks
- Crypto regulations - Ongoing changes globally

**Stay Informed:**
- Follow NFA, CFTC, SEC websites and news releases
- Subscribe to broker regulatory updates
- Join trading forums and communities
- Consult with attorney for major regulatory changes
