/**
 * @file timestamp.hpp
 * @brief Microsecond-precision timestamp utilities
 *
 * All timestamps are stored as int64_t microseconds since Unix epoch (UTC).
 * This provides:
 * - Microsecond precision for tick-level data
 * - Simple arithmetic (difference, comparison)
 * - No timezone ambiguity (always UTC internally)
 * - Y2262 overflow (int64_t microseconds)
 */

#pragma once

#include <cstdint>
#include <ctime>
#include <chrono>
#include <string>

namespace hqt {

/**
 * @brief Timestamp utilities for microsecond-precision time handling
 */
class Timestamp {
public:
    /**
     * @brief Get current UTC time in microseconds since epoch
     * @return Current timestamp
     */
    [[nodiscard]] static int64_t now_us() noexcept {
        auto now = std::chrono::system_clock::now();
        auto duration = now.time_since_epoch();
        return std::chrono::duration_cast<std::chrono::microseconds>(duration).count();
    }

    /**
     * @brief Convert timestamp to ISO 8601 string (UTC)
     * @param timestamp_us Timestamp in microseconds
     * @return ISO 8601 formatted string (e.g., "2026-02-10T14:30:00.123456Z")
     */
    [[nodiscard]] static std::string to_iso8601(int64_t timestamp_us) {
        // Convert to seconds and microseconds
        int64_t seconds = timestamp_us / 1'000'000;
        int64_t microseconds = timestamp_us % 1'000'000;
        if (microseconds < 0) {
            microseconds += 1'000'000;
            seconds -= 1;
        }

        // Convert to time_t and tm
        std::time_t time_t_val = static_cast<std::time_t>(seconds);
        std::tm tm_val;

        #ifdef _WIN32
        gmtime_s(&tm_val, &time_t_val);
        #else
        gmtime_r(&time_t_val, &tm_val);
        #endif

        // Format as ISO 8601
        char buffer[64];
        std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &tm_val);

        // Append microseconds
        char full_buffer[80];
        std::snprintf(full_buffer, sizeof(full_buffer), "%s.%06ldZ",
                     buffer, static_cast<long>(microseconds));

        return std::string(full_buffer);
    }

    /**
     * @brief Parse ISO 8601 string to timestamp
     * @param iso8601 ISO 8601 formatted string
     * @return Timestamp in microseconds (0 if parse fails)
     */
    [[nodiscard]] static int64_t from_iso8601(const std::string& iso8601) noexcept {
        // Basic parsing (simplified - real implementation would be more robust)
        std::tm tm_val = {};
        int microseconds = 0;

        // Try to parse "YYYY-MM-DDTHH:MM:SS.microsZ" format
        #ifdef _WIN32
        int parsed = sscanf_s(iso8601.c_str(), "%4d-%2d-%2dT%2d:%2d:%2d.%6d",
                              &tm_val.tm_year, &tm_val.tm_mon, &tm_val.tm_mday,
                              &tm_val.tm_hour, &tm_val.tm_min, &tm_val.tm_sec,
                              &microseconds);
        #else
        int parsed = std::sscanf(iso8601.c_str(), "%4d-%2d-%2dT%2d:%2d:%2d.%6d",
                                 &tm_val.tm_year, &tm_val.tm_mon, &tm_val.tm_mday,
                                 &tm_val.tm_hour, &tm_val.tm_min, &tm_val.tm_sec,
                                 &microseconds);
        #endif

        if (parsed < 6) return 0;  // Parse failed

        // Adjust tm fields
        tm_val.tm_year -= 1900;  // tm_year is years since 1900
        tm_val.tm_mon -= 1;       // tm_mon is 0-11
        tm_val.tm_isdst = 0;      // UTC, no DST

        // Convert to time_t (seconds since epoch)
        #ifdef _WIN32
        std::time_t seconds = _mkgmtime(&tm_val);
        #else
        std::time_t seconds = timegm(&tm_val);
        #endif

        if (seconds == -1) return 0;  // Conversion failed

        return seconds * 1'000'000 + microseconds;
    }

