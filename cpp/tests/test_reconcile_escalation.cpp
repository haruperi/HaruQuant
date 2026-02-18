/**
 * @file test_reconcile_escalation.cpp
 * @brief Tests for reconciliation escalation policy and incident reports.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <filesystem>
#include <fstream>
#include <string>

namespace {

using hqt::sim::AccountInfoData;
using hqt::sim::PositionAggregate;
using hqt::sim::PositionBook;
using hqt::sim::PositionMode;
using hqt::sim::ReconcilePolicy;

TEST(ReconcileEscalationTest, AutoPolicyMinorMismatchAllowsNewOrdersWithAlert) {
    PositionBook book(PositionMode::Netting);

    AccountInfoData local;
    local.balance = 10000.0;
    local.equity = 10000.0;
    local.margin = 0.0;
    book.apply_account_snapshot(local);

    std::unordered_map<std::string, PositionAggregate> broker_positions;
    PositionAggregate eurusd;
    eurusd.net_volume = 0.1;
    broker_positions["EURUSD"] = eurusd;

    const auto report = book.periodic_reconcile(broker_positions, local);
    const auto decision = book.evaluate_reconciliation(report, ReconcilePolicy::Auto, 3);

    EXPECT_FALSE(report.ok);
    EXPECT_TRUE(decision.allow_new_orders);
    EXPECT_FALSE(decision.requires_manual_resolution);
    EXPECT_TRUE(decision.escalate_alert);
}

TEST(ReconcileEscalationTest, ManualPolicyBlocksUntilClean) {
    PositionBook book(PositionMode::Netting);

    AccountInfoData local;
    local.balance = 10000.0;
    local.equity = 10000.0;
    local.margin = 0.0;
    book.apply_account_snapshot(local);

    std::unordered_map<std::string, PositionAggregate> broker_positions;
    PositionAggregate a;
    a.net_volume = 1.0;
    a.long_volume = 1.0;
    broker_positions["EURUSD"] = a;

    PositionAggregate b;
    b.net_volume = -1.0;
    b.short_volume = 1.0;
    broker_positions["GBPUSD"] = b;

    AccountInfoData broker = local;
    broker.equity = 9800.0;
    broker.margin = 200.0;

    const auto report = book.reconnect_reconcile(broker_positions, broker);
    const auto decision = book.evaluate_reconciliation(report, ReconcilePolicy::Manual, 2);

    EXPECT_FALSE(report.ok);
    EXPECT_FALSE(decision.allow_new_orders);
    EXPECT_TRUE(decision.requires_manual_resolution);
    EXPECT_TRUE(decision.escalate_alert);
}

TEST(ReconcileEscalationTest, IncidentReportIsWritten) {
    PositionBook book(PositionMode::Netting);
    AccountInfoData account;
    book.apply_account_snapshot(account);

    std::unordered_map<std::string, PositionAggregate> broker_positions;
    PositionAggregate eurusd;
    eurusd.net_volume = 0.5;
    broker_positions["EURUSD"] = eurusd;

    const auto report = book.reconnect_reconcile(broker_positions, account);
    const auto decision = book.evaluate_reconciliation(report, ReconcilePolicy::Auto, 1);

    const std::filesystem::path path = "artifacts/logs/live/reconcile_discrepancy_report.json";
    ASSERT_TRUE(book.write_incident_report(path.string(), report, decision));
    ASSERT_TRUE(std::filesystem::exists(path));

    std::ifstream in(path.string());
    std::string content((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    EXPECT_NE(content.find("\"decision\""), std::string::npos);
    EXPECT_NE(content.find("\"issues\""), std::string::npos);
}

}  // namespace

