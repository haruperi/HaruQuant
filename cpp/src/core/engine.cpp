#include "core/engine.hpp"

#include "core/backtest_simulator.hpp"
#include "trading/trade.hpp"
#include "util/logger.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <ctime>
#include <iomanip>
#include <random>
#include <sstream>
#include <string>
#include <unordered_set>
#include <vector>

namespace haruquant::core {

namespace {

double read_double(const BacktestState::Dictionary& row, const std::string& key, double fallback = 0.0) {
    const auto it = row.find(key);
    if (it == row.end()) {
        return fallback;
    }
    try {
        return std::stod(it->second);
    } catch (...) {
        return fallback;
    }
}

long read_long(const BacktestState::Dictionary& row, const std::string& key, long fallback = 0) {
    const auto it = row.find(key);
    if (it == row.end()) {
        return fallback;
    }
    try {
        return static_cast<long>(std::stoll(it->second));
    } catch (...) {
        return fallback;
    }
}

std::string read_string(const BacktestState::Dictionary& row, const std::string& key, const std::string& fallback = "") {
    const auto it = row.find(key);
    if (it == row.end()) {
        return fallback;
    }
    return it->second;
}

std::string to_upper_copy(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    return value;
}

std::string find_symbol_key(const BacktestState::DictionaryMap& symbols, const std::string& symbol) {
    if (symbols.find(symbol) != symbols.end()) {
        return symbol;
    }
    const std::string target = to_upper_copy(symbol);
    for (const auto& [key, _] : symbols) {
        if (to_upper_copy(key) == target) {
            return key;
        }
    }
    return {};
}

long next_ticket(const BacktestState::DictionaryMap& rows) {
    long max_ticket = 0;
    for (const auto& [key, row] : rows) {
        long ticket = 0;
        const auto it = row.find("ticket");
        if (it != row.end()) {
            try {
                ticket = static_cast<long>(std::stoll(it->second));
            } catch (...) {
                ticket = 0;
            }
        }
        if (ticket <= 0) {
            try {
                ticket = static_cast<long>(std::stoll(key));
            } catch (...) {
                ticket = 0;
            }
        }
        max_ticket = std::max(max_ticket, ticket);
    }
    return max_ticket + 1;
}

std::string to_string_num(long value) {
    return std::to_string(value);
}

std::string to_string_num(double value) {
    std::ostringstream oss;
    oss << value;
    return oss.str();
}

int day_key_utc(long unix_ts) {
    if (unix_ts <= 0) {
        return -1;
    }
    std::time_t tt = static_cast<std::time_t>(unix_ts);
    std::tm tm{};
#if defined(_WIN32)
    gmtime_s(&tm, &tt);
#else
    gmtime_r(&tt, &tm);
#endif
    return (tm.tm_year + 1900) * 10000 + (tm.tm_mon + 1) * 100 + tm.tm_mday;
}

std::string format_index_utc(long long index_ns) {
    if (index_ns <= 0) {
        return std::to_string(index_ns);
    }
    long long seconds = index_ns;
    // Accept common epoch units from Python: ns/us/ms/s.
    if (index_ns > 100000000000000LL) {           // ns
        seconds = index_ns / 1000000000LL;
    } else if (index_ns > 100000000000LL) {       // us
        seconds = index_ns / 1000000LL;
    } else if (index_ns > 10000000000LL) {        // ms
        seconds = index_ns / 1000LL;
    }
    const std::time_t tt = static_cast<std::time_t>(seconds);
    std::tm tm{};
#if defined(_WIN32)
    gmtime_s(&tm, &tt);
#else
    gmtime_r(&tt, &tm);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%d %H:%M:%S");
    return oss.str();
}

long long index_to_unix_seconds(long long index_value) {
    if (index_value <= 0) {
        return index_value;
    }
    if (index_value > 100000000000000LL) {           // ns
        return index_value / 1000000000LL;
    }
    if (index_value > 100000000000LL) {              // us
        return index_value / 1000000LL;
    }
    if (index_value > 10000000000LL) {               // ms
        return index_value / 1000LL;
    }
    return index_value;                               // s
}

struct TickEvent {
    long long time_ns{0};
    double close{0.0};
    double bid{0.0};
    double ask{0.0};
    double spread_points{0.0};
};

struct ScheduledSignal {
    long long time_ns{0};
    long long entry_signal{0};
    long long exit_signal{0};
};

std::vector<ScheduledSignal> build_signal_schedule(const std::vector<EngineRunRow>& signal_data) {
    std::vector<ScheduledSignal> out;
    if (signal_data.empty()) {
        return out;
    }
    out.reserve(signal_data.size());
    for (const auto& row : signal_data) {
        if (row.entry_signal == 0 && row.exit_signal == 0) {
            continue;
        }
        out.push_back(ScheduledSignal{
            row.index_ns,
            row.entry_signal,
            row.exit_signal,
        });
    }
    return out;
}

void append_ohlc_ticks(const EngineRunRow& row, std::vector<TickEvent>& out) {
    const bool bullish = row.close >= row.open;
    const double seq[4] = {
        row.open,
        bullish ? row.low : row.high,
        bullish ? row.high : row.low,
        row.close,
    };
    for (int i = 0; i < 4; ++i) {
        TickEvent t{};
        t.time_ns = row.index_ns;
        t.close = seq[i];
        t.spread_points = row.spread_points;
        t.bid = 0.0;
        t.ask = 0.0;
        out.push_back(t);
    }
}

std::vector<TickEvent> build_ticks_ohlc(const std::vector<EngineRunRow>& rows) {
    std::vector<TickEvent> out;
    out.reserve(rows.size() * 4);
    for (const auto& row : rows) {
        append_ohlc_ticks(row, out);
    }
    return out;
}

std::vector<TickEvent> build_ticks_synthetic(const std::vector<EngineRunRow>& rows) {
    std::vector<TickEvent> out;
    auto support_points_for_volume = [](long long ticks) -> long long {
        // MT5-style coarse support-point bands (odd count, capped to 11).
        if (ticks < 8) {
            return 3;
        }
        if (ticks < 16) {
            return 5;
        }
        if (ticks < 32) {
            return 7;
        }
        if (ticks < 64) {
            return 9;
        }
        return 11;
    };

    auto append_linear_segment = [](std::vector<double>& prices, double a, double b, long long count, bool include_start) {
        if (count <= 0) {
            return;
        }
        const long long denom = include_start ? std::max(1LL, count - 1) : count;
        for (long long i = 0; i < count; ++i) {
            if (!include_start && i == 0) {
                continue;
            }
            const long long num = include_start ? i : i + 1;
            const double t = static_cast<double>(num) / static_cast<double>(denom);
            prices.push_back(a + (b - a) * t);
        }
    };

    for (const auto& row : rows) {
        const bool bullish = row.close >= row.open;
        const double open = row.open;
        const double high = row.high;
        const double low = row.low;
        const double close = row.close;
        long long ticks = static_cast<long long>(std::llround(row.volume));
        if (ticks <= 0) {
            ticks = 4;
        }

        // Keep MT5-style special low-volume behavior deterministic.
        if (ticks <= 3) {
            std::vector<double> special_prices{};
            if (ticks == 1) {
                special_prices.push_back(close);
            } else if (ticks == 2) {
                special_prices.push_back(open);
                special_prices.push_back(close);
            } else {
                special_prices.push_back(open);
                special_prices.push_back(bullish ? low : high);
                special_prices.push_back(close);
            }
            for (double px : special_prices) {
                TickEvent t{};
                t.time_ns = row.index_ns;
                t.close = px;
                t.spread_points = row.spread_points;
                t.bid = 0.0;
                t.ask = 0.0;
                out.push_back(t);
            }
            continue;
        }

        const double ext1 = bullish ? low : high;
        const double ext2 = bullish ? high : low;
        const long long support_count = support_points_for_volume(ticks);   // 3/5/7/9/11

        std::vector<double> supports{};
        supports.reserve(static_cast<size_t>(support_count));
        for (long long i = 0; i < support_count; ++i) {
            if (i == 0) {
                supports.push_back(open);
            } else if (i == support_count - 1) {
                supports.push_back(close);
            } else {
                // Alternate swings around O->ext1->ext2->C structure.
                const bool odd = (i % 2 == 1);
                const double a = odd ? ext1 : ext2;
                const double b = odd ? ext2 : ext1;
                const double alpha = static_cast<double>(i) / static_cast<double>(support_count - 1);
                supports.push_back(a + (b - a) * alpha);
            }
        }

        const long long segments = std::max(1LL, support_count - 1);
        long long remaining = ticks;
        std::vector<long long> per_segment(static_cast<size_t>(segments), 1);
        remaining -= segments;
        for (long long i = 0; i < remaining; ++i) {
            per_segment[static_cast<size_t>(i % segments)] += 1;
        }

        std::vector<double> prices{};
        prices.reserve(static_cast<size_t>(ticks));
        for (long long s = 0; s < segments; ++s) {
            append_linear_segment(
                prices,
                supports[static_cast<size_t>(s)],
                supports[static_cast<size_t>(s + 1)],
                per_segment[static_cast<size_t>(s)],
                s == 0);
        }
        if (prices.empty()) {
            prices.push_back(close);
        }
        if (static_cast<long long>(prices.size()) > ticks) {
            prices.resize(static_cast<size_t>(ticks));
        }
        while (static_cast<long long>(prices.size()) < ticks) {
            prices.push_back(close);
        }

        for (double px : prices) {
            TickEvent t{};
            t.time_ns = row.index_ns;
            t.close = px;
            t.spread_points = row.spread_points;
            t.bid = 0.0;
            t.ask = 0.0;
            out.push_back(t);
        }
    }
    return out;
}

std::vector<TickEvent> build_ticks_real(const std::vector<EngineRunRow>& rows) {
    std::vector<TickEvent> out;
    out.reserve(rows.size());
    std::vector<double> known_spread(rows.size(), 0.0);
    for (size_t i = 0; i < rows.size(); ++i) {
        if (rows[i].bid > 0.0 && rows[i].ask > 0.0) {
            known_spread[i] = rows[i].ask - rows[i].bid;
        }
    }

    for (size_t i = 0; i < rows.size(); ++i) {
        const auto& row = rows[i];
        TickEvent t{};
        t.time_ns = row.index_ns;
        t.close = (row.last > 0.0) ? row.last : ((row.bid > 0.0) ? row.bid : row.close);
        t.bid = row.bid;
        t.ask = row.ask;
        t.spread_points = row.spread_points;

        if (t.bid > 0.0 && !(t.ask > 0.0)) {
            double prev_spread = 0.0;
            double next_spread = 0.0;
            for (long long j = static_cast<long long>(i) - 1; j >= 0; --j) {
                if (known_spread[static_cast<size_t>(j)] > 0.0) {
                    prev_spread = known_spread[static_cast<size_t>(j)];
                    break;
                }
            }
            for (size_t j = i + 1; j < rows.size(); ++j) {
                if (known_spread[j] > 0.0) {
                    next_spread = known_spread[j];
                    break;
                }
            }
            double spread = 0.0;
            if (prev_spread > 0.0 && next_spread > 0.0) {
                spread = (prev_spread + next_spread) * 0.5;
            } else if (prev_spread > 0.0) {
                spread = prev_spread;
            } else if (next_spread > 0.0) {
                spread = next_spread;
            }
            t.ask = (spread > 0.0) ? (t.bid + spread) : t.bid;
        }
        if (!(t.bid > 0.0) && t.ask > 0.0) {
            t.bid = t.ask;
        }
        if (!(t.bid > 0.0) && !(t.ask > 0.0)) {
            continue;
        }
        if (!(t.close > 0.0)) {
            t.close = t.bid;
        }
        out.push_back(t);
    }
    return out;
}

}  // namespace

Engine::Engine(const haruquant::trading::AccountInfo& account) : account_(account) {}

void Engine::run(const std::vector<EngineRunRow>& signal_data,
                 const std::vector<EngineRunRow>& execution_data,
                 const std::string& loop_model,
                 const std::string& symbol,
                 long start_unix_sec,
                 long end_unix_sec,
                 const std::string& spread_mode,
                 double spread_points,
                 double spread_min,
                 double spread_max,
                 double trade_volume,
                 bool verbose) {
    const std::string mode = to_upper_copy(spread_mode);
    double point = 0.0;
    double volume_min = 0.0;
    std::string symbol_key{};
    auto shared_state = account_.GetSharedState();
    auto* state = shared_state.get();
    if (!symbol.empty()) {
        if (state != nullptr) {
            symbol_key = find_symbol_key(state->trading_symbols, symbol);
            if (!symbol_key.empty()) {
                const auto it = state->trading_symbols.find(symbol_key);
                if (it != state->trading_symbols.end()) {
                    point = read_double(it->second, "point", 0.0);
                    volume_min = read_double(it->second, "volume_min", 0.0);
                }
            }
        }
    }
    if (!(point > 0.0)) {
        point = 0.00001;
    }
    if (!(volume_min > 0.0)) {
        volume_min = 0.01;
    }
    const double exec_volume = (trade_volume > 0.0) ? trade_volume : volume_min;
    const bool can_trade = (state != nullptr && !symbol_key.empty());
    haruquant::trading::Trade trade(shared_state);
    BacktestSimulator simulator(account_);

    const std::string model = to_upper_copy(loop_model);
    std::vector<TickEvent> ticks{};
    const auto& execution_rows = execution_data.empty() ? signal_data : execution_data;
    if (model == "REAL_TICKS") {
        ticks = build_ticks_real(execution_rows);
    } else if (model == "SYNTHETIC_TICKS") {
        ticks = build_ticks_synthetic(execution_rows);
    } else if (model == "M1_OHLC") {
        ticks = build_ticks_ohlc(execution_rows);
    } else {
        ticks = build_ticks_ohlc(signal_data);
    }
    const auto schedule = build_signal_schedule(signal_data);
    size_t schedule_idx = 0;
    size_t processed_ticks = 0;

    std::mt19937 rng{std::random_device{}()};
    const double lo = std::min(spread_min, spread_max);
    const double hi = std::max(spread_min, spread_max);
    std::uniform_real_distribution<double> dist(lo, hi);

    for (const auto& tick : ticks) {
        const long long row_sec = index_to_unix_seconds(tick.time_ns);
        if (start_unix_sec > 0 && row_sec < start_unix_sec) {
            continue;
        }
        if (end_unix_sec > 0 && row_sec > end_unix_sec) {
            continue;
        }
        ++processed_ticks;

        const double close = tick.close;
        const double eff_spread_points =
            (mode == "FIXED") ? spread_points :
            (mode == "VARIABLE") ? dist(rng) :
            tick.spread_points;
        double bid = tick.bid;
        double ask = tick.ask;
        if (!(bid > 0.0) || !(ask > 0.0)) {
            bid = close;
            ask = close + (eff_spread_points * point);
        }
        if (can_trade) {
            auto sym_it = state->trading_symbols.find(symbol_key);
            if (sym_it != state->trading_symbols.end()) {
                sym_it->second["bid"] = to_string_num(bid);
                sym_it->second["ask"] = to_string_num(ask);
                sym_it->second["last"] = to_string_num(close);
            }
        }

        bool trade_activity = false;
        if (can_trade) {
            long long entry_signal = 0;
            long long exit_signal = 0;
            while (schedule_idx < schedule.size() && tick.time_ns >= schedule[schedule_idx].time_ns) {
                entry_signal = schedule[schedule_idx].entry_signal;
                exit_signal = schedule[schedule_idx].exit_signal;
                ++schedule_idx;
            }

            if (entry_signal == 1) {
                const bool opened = trade.PositionOpen(symbol_key, 0, exec_volume, 0.0, 0.0, 0.0, "engine_buy_signal");
                trade_activity = trade_activity || opened;
                if (verbose && opened) {
                    const long ticket = (trade.ResultDeal() > 0) ? trade.ResultDeal() : trade.ResultOrder();
                    std::ostringstream oss;
                    oss << format_index_utc(tick.time_ns)
                        << " Market BUY " << exec_volume << " " << symbol_key
                        << " " << ticket << " Opened";
                    haruquant::util::info(oss.str());
                }
            } else if (entry_signal == -1) {
                const bool opened = trade.PositionOpen(symbol_key, 1, exec_volume, 0.0, 0.0, 0.0, "engine_sell_signal");
                trade_activity = trade_activity || opened;
                if (verbose && opened) {
                    const long ticket = (trade.ResultDeal() > 0) ? trade.ResultDeal() : trade.ResultOrder();
                    std::ostringstream oss;
                    oss << format_index_utc(tick.time_ns)
                        << " Market SELL " << exec_volume << " " << symbol_key
                        << " " << ticket << " Opened";
                    haruquant::util::info(oss.str());
                }
            }

            if (exit_signal == 1 || exit_signal == -1) {
                const long target_type = (exit_signal == 1) ? 0 : 1;
                struct CloseCandidate {
                    long ticket{0};
                    double volume{0.0};
                };
                std::vector<CloseCandidate> tickets_to_close{};
                for (const auto& [_, pos_row] : state->trading_deals) {
                    if (read_string(pos_row, "entry", "0") != "0") {
                        continue;
                    }
                    const std::string pos_symbol = read_string(pos_row, "symbol", "");
                    if (to_upper_copy(pos_symbol) != to_upper_copy(symbol_key)) {
                        continue;
                    }
                    if (read_long(pos_row, "type", -1) != target_type) {
                        continue;
                    }
                    const long ticket = read_long(pos_row, "ticket", 0);
                    if (ticket > 0) {
                        tickets_to_close.push_back(CloseCandidate{
                            ticket,
                            read_double(pos_row, "volume", 0.0),
                        });
                    }
                }
                for (const auto& close_candidate : tickets_to_close) {
                    const bool closed = trade.PositionClose("", close_candidate.ticket);
                    trade_activity = trade_activity || closed;
                    if (verbose && closed) {
                        std::ostringstream oss;
                        oss << format_index_utc(tick.time_ns)
                            << " Market " << ((target_type == 0) ? "BUY" : "SELL")
                            << " " << close_candidate.volume << " " << symbol_key
                            << " " << close_candidate.ticket << " Closed";
                        haruquant::util::info(oss.str());
                    }
                }
            }
        }

        // Keep simulator state synchronized without doing unnecessary work.
        const bool has_pending_orders = (state != nullptr && !state->trading_orders.empty());
        if (has_pending_orders) {
            monitor_pending_orders_impl(simulator, verbose);
        }
        const bool has_open_positions = (state != nullptr && !state->trading_deals.empty());
        if (has_open_positions) {
            monitor_positions_impl(simulator, verbose);
        }
        if (verbose || trade_activity || has_open_positions) {
            monitor_account(verbose);
        }
    }

    if (verbose) {
        std::ostringstream oss;
        oss << "sim -> engine | model " << model
            << " | signal_rows " << signal_data.size()
            << " | execution_rows " << execution_rows.size()
            << " | generated_ticks " << ticks.size()
            << " | looped_ticks " << processed_ticks;
        haruquant::util::info(oss.str());
    }
}

void Engine::monitor_positions(bool verbose) {
    BacktestSimulator simulator(account_);
    monitor_positions_impl(simulator, verbose);
}

void Engine::monitor_positions_impl(BacktestSimulator& simulator, bool verbose) {
    auto* state = account_.GetSharedState().get();
    if (state == nullptr) {
        return;
    }

    const long now = static_cast<long>(std::time(nullptr));
    const long now_msc = now * 1000;

    struct CloseEvent {
        std::string position_key;
        std::string symbol;
        long position_ticket;
        long order_type;
        double volume;
        double close_price;
        double profit;
        std::string reason;
        std::string comment;
        long magic;
    };
    std::vector<CloseEvent> to_close{};

    for (auto& [position_key, pos_row] : state->trading_deals) {
        const std::string row_entry = read_string(pos_row, "entry", "0");
        if (row_entry != "0") {
            continue;
        }
        const std::string symbol_raw = read_string(pos_row, "symbol", position_key);
        const std::string symbol_key = find_symbol_key(state->trading_symbols, symbol_raw);
        if (symbol_key.empty()) {
            continue;
        }

        const auto sym_it = state->trading_symbols.find(symbol_key);
        if (sym_it == state->trading_symbols.end()) {
            continue;
        }
        const double bid = read_double(sym_it->second, "bid", 0.0);
        const double ask = read_double(sym_it->second, "ask", 0.0);
        if (!(bid > 0.0) || !(ask > 0.0)) {
            continue;
        }

        const long order_type = read_long(pos_row, "type", -1);
        const bool is_buy = (order_type == 0);
        const bool is_sell = (order_type == 1);
        if (!is_buy && !is_sell) {
            continue;
        }

        const double entry_price = read_double(pos_row, "price_open", 0.0);
        const double volume = read_double(pos_row, "volume", 0.0);
        if (!(entry_price > 0.0) || !(volume > 0.0)) {
            continue;
        }

        const double exit_price = is_buy ? bid : ask;
        double profit = 0.0;
        try {
            profit = simulator.order_calc_profit(is_buy ? "BUY" : "SELL", symbol_key, volume, entry_price, exit_price);
        } catch (...) {
            profit = 0.0;
        }

        pos_row["profit"] = to_string_num(profit);
        pos_row["price_current"] = to_string_num(exit_price);
        pos_row["time_update"] = to_string_num(now);
        pos_row["time_update_msc"] = to_string_num(now_msc);

        bool should_close = false;
        std::string close_reason{};
        const double sl = read_double(pos_row, "sl", 0.0);
        const double tp = read_double(pos_row, "tp", 0.0);
        if (is_buy) {
            if (sl > 0.0 && bid <= sl) {
                should_close = true;
                close_reason = "stop_loss";
            } else if (tp > 0.0 && bid >= tp) {
                should_close = true;
                close_reason = "take_profit";
            }
        } else {
            if (sl > 0.0 && ask >= sl) {
                should_close = true;
                close_reason = "stop_loss";
            } else if (tp > 0.0 && ask <= tp) {
                should_close = true;
                close_reason = "take_profit";
            }
        }

        if (should_close) {
            to_close.push_back(CloseEvent{
                position_key,
                symbol_key,
                read_long(pos_row, "ticket", 0),
                order_type,
                volume,
                exit_price,
                profit,
                close_reason,
                read_string(pos_row, "comment"),
                read_long(pos_row, "magic", 0),
            });
        }
    }

    for (const auto& event : to_close) {
        auto pos_it = state->trading_deals.find(event.position_key);
        if (pos_it == state->trading_deals.end()) {
            continue;
        }
        const double current_balance = read_double(state->trading_account, "balance", 0.0);
        state->trading_account["balance"] = to_string_num(current_balance + event.profit);
        auto closed_row = pos_it->second;
        closed_row["profit"] = to_string_num(event.profit);
        closed_row["entry"] = "1";
        closed_row["time_update"] = to_string_num(now);
        closed_row["time_update_msc"] = to_string_num(now_msc);
        const std::string history_key =
            read_string(closed_row, "ticket", event.position_key);
        state->trading_history_deals[history_key] = closed_row;
        state->trading_deals.erase(pos_it);

    }
}

void Engine::monitor_pending_orders(bool verbose) {
    BacktestSimulator simulator(account_);
    monitor_pending_orders_impl(simulator, verbose);
}

void Engine::monitor_pending_orders_impl(BacktestSimulator& simulator, bool verbose) {
    (void) verbose;
    auto* state = account_.GetSharedState().get();
    if (state == nullptr) {
        return;
    }

    const long now = static_cast<long>(std::time(nullptr));
    const long now_msc = now * 1000;

    struct TriggerEvent {
        std::string key;
        BacktestState::Dictionary row;
    };
    std::vector<TriggerEvent> to_trigger{};
    std::vector<std::string> to_expire{};

    for (const auto& [key, row] : state->trading_orders) {
        const std::string action = read_string(row, "action", "");
        if (action != "order_open") {
            continue;
        }

        const long type = read_long(row, "type", -1);
        const bool is_buy_limit = (type == 2);
        const bool is_sell_limit = (type == 3);
        const bool is_buy_stop = (type == 4);
        const bool is_sell_stop = (type == 5);
        if (!is_buy_limit && !is_sell_limit && !is_buy_stop && !is_sell_stop) {
            continue;
        }

        const long type_time = read_long(row, "type_time", 0);       // GTC=0, DAY=1, SPECIFIED=2, SPECIFIED_DAY=3
        const long expiration = read_long(row, "time_expiration", 0);
        bool expired = false;
        if (type_time == 1) { // DAY
            const long setup = read_long(row, "time_setup", 0);
            expired = (day_key_utc(setup) > 0 && day_key_utc(setup) != day_key_utc(now));
        } else if (type_time == 2 || type_time == 3) { // SPECIFIED / SPECIFIED_DAY
            expired = (expiration > 0 && now >= expiration);
        }

        if (expired) {
            to_expire.push_back(key);
            continue;
        }

        const std::string symbol_raw = read_string(row, "symbol", "");
        const std::string symbol_key = find_symbol_key(state->trading_symbols, symbol_raw);
        if (symbol_key.empty()) {
            continue;
        }
        const auto sym_it = state->trading_symbols.find(symbol_key);
        if (sym_it == state->trading_symbols.end()) {
            continue;
        }
        const double bid = read_double(sym_it->second, "bid", 0.0);
        const double ask = read_double(sym_it->second, "ask", 0.0);
        if (!(bid > 0.0) || !(ask > 0.0)) {
            continue;
        }

        const double trigger_price = read_double(row, "price_open", 0.0);
        if (!(trigger_price > 0.0)) {
            continue;
        }

        bool triggered = false;
        if (is_buy_limit) {
            triggered = (ask <= trigger_price);
        } else if (is_sell_limit) {
            triggered = (bid >= trigger_price);
        } else if (is_buy_stop) {
            triggered = (ask >= trigger_price);
        } else if (is_sell_stop) {
            triggered = (bid <= trigger_price);
        }

        if (triggered) {
            to_trigger.push_back(TriggerEvent{key, row});
        }
    }

    // Expire orders first.
    for (const auto& key : to_expire) {
        const auto it = state->trading_orders.find(key);
        if (it == state->trading_orders.end()) {
            continue;
        }
        auto hist_row = it->second;
        hist_row["state"] = "6"; // ORDER_STATE_EXPIRED
        hist_row["time_done"] = to_string_num(now);
        hist_row["time_done_msc"] = to_string_num(now_msc);
        const std::string ticket_key = read_string(hist_row, "ticket", key);
        state->trading_history_orders[ticket_key] = hist_row;
        state->trading_orders.erase(it);
    }

    // Trigger matched pending orders into market deals.
    std::unordered_set<std::string> processed{};
    for (const auto& ev : to_trigger) {
        if (processed.count(ev.key) > 0) {
            continue;
        }
        processed.insert(ev.key);

        auto it = state->trading_orders.find(ev.key);
        if (it == state->trading_orders.end()) {
            continue;
        }
        const auto row = it->second;

        const long pending_type = read_long(row, "type", -1);
        const long deal_side =
            (pending_type == 2 || pending_type == 4) ? 0 : 1; // buy types -> BUY, sell types -> SELL

        TradeRequest req{};
        req.action = 1; // TRADE_ACTION_DEAL
        req.magic = read_long(row, "magic", 0);
        req.symbol = read_string(row, "symbol", "");
        req.volume = read_double(row, "volume_current", 0.0);
        if (!(req.volume > 0.0)) {
            req.volume = read_double(row, "volume_initial", 0.0);
        }
        req.type = deal_side;
        req.price = 0.0; // let order_send use current bid/ask
        req.sl = read_double(row, "sl", 0.0);
        req.tp = read_double(row, "tp", 0.0);
        req.type_filling = read_long(row, "type_filling", 0);
        req.type_time = read_long(row, "type_time", 0);
        req.comment = read_string(row, "comment", "");

        if (!(req.volume > 0.0) || req.symbol.empty()) {
            continue;
        }

        const auto result = simulator.order_send(req);

        auto hist_row = row;
        hist_row["time_done"] = to_string_num(now);
        hist_row["time_done_msc"] = to_string_num(now_msc);
        hist_row["state"] = (result.retcode == 10009) ? "4" : "5"; // filled/rejected
        const std::string ticket_key = read_string(hist_row, "ticket", ev.key);
        state->trading_history_orders[ticket_key] = hist_row;
        state->trading_orders.erase(it);

    }
}

void Engine::monitor_account(bool verbose) {
    auto* state = account_.GetSharedState().get();
    if (state == nullptr) {
        return;
    }

    double total_unrealized_profit = 0.0;
    double used_margin = 0.0;
    for (const auto& [_, pos_row] : state->trading_deals) {
        const std::string row_entry = read_string(pos_row, "entry", "0");
        if (row_entry != "0") {
            continue;
        }
        total_unrealized_profit += read_double(pos_row, "profit", 0.0);
        used_margin += read_double(pos_row, "margin_required", 0.0);
    }

    const double balance = read_double(state->trading_account, "balance", 0.0);
    const double equity = balance + total_unrealized_profit;
    const double free_margin = equity - used_margin;
    const double margin_level = (used_margin > 0.0) ? (equity / used_margin) * 100.0 : 0.0;

    state->trading_account["profit"] = to_string_num(total_unrealized_profit);
    state->trading_account["equity"] = to_string_num(equity);
    state->trading_account["margin"] = to_string_num(used_margin);
    state->trading_account["margin_free"] = to_string_num(free_margin);
    state->trading_account["margin_level"] = to_string_num(margin_level);

    if (verbose) {
        std::ostringstream oss;
        oss << "sim -> account | balance " << balance
            << " | profit " << total_unrealized_profit
            << " | equity " << equity
            << " | margin " << used_margin
            << " | margin_free " << free_margin
            << " | margin_level " << margin_level;
        haruquant::util::info(oss.str());
    }
}

}  // namespace haruquant::core
