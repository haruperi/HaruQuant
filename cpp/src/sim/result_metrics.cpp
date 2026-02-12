#include "sim/result_metrics.hpp"

#include <cmath>
#include <limits>

namespace hqt::sim {

namespace {

double population_stddev(const std::vector<double>& values, double mean) {
    if (values.empty()) {
        return 0.0;
    }
    double accum = 0.0;
    for (const double v : values) {
        const double d = v - mean;
        accum += d * d;
    }
    return std::sqrt(accum / static_cast<double>(values.size()));
}

}  // namespace

ResultMetricsSummary ResultMetrics::from_trades(
    const std::vector<TradeRecord>& trades,
    double initial_balance,
    double final_balance) {
    ResultMetricsSummary out;
    out.initial_balance = initial_balance;
    out.final_balance = final_balance;
    out.total_return = out.final_balance - out.initial_balance;
    out.total_return_pct = (out.initial_balance > 0.0)
        ? ((out.total_return / out.initial_balance) * 100.0)
        : 0.0;

    if (trades.empty()) {
        return out;
    }

    out.total_trades = trades.size();
    std::vector<double> trade_returns;
    trade_returns.reserve(trades.size());

    std::vector<double> equity_curve;
    equity_curve.reserve(trades.size() + 1);
    equity_curve.push_back(initial_balance);
    double running_balance = initial_balance;

    for (const auto& t : trades) {
        if (t.profit_loss > 0.0) {
            ++out.winning_trades;
            out.gross_profit += t.profit_loss;
        } else if (t.profit_loss < 0.0) {
            ++out.losing_trades;
            out.gross_loss += -t.profit_loss;
        } else {
            ++out.breakeven_trades;
        }

        if (initial_balance > 0.0) {
            trade_returns.push_back(t.profit_loss / initial_balance);
        } else {
            trade_returns.push_back(0.0);
        }

        running_balance += t.profit_loss;
        equity_curve.push_back(running_balance);
    }

    out.win_rate = (out.total_trades > 0)
        ? (static_cast<double>(out.winning_trades) / static_cast<double>(out.total_trades) * 100.0)
        : 0.0;

    if (out.gross_loss > 0.0) {
        out.profit_factor = out.gross_profit / out.gross_loss;
    } else {
        out.profit_factor = std::numeric_limits<double>::infinity();
    }

    double peak = equity_curve.front();
    for (const double equity : equity_curve) {
        if (equity > peak) {
            peak = equity;
        }
        const double dd_abs = peak - equity;
        const double dd_pct = (peak > 0.0) ? ((dd_abs / peak) * 100.0) : 0.0;
        if (dd_abs > out.max_drawdown) {
            out.max_drawdown = dd_abs;
        }
        if (dd_pct > out.max_drawdown_pct) {
            out.max_drawdown_pct = dd_pct;
        }
    }

    if (trade_returns.size() > 1U) {
        double mean = 0.0;
        for (const double r : trade_returns) {
            mean += r;
        }
        mean /= static_cast<double>(trade_returns.size());

        const double stdev = population_stddev(trade_returns, mean);
        out.sharpe_ratio = (stdev > 0.0)
            ? ((mean / stdev) * std::sqrt(252.0))
            : 0.0;
    }

    return out;
}

}  // namespace hqt::sim

