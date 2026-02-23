/**
FILE: include\engine\event_sequencer.hpp

PURPOSE:
Defines event_sequencer.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in event_sequencer.hpp.
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

#include "engine/event.hpp"

#include <algorithm>
#include <cstdint>
#include <unordered_map>
#include <vector>

namespace haruquant {

struct SequencedEvent {
    Event event{};
    uint32_t stream_id{0};
    uint64_t sequence_no{0};
    uint32_t symbol_id{0};
};

class EventSequencer {
public:
    EventSequencer() = default;

    void push(uint32_t stream_id, const Event& event) {
        const SequencedEvent item{
            .event = event,
            .stream_id = stream_id,
            .sequence_no = next_sequence_++,
            .symbol_id = extract_symbol_id(event),
        };
        all_events_.push_back(item);
        per_symbol_[item.symbol_id].push_back(item);
    }

    template <typename Iter>
    void push_batch(uint32_t stream_id, Iter begin, Iter end) {
        for (auto it = begin; it != end; ++it) {
            push(stream_id, *it);
        }
    }

    [[nodiscard]] std::size_t size() const noexcept { return all_events_.size(); }
    [[nodiscard]] bool empty() const noexcept { return all_events_.empty(); }

    [[nodiscard]] std::vector<Event> ordered_merged() const {
        auto copy = all_events_;
        sort_events(copy);
        std::vector<Event> out;
        out.reserve(copy.size());
        for (const auto& e : copy) {
            out.push_back(e.event);
        }
        return out;
    }

    [[nodiscard]] std::vector<Event> ordered_for_symbol(uint32_t symbol_id) const {
        const auto it = per_symbol_.find(symbol_id);
        if (it == per_symbol_.end()) {
            return {};
        }
        auto copy = it->second;
        sort_events(copy);
        std::vector<Event> out;
        out.reserve(copy.size());
        for (const auto& e : copy) {
            out.push_back(e.event);
        }
        return out;
    }

    [[nodiscard]] std::vector<SequencedEvent> ordered_merged_with_metadata() const {
        auto copy = all_events_;
        sort_events(copy);
        return copy;
    }

    void clear() {
        all_events_.clear();
        per_symbol_.clear();
        next_sequence_ = 0;
    }

private:
    static uint32_t extract_symbol_id(const Event& event) noexcept {
        if (event.type == EventType::TICK) {
            return event.data.tick_data.symbol_id;
        }
        if (event.type == EventType::BAR_CLOSE) {
            return event.data.bar_data.symbol_id;
        }
        return 0;
    }

    static void sort_events(std::vector<SequencedEvent>& events) {
        std::sort(events.begin(), events.end(), [](const SequencedEvent& a, const SequencedEvent& b) {
            if (a.event.timestamp_us != b.event.timestamp_us) {
                return a.event.timestamp_us < b.event.timestamp_us;
            }
            if (a.symbol_id != b.symbol_id) {
                return a.symbol_id < b.symbol_id;
            }
            if (a.stream_id != b.stream_id) {
                return a.stream_id < b.stream_id;
            }
            return a.sequence_no < b.sequence_no;
        });
    }

    std::vector<SequencedEvent> all_events_{};
    std::unordered_map<uint32_t, std::vector<SequencedEvent>> per_symbol_{};
    uint64_t next_sequence_{0};
};

}  // namespace haruquant


