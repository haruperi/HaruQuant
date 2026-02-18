/**
 * @file test_replay_certification.cpp
 * @brief Tests for replay certification fingerprinting and comparison.
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

