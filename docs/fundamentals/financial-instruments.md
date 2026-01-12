
# Financial Instruments

Each instrument type has unique characteristics affecting strategy selection, capital requirements, and risk management.

## Futures

Standardized contracts to buy/sell assets at future date. Traded on exchanges (CME, ICE, Eurex).
- **Good liquidity on many markets:** ES, NQ, YM, CL, GC, 6E - excellent liquidity. Many sector and commodity futures available.
- **Leveraged product:** Control large notional value with small margin. ES contract = ~$200k notional with $12k margin. 16:1 leverage.
- **Sometimes high margin requirements:** Full-sized contracts require significant capital. Mini and micro contracts address this (MES, MNQ).
- **Position sizing requires big capital:** Cannot buy fractional contracts. Micro futures help (1/10 mini size).
- **Great diversification:** Access to equities, bonds, currencies, commodities, volatility (VIX) all in one account.
- **Unique strategies:** Seasonality (agricultural), term structure spreads, volatility trading, intermarket spreads.
- **Tax Treatment (US):** Section 1256 (US) - 60/40 rule (60% long-term, 40% short-term regardless of holding period). Generally favorable.

**Considerations:**
- Roll costs/benefits when transitioning between contract months
- Expiration dates require position management
- Some contracts have low liquidity (beware)
- Continuous contract construction important for backtesting

## Stocks/ETFs

Equity shares in companies or exchange-traded funds.
- **Heavily regulated markets**: SEC oversight. Strong investor protection. Transparent pricing.
- **Many sectors, but highly correlated in crises**: 2008, 2020 showed correlations spike to 0.9+ during crashes. Diversification fails when most needed.
- **Day trading rule in US:** Pattern Day Trader (PDT) - 4+ day trades in 5 days require $25k minimum. Significant barrier for small accounts. News is that they are discussing to remove that, might be passed by the time you are reading this.
- **Very difficult to short:** Hard-to-borrow stocks. Costly borrowing fees. Risk of forced buy-in. Short squeezes. Asymmetric risk (limited upside, unlimited downside).
- **Position sizing requires big capital:** Cannot buy fractional shares easily (some brokers now allow). $100 stock requires $100 minimum position.
- **Unique strategies:** End-of-month (EOM) equity buying, Tactical Asset Allocation (TAA) with sector ETFs, pairs trading, relative strength rotation.
- **Tax Treatment (US):** Short-term gains (&lt;1 year) = ordinary income. Long-term gains (&gt;1 year) = preferential rates (0%, 15%, 20%).

**ETF Advantages:**
- Diversification in a single instrument
- Lower risk than individual stocks
- Sector/theme exposure (SPY, QQQ, XLE, IWM)
- Leverage ETFs available (TQQQ 3x, UPRO 3x)

## Forex

Foreign exchange - trading currency pairs.
- **Very liquid:** $6+ trillion daily volume. Major pairs (EUR/USD, GBP/USD, USD/JPY) extremely liquid. Tiny spreads.
- **Picking right broker very important**: Forex brokers vary wildly in quality. Not all regulated equally. Check: NFA (US), FCA (UK), ASIC (Australia). Avoid market makers with conflicts of interest.
- **Many uncorrelated pairs**: EUR/USD, USD/JPY, AUD/USD, GBP/JPY have different drivers. Good diversification opportunities.
- **Very good for position sizing**: Trade any size down to micro lots (1,000 units). Excellent for precise risk management.
- **Good for low capital accounts**: Can start with as low as $100. High leverage available (use carefully - 10:1 max recommended).

**Considerations:**
- Swap/rollover costs for overnight positions
- Major news events create extreme volatility
- 24-hour market - gaps are rare but spreads widen overnight
- Currency risk if account denominated differently

## Crypto

Cryptocurrencies - Bitcoin, Ethereum, altcoins.
- **Great diversifier**: Low correlation to traditional assets. Can perform when stocks/bonds struggle.
- **Limited data history:** Bitcoin since 2010, but meaningful trading only post-2016. Small sample for robust backtesting. Market behavior still evolving.
- **Excellent for position sizing**: Trade any fractional amount. 0.0001 BTC possible.
- **High commissions currently**: 0.1-0.5% per trade typical. Impacts short-term strategies significantly.
- **MC/Binance for full algo trading**: MultiCharts with Binance API currently best option for algorithmic trading with robust data and execution.

**Risks:**
- Extreme volatility - 20-30% moves in days
- Regulatory uncertainty
- Exchange hacks and security risks
- Market manipulation concerns
- Tax complexity (property classification in US)

## CFD

Contracts for Difference - derivative products.
- **Stay away unless no other option**: CFDs are banned in US for good reason. High risk of broker conflicts of interest.
- **Broker-specific products**: Not exchange-traded. Broker is counterparty. If broker fails, your positions/capital at risk.

**Why They're Dangerous:**
- Broker controls pricing - can manipulate spreads
- Stop hunting accusations common
- Your loss is broker's gain (market maker model)
- Limited regulatory protection in many jurisdictions

**Recommendation:** Use regulated futures, forex, or stocks instead whenever possible. However some brokers offering CFDs are highly regulated, so only use those if you trade CFDs, especially Tier 1 regulators.

## Options/Exotic

Derivatives providing right (not obligation) to buy/sell.

**Options Characteristics:**
- Limited risk for buyers (premium paid)
- Time decay - theta works against long options
- Volatility sensitivity - vega risk
- Complex pricing - requires options knowledge
- Can be used for hedging existing positions

**Warning:** Options are complex instruments. Most retail options traders lose money. Requires substantial education before trading. Not recommended for beginners. If using options, start with simple strategies (covered calls, cash-secured puts) before complex multi-leg strategies.
