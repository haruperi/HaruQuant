# Tool, Resource & Prompt Catalog (Playbook §5.2)

## MCP Server: mt5_mcp
| Type | Name | Purpose | Risk Class |
|---|---|---|---|
| Tool | place_order | Execute MT5 order | D |
| Tool | modify_order | Modify pending order | D |
| Tool | close_position | Close open position | D |
| Tool | get_account_info | Read account balance/equity | A |
| Tool | get_symbol_info | Read symbol specifications | A |
| Tool | get_bars | Fetch OHLCV bars | A |
| Tool | get_ticks | Fetch tick data | A |
| Tool | list_positions | List open positions | A |
| Tool | list_orders | List pending orders | A |
| Resource | broker://account_snapshot | Current account state | A |
| Resource | broker://open_orders | Pending order list | A |

## MCP Server: market_data_mcp
| Type | Name | Purpose | Risk Class |
|---|---|---|---|
| Tool | fetch_bars | Fetch historical bars (Dukascopy) | A |
| Resource | market://symbol/{symbol} | Symbol info | A |
| Resource | market://session_calendar | Trading calendar | A |

## MCP Server: risk_analytics_mcp
| Type | Name | Purpose | Risk Class |
|---|---|---|---|
| Tool | calculate_var | Portfolio VaR | A |
| Tool | calculate_cvar | Portfolio CVaR | A |
| Tool | check_correlation_limit | Correlation check | A |
| Resource | risk://policy | Risk policy | A |
| Resource | portfolio://current | Portfolio state | A |

## MCP Server: backtest_mcp
| Type | Name | Purpose | Risk Class |
|---|---|---|---|
| Tool | run_backtest | Execute backtest | A |
| Resource | backtest://results/{id} | Backtest results | A |

## MCP Server: optimization_mcp
| Type | Name | Purpose | Risk Class |
|---|---|---|---|
| Tool | run_backtest_candidate | Test param set | A |
| Tool | run_optimization | Grid/random search | A |

## MCP Server: sql_mcp
| Type | Name | Purpose | Risk Class |
|---|---|---|---|
| Tool | read_query | Execute read-only SQL | A |
