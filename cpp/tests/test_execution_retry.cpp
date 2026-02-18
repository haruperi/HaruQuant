/**
 * @file test_execution_retry.cpp
 * @brief Tests for execution router retry, risk gate, and rate limiting.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <memory>

namespace {

using hqt::sim::ExecutionPolicy;
using hqt::sim::ExecutionRouter;
using hqt::sim::MockBroker;
using hqt::sim::BrokerAdapter;
using hqt::sim::BrokerSnapshot;
using hqt::sim::TradeSimulator;
using hqt::sim::SymbolInfoData;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeResult;
using hqt::sim::TradeRequest;

TradeSimulator make_client() {
    TradeSimulator client;

    SymbolInfoData symbol;
    symbol.symbol = "EURUSD";
    symbol.digits = 5;
    symbol.point = 0.00001;
    symbol.spread = 10;
    symbol.volume_min = 0.01;
    symbol.volume_step = 0.01;
    symbol.volume_max = 100.0;
    symbol.trade_contract_size = 100000.0;
    symbol.trade_tick_size = 0.00001;
    symbol.trade_tick_value = 1.0;
    symbol.bid = 1.10000;
    symbol.ask = 1.10010;
    client.set_symbol_info(symbol);

    SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10010;
    tick.last = 1.10000;
    tick.time = 1700000000;
    tick.time_msc = 1700000000000;
    client.set_symbol_tick("EURUSD", tick);

    return client;
}

TradeRequest market_buy(double volume = 1.0) {
    TradeRequest req;
    req.action = 1;
    req.type = 0;
    req.symbol = "EURUSD";
    req.volume = volume;
    return req;
}

class FlakyBroker final : public BrokerAdapter {
public:
    bool connect() override {
        connected_ = true;
        return true;
    }

    TradeResult submit(const TradeRequest&) override {
        ++submit_count_;
        TradeResult out;
        out.retcode = 10031;  // retryable connection error
        out.comment = "simulated transient failure";
        return out;
    }

    TradeResult cancel(uint64_t) override {
        TradeResult out;
        out.retcode = 10009;
        out.comment = "ok";
        return out;
    }

    BrokerSnapshot fetch_state() const override {
        return {};
    }

    [[nodiscard]] int submit_count() const noexcept { return submit_count_; }

private:
    bool connected_{false};
    int submit_count_{0};
};

TEST(ExecutionRouterTest, RiskGateBlocksBeforeSubmit) {
    auto broker = std::make_shared<MockBroker>(make_client());
    ExecutionRouter router(broker, ExecutionPolicy{});
    ASSERT_TRUE(router.connect());
    router.set_risk_account_state(7000.0, 10000.0, 0.1, 0.1);  // 30% drawdown

    const auto routed = router.submit(market_buy());
    EXPECT_TRUE(routed.risk_blocked);
    EXPECT_EQ(routed.policy_code, "MAX_DRAWDOWN");
    EXPECT_EQ(routed.result.retcode, 10006);
    EXPECT_EQ(routed.attempts, 0);
}

TEST(ExecutionRouterTest, RetryIsBoundedAndEscalates) {
    auto broker = std::make_shared<FlakyBroker>();
    ExecutionPolicy policy;
    policy.max_retries = 2;
    policy.escalation_after_failures = 1;
    ExecutionRouter router(broker, policy);
    ASSERT_TRUE(router.connect());
    router.set_risk_account_state(10000.0, 10000.0, 0.0, 0.0);

    const auto routed = router.submit(market_buy());
    EXPECT_EQ(routed.result.retcode, 10031);
    EXPECT_EQ(routed.attempts, 3);
    EXPECT_TRUE(routed.retried);
    EXPECT_TRUE(routed.escalated);
    EXPECT_EQ(routed.policy_code, "EXECUTION_FAILED");
    EXPECT_EQ(broker->submit_count(), 3);
}

TEST(ExecutionRouterTest, RateLimitBlocksSecondOrderInWindow) {
    auto broker = std::make_shared<MockBroker>(make_client());
    ExecutionPolicy policy;
    policy.max_orders_per_window = 1;
    policy.rate_limit_window_ms = 60000;
    ExecutionRouter router(broker, policy);
    ASSERT_TRUE(router.connect());
    router.set_risk_account_state(10000.0, 10000.0, 0.0, 0.0);

    const auto first = router.submit(market_buy(0.1));
    EXPECT_EQ(first.result.retcode, 10009);

    const auto second = router.submit(market_buy(0.1));
    EXPECT_TRUE(second.rate_limited);
    EXPECT_EQ(second.policy_code, "RATE_LIMIT");
    EXPECT_EQ(second.result.retcode, 10024);
}

}  // namespace

