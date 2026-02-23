/**
FILE: include\engine\clock_service.hpp

PURPOSE:
Defines clock_service.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in clock_service.hpp.
- File-local helpers supporting the main public or internal entry points.

DATA FLOW:
Callers provide requests or data -> this file applies core logic -> outputs state changes or results.

DEPENDENCIES:
- Internal modules: Neighboring headers under cpp/include and shared utility components.
- External systems: Standard C++ library and optional third-party libs linked by CMake.

DESIGN NOTES:
- Keep behavior deterministic for backtest and unit-test reliability.
- Prefer explicit validation and retcode-based failure signaling.
- Preserve low coupling between domains through typed interfaces.
*/
#pragma once

#include "util/timestamp.hpp"

#include <cstdint>
#include <stdexcept>

namespace haruquant {

enum class ClockMode : uint8_t {
    EVENT_TIME = 0,
    PROCESSING_TIME = 1,
};

enum class TimezoneNormalizationPolicy : uint8_t {
    UTC_ONLY = 0,        // Input timestamps are already UTC.
    APPLY_OFFSET = 1,    // Apply offset + optional DST adjustment to get UTC.
    REJECT_NON_UTC = 2,  // Reject non-zero offsets/DST usage.
};

enum class DstPolicy : uint8_t {
    NO_DST = 0,
    APPLY_ONE_HOUR = 1,
    REJECT = 2,
};

struct ClockSnapshot {
    int64_t event_time_us{0};
    int64_t processing_time_us{0};
    int64_t canonical_time_us{0};
    ClockMode mode{ClockMode::EVENT_TIME};
};

class ClockService {
public:
    explicit ClockService(
        ClockMode mode = ClockMode::EVENT_TIME,
        TimezoneNormalizationPolicy tz_policy = TimezoneNormalizationPolicy::UTC_ONLY,
        DstPolicy dst_policy = DstPolicy::NO_DST
    ) noexcept
        : mode_(mode), tz_policy_(tz_policy), dst_policy_(dst_policy) {}

    void set_mode(ClockMode mode) noexcept { mode_ = mode; }
    [[nodiscard]] ClockMode mode() const noexcept { return mode_; }

    void set_timezone_policy(TimezoneNormalizationPolicy policy) noexcept { tz_policy_ = policy; }
    [[nodiscard]] TimezoneNormalizationPolicy timezone_policy() const noexcept { return tz_policy_; }

    void set_dst_policy(DstPolicy policy) noexcept { dst_policy_ = policy; }
    [[nodiscard]] DstPolicy dst_policy() const noexcept { return dst_policy_; }

    void observe_event_time(int64_t event_time_us) noexcept {
        if (event_time_us > event_time_us_) {
            event_time_us_ = event_time_us;
        }
    }

    void observe_processing_time_now() noexcept {
        observe_processing_time(Timestamp::now_us());
    }

    void observe_processing_time(int64_t processing_time_us) noexcept {
        if (processing_time_us > processing_time_us_) {
            processing_time_us_ = processing_time_us;
        }
    }

    [[nodiscard]] int64_t canonical_now() const noexcept {
        if (mode_ == ClockMode::PROCESSING_TIME) {
            return processing_time_us_;
        }
        return event_time_us_;
    }

    [[nodiscard]] ClockSnapshot snapshot() const noexcept {
        return ClockSnapshot{
            .event_time_us = event_time_us_,
            .processing_time_us = processing_time_us_,
            .canonical_time_us = canonical_now(),
            .mode = mode_,
        };
    }

    [[nodiscard]] int64_t normalize_to_utc(
        int64_t timestamp_us,
        int32_t utc_offset_minutes = 0,
        bool is_dst = false
    ) const {
        if (tz_policy_ == TimezoneNormalizationPolicy::UTC_ONLY) {
            return timestamp_us;
        }

        if (tz_policy_ == TimezoneNormalizationPolicy::REJECT_NON_UTC) {
            if (utc_offset_minutes != 0 || is_dst) {
                throw std::invalid_argument("Non-UTC timestamp rejected by policy");
            }
            return timestamp_us;
        }

        int64_t adjusted = timestamp_us - static_cast<int64_t>(utc_offset_minutes) * 60LL * 1'000'000LL;
        if (is_dst) {
            if (dst_policy_ == DstPolicy::REJECT) {
                throw std::invalid_argument("DST timestamp rejected by policy");
            }
            if (dst_policy_ == DstPolicy::APPLY_ONE_HOUR) {
                adjusted -= 3600LL * 1'000'000LL;
            }
        }
        return adjusted;
    }

private:
    ClockMode mode_{ClockMode::EVENT_TIME};
    TimezoneNormalizationPolicy tz_policy_{TimezoneNormalizationPolicy::UTC_ONLY};
    DstPolicy dst_policy_{DstPolicy::NO_DST};
    int64_t event_time_us_{0};
    int64_t processing_time_us_{0};
};

}  // namespace haruquant


