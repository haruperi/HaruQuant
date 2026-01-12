# Key Concepts

## Right Mindset
Developing the proper trading mindset is foundational to long-term success. This involves accepting uncertainty, embracing probabilistic thinking, and maintaining emotional discipline.

- **Probabilistic Thinking**: No single trade defines your success. Think in terms of expected value across hundreds of trades. A 60% win rate means 40% of trades will lose--this is expected.
- **Detachment from Outcomes**: Judge yourself by process quality, not individual trade results. A well-executed trade that loses money is still a good trade. A poorly executed trade that makes money is still a bad trade.
- **Patience and Discipline**: Wait for your edge to appear. Don't force trades. The market doesn't care about your need to trade or make money today. Most of your profits will come from a small percentage of trades. Consistency trumps intensity.
- **Continuous Improvement**: View losses as tuition paid to the market. Keep detailed records, analyze mistakes objectively, and constantly refine your approach without over-optimizing.

The Dunning-Kruger effect describes the psychological journey of a trader. Initially, new traders may overestimate their abilities, but as they gain more experience, skills, and knowledge, they realise there is much more to learn. This often leads to a decrease in confidence as they become aware of their own ignorance. When you go through the dips, commit to learning the new material and focus on the long-term benefits. Working through these challenges increases both experience and confidence in the long run.

## Right Knowledge
Success in trading requires distinguishing between market myths and evidence-based practices. Build knowledge through rigorous testing rather than accepting conventional wisdom.

### Dispose of All Myths
- **Myth**: You need to watch charts all day long on multiple monitors, looking for opportunities to trade
**Reality**: There is no evidence to support this, personally I have actually made more money from trading without looking at the charts.
- **Myth**: Forecasting the future price of financial instruments is important to be a profitable trader.
**Reality**: This is a major misconception. No one can consistently and accurately predict the future. Profitable trading is not about prediction; it's about probability and risk management. Successful traders use a system that gives them a statistical "edge" over many trades. They know they will be wrong often, but they manage their risk so that their winning trades are (on average) larger than their losing trades.
- **Myth**: Trading is like gambling with huge luck swings.
**Reality**: Trading without a plan, a strategy, and risk management is gambling. However, professional trading is a business of probabilities. While luck affects any single trade, a successful trader relies on a tested strategy that has a positive expectancy over the long run. A gambler has a negative expectancy (the house always wins); a skilled trader aims for a positive one.
- **Myth**: Trading is the fastest way to get rich.
**Reality**: This is perhaps the most dangerous myth. Trading is, in fact, one of the fastest ways to get poor. The pressure to "get rich quick" causes traders to take massive, unmanaged risks. Building real, sustainable wealth from trading is a skill that takes years to develop and is typically a slow, compounding process, not an overnight jackpot.
- **Myth**: High leverage is the best way to get more profits through trading.
**Reality**: Leverage is a double-edged sword: it magnifies both gains and losses. While it can amplify profits, it is far more likely to amplify a new trader's losses, leading to a "blown-up" account (losing all your money). Most professional traders are primarily focused on capital preservation and use leverage very cautiously and strategically, if at all.
- **Myth**: You need to be an expert at reading balance sheets, or keep up with financial news.
**Reality**: This describes fundamental analysis, which is just one school of thought. An entirely different and widely used approach is technical analysis, which ignores news and company fundamentals (like balance sheets) completely. Technical traders believe that all available information is already reflected in the asset's price chart, so they focus only on chart patterns, volume, and price action to make decisions.
- **Myth**: Higher win rate = better strategy.
**Reality**: A 40% win rate with 3:1 reward-to-risk is more profitable than 70% win rate with 1:2 reward-to-risk. Focus on expectancy, not win rate.
- **Myth**: There is a "Holy grail" strategy.
**Reality**: All strategies have periods of underperformance. Success comes from portfolio diversification and proper risk management.

### Arm Yourself with Right Knowledge by Testing

 - Learning the right methodology is very important to start on the right step.
 - Whatever you learn you can take it further or adapt it to your style, but always make sure to test before you commit.
- Build knowledge through empirical testing rather than theory or opinion. Every assumption about the market should be validated with data.

