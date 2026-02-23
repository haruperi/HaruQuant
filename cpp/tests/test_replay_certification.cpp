/**
FILE: tests\test_replay_certification.cpp

PURPOSE:
Defines test_replay_certification.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_replay_certification.cpp.
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
#include "engine/engine.hpp"

#include <vector>

using hqt::sim::ReplayCertificationResult;
using hqt::sim::ReplayCertifier;
using hqt::sim::ReplayTradeEvent;

TEST(ReplayCertificationTest, FingerprintStableForEquivalentSequences) {
    std::vector<ReplayTradeEvent> a{
        {1000, "EURUSD", "BUY", 1.1000, 0.10, 1},
        {2000, "EURUSD", "SELL", 1.1005, 0.10, 2},
    };
    std::vector<ReplayTradeEvent> b{
        {2000, "EURUSD", "SELL", 1.1005, 0.10, 2},
        {1000, "EURUSD", "BUY", 1.1000, 0.10, 1},
    };

    const auto fa = ReplayCertifier::fingerprint(a);
    const auto fb = ReplayCertifier::fingerprint(b);
    EXPECT_EQ(fa, fb);
}

TEST(ReplayCertificationTest, CompareDetectsMismatch) {
    std::vector<ReplayTradeEvent> baseline{
        {1000, "EURUSD", "BUY", 1.1000, 0.10, 1},
        {2000, "EURUSD", "SELL", 1.1005, 0.10, 2},
    };
    std::vector<ReplayTradeEvent> changed{
        {1000, "EURUSD", "BUY", 1.1000, 0.10, 1},
        {2000, "EURUSD", "SELL", 1.1008, 0.10, 2},
    };

    const ReplayCertificationResult result = ReplayCertifier::compare(baseline, changed);
    EXPECT_FALSE(result.consistent);
    EXPECT_NE(result.baseline_fingerprint, result.candidate_fingerprint);
    EXPECT_NE(result.message.find("Replay mismatch"), std::string::npos);
}


