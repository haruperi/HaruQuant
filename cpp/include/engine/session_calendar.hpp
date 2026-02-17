/**
 * @file session_calendar.hpp
 * @brief Session calendar with holiday/hour/timezone/DST constraints.
 */

#pragma once

#include "engine/clock_service.hpp"
#include "trading/symbol_info.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace hqt {

enum class SessionBlockReason : uint8_t {
    NONE = 0,
    UNKNOWN_SYMBOL = 1,
    UNKNOWN_SESSION = 2,
    HOLIDAY = 3,
    OUTSIDE_SESSION = 4,
};

struct SessionGateDecision {
    bool allowed{false};
    SessionBlockReason reason{SessionBlockReason::UNKNOWN_SYMBOL};
};

struct SessionWindow {
    int weekday{1};         // 1=Mon ... 7=Sun
    int start_minute{0};    // inclusive, local session minute
    int end_minute{1440};   // exclusive, local session minute
};

class SessionCalendar {
public:
    SessionCalendar(
        int32_t utc_offset_minutes = 0,
        DstPolicy dst_policy = DstPolicy::NO_DST
    ) noexcept
        : utc_offset_minutes_(utc_offset_minutes), dst_policy_(dst_policy) {}

    void set_timezone_offset_minutes(int32_t offset_minutes) noexcept {
        utc_offset_minutes_ = offset_minutes;
    }

    [[nodiscard]] int32_t timezone_offset_minutes() const noexcept {
        return utc_offset_minutes_;
    }

    void set_dst_policy(DstPolicy policy) noexcept { dst_policy_ = policy; }
    [[nodiscard]] DstPolicy dst_policy() const noexcept { return dst_policy_; }

    void register_session(
        const std::string& session_id,
        const std::vector<SessionWindow>& windows
    ) {
        if (session_id.empty()) {
            throw std::invalid_argument("session_id cannot be empty");
        }
        session_rules_[session_id] = windows;
    }

    void add_holiday(const std::string& session_id, int year, int month, int day) {
        holiday_days_[session_id].insert(day_key(year, month, day));
    }

    void register_symbol(const SymbolInfo& symbol, const std::string& session_id) {
        const uint32_t symbol_id = symbol.SymbolId();
        if (symbol_id == 0) {
            throw std::invalid_argument("symbol must have non-zero SymbolId");
        }
        symbols_[symbol_id] = symbol;
        symbol_sessions_[symbol_id] = session_id;
    }

    [[nodiscard]] std::optional<SymbolInfo> get_symbol_info(uint32_t symbol_id) const {
        const auto it = symbols_.find(symbol_id);
        if (it == symbols_.end()) {
            return std::nullopt;
        }
        return it->second;
    }

    [[nodiscard]] std::optional<std::string> get_symbol_session(uint32_t symbol_id) const {
        const auto it = symbol_sessions_.find(symbol_id);
        if (it == symbol_sessions_.end()) {
            return std::nullopt;
        }
        return it->second;
    }

    [[nodiscard]] SessionGateDecision can_trade_symbol(
        uint32_t symbol_id,
        int64_t timestamp_us,
        bool is_dst = false
    ) const {
        const auto symbol_it = symbols_.find(symbol_id);
        if (symbol_it == symbols_.end()) {
            return {false, SessionBlockReason::UNKNOWN_SYMBOL};
        }

        const auto session_it = symbol_sessions_.find(symbol_id);
        if (session_it == symbol_sessions_.end()) {
            return {false, SessionBlockReason::UNKNOWN_SESSION};
        }
        const std::string& session_id = session_it->second;

        if (!session_rules_.contains(session_id)) {
            return {false, SessionBlockReason::UNKNOWN_SESSION};
        }

        if (is_holiday(session_id, timestamp_us, is_dst)) {
            return {false, SessionBlockReason::HOLIDAY};
        }

        if (!is_open_in_windows(session_rules_.at(session_id), timestamp_us, is_dst)) {
            return {false, SessionBlockReason::OUTSIDE_SESSION};
        }

        return {true, SessionBlockReason::NONE};
    }

    [[nodiscard]] bool is_market_open(
        uint32_t symbol_id,
        int64_t timestamp_us,
        bool is_dst = false
    ) const {
        return can_trade_symbol(symbol_id, timestamp_us, is_dst).allowed;
    }

