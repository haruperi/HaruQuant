/**
FILE: include\engine\replay_clock.hpp

PURPOSE:
Defines replay_clock.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in replay_clock.hpp.
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

#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace hqt {

struct ReplayClockState {
    std::size_t cursor{0};
    int64_t current_time_us{0};
    bool paused{false};
    double speed_multiplier{1.0};
    uint64_t timeline_signature{0};
};

class ReplayClock {
public:
    ReplayClock() = default;

    explicit ReplayClock(std::vector<int64_t> timeline_us)
        : timeline_us_(std::move(timeline_us)),
          timeline_signature_(signature_of(timeline_us_)) {}

    void load_timeline(std::vector<int64_t> timeline_us) {
        timeline_us_ = std::move(timeline_us);
        timeline_signature_ = signature_of(timeline_us_);
        reset();
    }

    [[nodiscard]] bool empty() const noexcept { return timeline_us_.empty(); }
    [[nodiscard]] std::size_t size() const noexcept { return timeline_us_.size(); }
    [[nodiscard]] std::size_t cursor() const noexcept { return cursor_; }
    [[nodiscard]] bool paused() const noexcept { return paused_; }
    [[nodiscard]] bool finished() const noexcept { return cursor_ >= timeline_us_.size(); }

    void set_speed_multiplier(double speed) {
        if (speed <= 0.0) {
            throw std::invalid_argument("speed multiplier must be > 0");
        }
        speed_multiplier_ = speed;
    }

    [[nodiscard]] double speed_multiplier() const noexcept { return speed_multiplier_; }

    void pause() noexcept { paused_ = true; }
    void resume() noexcept { paused_ = false; }

    void reset() noexcept {
        cursor_ = 0;
        current_time_us_ = 0;
        paused_ = false;
    }

    [[nodiscard]] std::optional<int64_t> peek_next() const noexcept {
        if (cursor_ >= timeline_us_.size()) {
            return std::nullopt;
        }
        return timeline_us_[cursor_];
    }

    [[nodiscard]] std::optional<int64_t> advance() noexcept {
        if (paused_) {
            return std::nullopt;
        }
        return step_by_bar(1);
    }

    [[nodiscard]] std::optional<int64_t> step_by_bar(std::size_t bars = 1) noexcept {
        if (bars == 0 || cursor_ >= timeline_us_.size()) {
            return std::nullopt;
        }

        const std::size_t remaining = timeline_us_.size() - cursor_;
        const std::size_t take = bars > remaining ? remaining : bars;
        cursor_ += take;
        current_time_us_ = timeline_us_[cursor_ - 1];
        return current_time_us_;
    }

    [[nodiscard]] int64_t current_time() const noexcept { return current_time_us_; }
    [[nodiscard]] uint64_t timeline_signature() const noexcept { return timeline_signature_; }

    [[nodiscard]] ReplayClockState state() const noexcept {
        return ReplayClockState{
            .cursor = cursor_,
            .current_time_us = current_time_us_,
            .paused = paused_,
            .speed_multiplier = speed_multiplier_,
            .timeline_signature = timeline_signature_,
        };
    }

private:
    static uint64_t signature_of(const std::vector<int64_t>& values) noexcept {
        // FNV-1a 64-bit over timeline bytes for deterministic replay fingerprints.
        uint64_t hash = 1469598103934665603ULL;
        for (const auto v : values) {
            uint64_t x = static_cast<uint64_t>(v);
            for (int i = 0; i < 8; ++i) {
                const uint8_t byte = static_cast<uint8_t>((x >> (i * 8)) & 0xFFU);
                hash ^= byte;
                hash *= 1099511628211ULL;
            }
        }
        return hash;
    }

    std::vector<int64_t> timeline_us_{};
    std::size_t cursor_{0};
    int64_t current_time_us_{0};
    bool paused_{false};
    double speed_multiplier_{1.0};
    uint64_t timeline_signature_{signature_of(timeline_us_)};
};

}  // namespace hqt


