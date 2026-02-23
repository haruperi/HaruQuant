/**
FILE: tests\test_event_sequencer.cpp

PURPOSE:
Defines test_event_sequencer.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_event_sequencer.cpp.
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
#include <gtest/gtest.h>
#include "engine/event_sequencer.hpp"

using namespace haruquant;

TEST(EventSequencerTest, MergedOrderingIsDeterministic) {
    EventSequencer sequencer;

    sequencer.push(2, Event::tick(2'000'000, 2));
    sequencer.push(1, Event::tick(1'000'000, 1));
    sequencer.push(2, Event::tick(1'000'000, 2));
    sequencer.push(1, Event::tick(1'000'000, 1));  // same ts/stream/symbol -> sequence tie-break

    const auto ordered = sequencer.ordered_merged_with_metadata();
    ASSERT_EQ(ordered.size(), 4U);

    EXPECT_EQ(ordered[0].event.timestamp_us, 1'000'000);
    EXPECT_EQ(ordered[0].symbol_id, 1U);
    EXPECT_EQ(ordered[0].stream_id, 1U);

    EXPECT_EQ(ordered[1].event.timestamp_us, 1'000'000);
    EXPECT_EQ(ordered[1].symbol_id, 1U);
    EXPECT_EQ(ordered[1].stream_id, 1U);
    EXPECT_LT(ordered[0].sequence_no, ordered[1].sequence_no);

    EXPECT_EQ(ordered[2].event.timestamp_us, 1'000'000);
    EXPECT_EQ(ordered[2].symbol_id, 2U);
    EXPECT_EQ(ordered[2].stream_id, 2U);

    EXPECT_EQ(ordered[3].event.timestamp_us, 2'000'000);
}

TEST(EventSequencerTest, PerSymbolOrderingIsDeterministic) {
    EventSequencer sequencer;

    sequencer.push(1, Event::tick(3'000'000, 7));
    sequencer.push(2, Event::tick(1'000'000, 8));
    sequencer.push(1, Event::tick(2'000'000, 7));
    sequencer.push(2, Event::tick(1'500'000, 7));

    const auto symbol7 = sequencer.ordered_for_symbol(7);
    ASSERT_EQ(symbol7.size(), 3U);
    EXPECT_EQ(symbol7[0].timestamp_us, 1'500'000);
    EXPECT_EQ(symbol7[1].timestamp_us, 2'000'000);
    EXPECT_EQ(symbol7[2].timestamp_us, 3'000'000);
}

TEST(EventSequencerTest, ClearResetsState) {
    EventSequencer sequencer;
    sequencer.push(1, Event::tick(1'000'000, 1));
    ASSERT_FALSE(sequencer.empty());

    sequencer.clear();
    EXPECT_TRUE(sequencer.empty());
    EXPECT_EQ(sequencer.size(), 0U);
}