##  Keep Your Eye on the Process, Not the Outcome
 - By focusing on the process of doing things the right way, every time, all the time, you get out of the way to achieve success.
 - Focusing on the outcome will cloud your judgement and most likely limit your actions.
 - Short-term results are largely random; long-term results reflect process quality.

##  A Case for Algo Trading in a Portfolio
For years, I was a Discretionary Trader, and I must confess that it's extremely difficult and, in most cases, rarely profitable long-term. Because you have a lot of variables to deal with, and the biggest one is yourself. Plus, you can't have a sustainable business where your absence affects income, that's definitely any issue long term especially if you want to have a business that can function irrespective of your presence. So, you might start off as a Discretionary Trader, but I highly encourage you to pivot to Algo Trading as soon as possible. All things being equal, if you start off as an Algo trader the better, you have fewer variables to deal with.
Systematic, algorithmic trading in a diversified portfolio is the most reliable path to consistent returns.

### Why Algorithmic Trading
- **Speed and Accuracy**: Computers can calculate and execute trades in a fraction of a second, significantly faster and more accurately than humans, reducing errors.
- **Diversification**: Since computers handle all monitoring and calculations, you can trade hundreds of strategies across various instruments, diversifying your portfolio more effectively.
- **No Emotions**: Algorithmic trading eliminates emotional biases like fear, greed, or fear of missing out, as the computer strictly follows the predefined rules.
- **Time Saving**: Once strategies are developed, tested, and deployed, the computer performs the trading, freeing up your time.
- **Backtesting**: Allows you to test trading ideas faster against historical data to eliminate unprofitable strategies before risking real capital.

### Portfolio Approach Benefits
- Algo trading makes it easier to manage portfolio trading.
- Portfolio trading reduces equity curve volatility through diversification
- Smooths returns - when one strategy struggles, others may profit
- Lowers maximum drawdown compared to single strategy
- Increases Sharpe ratio through reduced volatility
- Provides psychological comfort during individual strategy drawdowns

## Losses and Drawdowns are Normal
Losses are the cost of doing business in trading. Even the best strategies have losing periods. Understanding and accepting this is crucial for psychological survival. Expect them and plan for this.

### Expected Drawdown Characteristics

- Profitable strategies can experience 20-35% drawdowns. However, it's up to you to decide the drawdown levels you are comfortable with during development.
- Strategy drawdowns can last 3-12 months even in good strategies.
- Live trading often experiences larger drawdowns than backtest suggest
- Losing streaks of 5-10 trades are common even with a 60%-win rate

![Graph showing probability distribution curve with trading outcomes, illustrating that most trades cluster around break-even while extreme wins and losses occur less frequently, demonstrating the normal distribution of trading results that successful traders must accept and plan for](/img/probabilities.png)


### Managing Drawdowns

- Set maximum acceptable drawdown before going live (e.g., 10-15%).
Its important to note here that live drawdown is usually greater than backtest drawdown, so the tip here is whatever drawdown you are comfortable with, cut that in half in the backtest. For example, if you are comfortable with a 10% drawdown in live trading then, your maximum drawdown in backtest should be 5%.
- Use Monte Carlo simulation to estimate worst-case scenarios
- Don't abandon strategies during normal drawdown ranges
- Consider reducing position size during extended drawdowns
- Keep adequate capital reserves to survive expected drawdowns

## Avoid Risk of Ruin
Risk of ruin is the probability of losing so much capital that you cannot continue trading. This must be kept near zero through proper position sizing and risk management.

**Risk of Ruin Formula:**
For a given win rate (W), average win (AW), and average loss (AL), the risk of ruin depends on the percentage of capital risked per trade.
**Example:** If you risk 10% per trade with a 50% win rate and 1:1 reward-to-risk, your risk of ruin approaches 100%. If you risk 1% per trade with the same parameters, risk of ruin is near zero. The difference is survival.

![Risk of ruin probability chart showing exponential increase in bankruptcy risk as position size grows, with x-axis displaying percentage of capital risked per trade from 0% to 25% and y-axis showing risk of ruin from 0% to 100%, demonstrating how risking just 10% per trade approaches certain financial ruin while keeping risk below 2% maintains survivability in trading](/img/riskofruin.png)


**Protection Strategies**