    /**
     * @brief Convert timestamp to date string (YYYY-MM-DD)
     * @param timestamp_us Timestamp in microseconds
     * @return Date string
     */
    [[nodiscard]] static std::string to_date(int64_t timestamp_us) {
        int64_t seconds = timestamp_us / 1'000'000;
        std::time_t time_t_val = static_cast<std::time_t>(seconds);
        std::tm tm_val;

        #ifdef _WIN32
        gmtime_s(&tm_val, &time_t_val);
        #else
        gmtime_r(&time_t_val, &tm_val);
        #endif

        char buffer[32];
        std::strftime(buffer, sizeof(buffer), "%Y-%m-%d", &tm_val);
        return std::string(buffer);
    }

    /**
     * @brief Get day of week (0=Sunday, 6=Saturday)
     * @param timestamp_us Timestamp in microseconds
     * @return Day of week (0-6)
     */
    [[nodiscard]] static int day_of_week(int64_t timestamp_us) noexcept {
        int64_t seconds = timestamp_us / 1'000'000;
        std::time_t time_t_val = static_cast<std::time_t>(seconds);
        std::tm tm_val;

        #ifdef _WIN32
        gmtime_s(&tm_val, &time_t_val);
        #else
        gmtime_r(&time_t_val, &tm_val);
        #endif

        return tm_val.tm_wday;
    }

    /**
     * @brief Get hour of day (0-23)
     * @param timestamp_us Timestamp in microseconds
     * @return Hour (0-23)
     */
    [[nodiscard]] static int hour_of_day(int64_t timestamp_us) noexcept {
        int64_t seconds = timestamp_us / 1'000'000;
        std::time_t time_t_val = static_cast<std::time_t>(seconds);
        std::tm tm_val;

        #ifdef _WIN32
        gmtime_s(&tm_val, &time_t_val);
        #else
        gmtime_r(&time_t_val, &tm_val);
        #endif

        return tm_val.tm_hour;
    }

    /**
     * @brief Convert microseconds to seconds
     */
    [[nodiscard]] static constexpr int64_t to_seconds(int64_t timestamp_us) noexcept {
        return timestamp_us / 1'000'000;
    }

    /**
     * @brief Convert microseconds to milliseconds
     */
    [[nodiscard]] static constexpr int64_t to_milliseconds(int64_t timestamp_us) noexcept {
        return timestamp_us / 1'000;
    }

    /**
     * @brief Convert seconds to microseconds
     */
    [[nodiscard]] static constexpr int64_t from_seconds(int64_t seconds) noexcept {
        return seconds * 1'000'000;
    }

    /**
     * @brief Convert milliseconds to microseconds
     */
    [[nodiscard]] static constexpr int64_t from_milliseconds(int64_t milliseconds) noexcept {
        return milliseconds * 1'000;
    }

    /**
     * @brief Round timestamp down to start of day (00:00:00 UTC)
     * @param timestamp_us Timestamp in microseconds
     * @return Timestamp at start of day
     */
    [[nodiscard]] static int64_t floor_to_day(int64_t timestamp_us) noexcept {
        constexpr int64_t MICROS_PER_DAY = 86400LL * 1'000'000LL;
        return (timestamp_us / MICROS_PER_DAY) * MICROS_PER_DAY;
    }

    /**
     * @brief Round timestamp down to start of hour
     * @param timestamp_us Timestamp in microseconds
     * @return Timestamp at start of hour
     */
    [[nodiscard]] static int64_t floor_to_hour(int64_t timestamp_us) noexcept {
        constexpr int64_t MICROS_PER_HOUR = 3600LL * 1'000'000LL;
        return (timestamp_us / MICROS_PER_HOUR) * MICROS_PER_HOUR;
    }

    /**
     * @brief Round timestamp down to start of minute
     * @param timestamp_us Timestamp in microseconds
     * @return Timestamp at start of minute
     */
    [[nodiscard]] static int64_t floor_to_minute(int64_t timestamp_us) noexcept {
        constexpr int64_t MICROS_PER_MINUTE = 60LL * 1'000'000LL;
        return (timestamp_us / MICROS_PER_MINUTE) * MICROS_PER_MINUTE;
    }
};

} // namespace hqt