    [[nodiscard]] std::optional<int64_t> next_open_time(
        uint32_t symbol_id,
        int64_t from_timestamp_us,
        bool is_dst = false,
        int lookahead_days = 14
    ) const {
        const auto session_opt = get_symbol_session(symbol_id);
        if (!session_opt.has_value()) {
            return std::nullopt;
        }
        const auto rules_it = session_rules_.find(*session_opt);
        if (rules_it == session_rules_.end()) {
            return std::nullopt;
        }

        static constexpr int64_t kDayUs = 24LL * 60LL * 60LL * 1'000'000LL;
        int64_t ts = from_timestamp_us;
        for (int d = 0; d < lookahead_days; ++d) {
            const auto local = to_local_parts(ts, is_dst);
            const int weekday = local.weekday;
            const int minute = local.minute_of_day;
            const auto& windows = rules_it->second;

            if (!is_holiday(*session_opt, ts, is_dst)) {
                int best_minute = 24 * 60 + 1;
                for (const auto& w : windows) {
                    if (w.weekday != weekday) {
                        continue;
                    }
                    if (is_minute_in_window(minute, w)) {
                        return ts;
                    }
                    if (minute < w.start_minute) {
                        best_minute = std::min(best_minute, w.start_minute);
                    }
                }

                if (best_minute <= 24 * 60) {
                    return ts + static_cast<int64_t>(best_minute - minute) * 60LL * 1'000'000LL;
                }
            }

            ts = floor_to_local_day(ts, is_dst) + kDayUs;
        }

        return std::nullopt;
    }

private:
    struct LocalParts {
        int year{1970};
        int month{1};
        int day{1};
        int weekday{4};       // 1=Mon ... 7=Sun
        int minute_of_day{0}; // local minute
    };

    [[nodiscard]] static int day_key(int year, int month, int day) {
        return year * 10000 + month * 100 + day;
    }

    [[nodiscard]] int64_t local_offset_us(bool is_dst) const {
        int64_t offset = static_cast<int64_t>(utc_offset_minutes_) * 60LL * 1'000'000LL;
        if (is_dst) {
            if (dst_policy_ == DstPolicy::REJECT) {
                throw std::invalid_argument("DST input rejected by calendar policy");
            }
            if (dst_policy_ == DstPolicy::APPLY_ONE_HOUR) {
                offset += 3600LL * 1'000'000LL;
            }
        }
        return offset;
    }

    [[nodiscard]] LocalParts to_local_parts(int64_t timestamp_us, bool is_dst) const {
        const int64_t local_us = timestamp_us + local_offset_us(is_dst);
        const int64_t seconds = local_us / 1'000'000LL;
        const std::time_t tt = static_cast<std::time_t>(seconds);
        std::tm tm_val{};
#if defined(_WIN32)
        gmtime_s(&tm_val, &tt);
#else
        gmtime_r(&tt, &tm_val);
#endif
        LocalParts out{};
        out.year = tm_val.tm_year + 1900;
        out.month = tm_val.tm_mon + 1;
        out.day = tm_val.tm_mday;
        out.weekday = (tm_val.tm_wday == 0) ? 7 : tm_val.tm_wday;
        out.minute_of_day = tm_val.tm_hour * 60 + tm_val.tm_min;
        return out;
    }

    [[nodiscard]] int64_t floor_to_local_day(int64_t timestamp_us, bool is_dst) const {
        const int64_t local_us = timestamp_us + local_offset_us(is_dst);
        constexpr int64_t kDayUs = 24LL * 60LL * 60LL * 1'000'000LL;
        const int64_t floored_local = (local_us / kDayUs) * kDayUs;
        return floored_local - local_offset_us(is_dst);
    }

    [[nodiscard]] bool is_holiday(
        const std::string& session_id,
        int64_t timestamp_us,
        bool is_dst
    ) const {
        const auto it = holiday_days_.find(session_id);
        if (it == holiday_days_.end()) {
            return false;
        }
        const auto local = to_local_parts(timestamp_us, is_dst);
        return it->second.contains(day_key(local.year, local.month, local.day));
    }

    [[nodiscard]] static bool is_minute_in_window(int minute, const SessionWindow& w) {
        // Same-day window.
        if (w.start_minute <= w.end_minute) {
            return minute >= w.start_minute && minute < w.end_minute;
        }
        // Overnight window (e.g., 22:00 -> 02:00).
        return minute >= w.start_minute || minute < w.end_minute;
    }

    [[nodiscard]] bool is_open_in_windows(
        const std::vector<SessionWindow>& windows,
        int64_t timestamp_us,
        bool is_dst
    ) const {
        const auto local = to_local_parts(timestamp_us, is_dst);
        for (const auto& w : windows) {
            if (w.weekday != local.weekday) {
                continue;
            }
            if (is_minute_in_window(local.minute_of_day, w)) {
                return true;
            }
        }
        return false;
    }

    int32_t utc_offset_minutes_{0};
    DstPolicy dst_policy_{DstPolicy::NO_DST};
    std::unordered_map<std::string, std::vector<SessionWindow>> session_rules_{};
    std::unordered_map<std::string, std::unordered_set<int>> holiday_days_{};
    std::unordered_map<uint32_t, SymbolInfo> symbols_{};
    std::unordered_map<uint32_t, std::string> symbol_sessions_{};
};

}  // namespace hqt