- Never risk more than 1-2% of the account per trade idea.
- Limit total portfolio heat to 5-10% of account value
- Maintain positive expectancy (expected value > 0)
- Use catastrophic stops to prevent single-trade disasters
- Keep 6-12 months of living expenses separate from trading capital
- Start with adequate capital for your instrument (discussed more later)

## Trading is a Business
Treat trading as a professional business with proper planning, infrastructure, record-keeping, and continuous improvement processes, not just a hobby.
Trading is a skill, that will take time and effort on your part to get good at.
Having a plan with a clear process is important to success.
Not overloading your business with high profit requirements will get you faster to success.
There is no one best way to trade, it all depends on you, your age, geography, capital, character, available markets, target drawdown, target profits, etc.

### Business Components

- **Business Plan**: Define goals, strategies, risk parameters, and success metrics. Review and update quarterly.
- **Operating Expenses**: Data feeds ($50-500/month), platform costs, VPS hosting, education, and software tools.
- **Accounting**: Track all expenses, commission, and slippage. Maintain detailed P&L records for tax purposes.
- **Performance Review**: Monthly performance meetings with yourself. What worked? What didn't? What needs adjustment?
- **Reinvestment**: Allocate portion of profits to better tools, education, and system development.
- **Salary Structure**: Pay yourself a reasonable "salary" from profits, reinvest the rest. Don't withdraw during drawdowns.

### Professional Standards

- Maintain consistent trading hours
- Keep an organized workspace and digital files
- Document all trading decisions and outcomes
- Separate personal and trading finances
- Continuously invest in skill development

## Psychology & Discipline
Trading psychology is often the difference between theoretical profitability and actual profits. Mental discipline prevents self-sabotage.

### Managing Emotions During Drawdowns
Drawdowns trigger fear, doubt, and the impulse to abandon proven strategies. Emotional management is critical.

**Techniques**

- **Pre-commitment**: Decide in advance your maximum acceptable drawdown and stick to it
- **Context Check**: Compare current drawdown to historical worst-case scenarios from testing
- **Position Sizing Reduction**: Trade smaller size during drawdowns to reduce emotional pressure
- **Stop Monitoring Too Closely**: Check performance weekly instead of daily during drawdowns
- **Portfolio View**: Focus on portfolio performance, not individual strategies
- **Timeline Perspective**: Judge performance over years, not weeks or months

### Sticking to the System
System abandonment during drawdowns is the primary cause of trader failure. Trust is built through thorough testing and realistic expectations.

**When to Stick**

- Drawdown is within historical range from testing
- Individual trade outcomes match expected distributions
- Strategy logic remains sound for current market conditions
- No implementation errors or data quality issues

**When to Abandon**

- Drawdown exceeds 150% of historical worst-case
- Market structure has permanently changed (e.g., new regulations)
- Strategy shows consistent degradation over 12+ months
- Discovery of logic error in strategy implementation

### Trade Journaling for Continuous Improvement
A detailed trade journal captures lessons that would otherwise be lost. It's the foundation for continuous improvement.

**What to Record**

- Entry and exit prices, times, and reasons
- Emotional state before, during, and after trade
- Was the trade executed according to plan?
- Market conditions and any unusual events
- Slippage experienced vs expected
- Screenshots of entry setup

**Review Process**

- **Weekly**: Review all trades for execution quality
- **Monthly**: Identify patterns in mistakes or exceptional trades
- **Quarterly**: Assess psychological growth and areas needing work

### When to Override the System (If Ever)
General rule: Never override your system based on feelings or hunches. Rare exceptions exist but must be predefined.

**Acceptable Override Situations (Must Be Pre-Defined)**

- **Extreme News Events**: FOMC announcements, NFP, central bank surprises - predefined no-trade windows
- **Technical Failures**: Internet outage, platform crash - skip trades you can't execute properly
- **Extraordinary Volatility**: Market circuit breakers, flash crashes - predefined volatility filters
- **Data Quality Issues**: Obvious bad ticks or data errors affecting signals

**Never Override Based On**

- "Feeling" the market will move differently
- Recent winning or losing streak
- News that "seems" important but isn't on predefined list
- Wanting to avoid a loss or lock in a profit early
