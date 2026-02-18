/**
 * @file test_optimization_runners.cpp
 * @brief Tests for C++ optimization runners (IP-42).
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <cmath>
#include <unordered_map>

using hqt::sim::BayesianSearchRunner;
using hqt::sim::GeneticSearchRunner;
using hqt::sim::GridSearchRunner;
using hqt::sim::OptimizationParamSpace;
using hqt::sim::RandomSearchRunner;

namespace {

double objective(const std::unordered_map<std::string, double>& p) {
    const double x = p.at("x");
    const double y = p.at("y");
    return -((x - 2.0) * (x - 2.0)) - ((y + 1.0) * (y + 1.0));
}

OptimizationParamSpace build_space() {
    return OptimizationParamSpace{
        {"x", {0.0, 1.0, 2.0, 3.0}},
        {"y", {-2.0, -1.0, 0.0, 1.0}},
    };
}

}  // namespace

TEST(OptimizationRunnersTest, GridSearchFindsGlobalBest) {
    const auto results = GridSearchRunner::run(build_space(), objective);
    ASSERT_FALSE(results.empty());
    EXPECT_EQ(results.size(), 16U);
    EXPECT_DOUBLE_EQ(results.front().score, 0.0);
    EXPECT_DOUBLE_EQ(results.front().params.at("x"), 2.0);
    EXPECT_DOUBLE_EQ(results.front().params.at("y"), -1.0);
}

TEST(OptimizationRunnersTest, RandomSearchIsDeterministicWithSeed) {
    const auto a = RandomSearchRunner::run(build_space(), 24U, 42U, objective);
    const auto b = RandomSearchRunner::run(build_space(), 24U, 42U, objective);
    ASSERT_EQ(a.size(), 24U);
    ASSERT_EQ(b.size(), 24U);
    EXPECT_DOUBLE_EQ(a.front().score, b.front().score);
    EXPECT_DOUBLE_EQ(a.front().params.at("x"), b.front().params.at("x"));
    EXPECT_DOUBLE_EQ(a.front().params.at("y"), b.front().params.at("y"));
}

TEST(OptimizationRunnersTest, GeneticSearchImprovesTowardBest) {
    const auto results = GeneticSearchRunner::run(build_space(), 12U, 8U, 123U, objective);
    ASSERT_FALSE(results.empty());
    EXPECT_GE(results.front().score, -1.0);
    EXPECT_LT(results.front().generation, 8U);
}

TEST(OptimizationRunnersTest, BayesianSearchProducesRankedTrials) {
    const auto results = BayesianSearchRunner::run(build_space(), 20U, 7U, objective, 4U, 0.30);
    ASSERT_EQ(results.size(), 20U);
    EXPECT_GE(results.front().score, -1.0);
    for (std::size_t i = 1; i < results.size(); ++i) {
        EXPECT_GE(results[i - 1].score, results[i].score);
    }
}

