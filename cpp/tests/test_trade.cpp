/**
 * @file test_trade.cpp
 * @brief Comprehensive tests for CTrade class (MT5-aligned)
 *
 * Tests all trading functionality including positions, orders, trailing stops,
 * snapshots, and MT5 API compatibility.
 */

#include <gtest/gtest.h>
#include "trading/trade.hpp"
#include "trading/symbol_info.hpp"

using namespace hqt;

class CTradeTest : public ::testing::Test {
protected:
    CTrade trade;
    SymbolInfo eurusd;

    void SetUp() override {
        // Initialize trade with $10,000
        trade = CTrade(10000.0, "USD", 100);

        // Configure EURUSD symbol
        eurusd.SetSymbolId(1);
        eurusd.Name("EURUSD");
        eurusd.SetDigits(5);
        eurusd.SetPoint(0.00001);
        eurusd.SetContractSize(100000.0);
        eurusd.SetVolumeMin(0.01);
        eurusd.SetVolumeMax(100.0);
        eurusd.SetVolumeStep(0.01);
        eurusd.SetMarginInitial(100.0);
        eurusd.SetSwapLong(-0.5);
        eurusd.SetSwapShort(0.3);

        // Set initial prices
        eurusd.UpdatePrice(1.10000, 1.10005, 0);

        // Register symbol
        trade.RegisterSymbol(eurusd);
        trade.SetCurrentTime(1000000);
    }
};

// ===================================================================
// Configuration Tests
// ===================================================================

TEST_F(CTradeTest, ConfigurationMethods) {
    trade.SetExpertMagicNumber(12345);
    EXPECT_EQ(trade.ExpertMagicNumber(), 12345);

    trade.SetDeviationInPoints(20);
    EXPECT_EQ(trade.DeviationInPoints(), 20);

    trade.SetTypeFilling(ENUM_ORDER_TYPE_FILLING::ORDER_FILLING_IOC);

    trade.SetAsyncMode(true);
    EXPECT_TRUE(trade.AsyncMode());

    trade.LogLevel(2);
    EXPECT_EQ(trade.LogLevel(), 2);
}

// ===================================================================
// Position Opening Tests
// ===================================================================

TEST_F(CTradeTest, BuyPositionOpensSuccessfully) {
    bool success = trade.Buy(0.1, "EURUSD");

    EXPECT_TRUE(success);
    EXPECT_EQ(trade.ResultRetcode(), ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE);

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 1);

    const auto& pos = positions[0];
    EXPECT_EQ(pos.PositionType(), ENUM_POSITION_TYPE::POSITION_TYPE_BUY);
    EXPECT_EQ(pos.Symbol(), "EURUSD");
    EXPECT_DOUBLE_EQ(pos.Volume(), 0.1);
    EXPECT_DOUBLE_EQ(pos.PriceOpen(), 1.10005); // Opens at ask
}

TEST_F(CTradeTest, SellPositionOpensSuccessfully) {
    bool success = trade.Sell(0.1, "EURUSD");

    EXPECT_TRUE(success);

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 1);

    const auto& pos = positions[0];
    EXPECT_EQ(pos.PositionType(), ENUM_POSITION_TYPE::POSITION_TYPE_SELL);
    EXPECT_DOUBLE_EQ(pos.PriceOpen(), 1.10000); // Opens at bid
}

TEST_F(CTradeTest, PositionOpenWithStopLossAndTakeProfit) {
    bool success = trade.PositionOpen(
        "EURUSD",
        ENUM_ORDER_TYPE::ORDER_TYPE_BUY,
        0.1,
        0.0,  // Market price
        1.09500,  // SL
        1.11000   // TP
    );

    EXPECT_TRUE(success);

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 1);

    const auto& pos = positions[0];
    EXPECT_DOUBLE_EQ(pos.StopLoss(), 1.09500);
    EXPECT_DOUBLE_EQ(pos.TakeProfit(), 1.11000);
}

TEST_F(CTradeTest, MultiplePositionsTracked) {
    trade.Buy(0.1, "EURUSD");
    trade.Buy(0.2, "EURUSD");

    auto positions = trade.GetPositions();
    EXPECT_EQ(positions.size(), 2);
    EXPECT_DOUBLE_EQ(positions[0].Volume(), 0.1);
    EXPECT_DOUBLE_EQ(positions[1].Volume(), 0.2);
}

// ===================================================================
// Position Modification Tests
// ===================================================================

TEST_F(CTradeTest, PositionModifyUpdatesStopLoss) {
    trade.Buy(0.1, "EURUSD");
    auto positions = trade.GetPositions();
    uint64_t ticket = positions[0].Ticket();

    bool success = trade.PositionModify(ticket, 1.09800, 0.0);
    EXPECT_TRUE(success);

    const PositionInfo* pos = trade.GetPosition(ticket);
    ASSERT_NE(pos, nullptr);
    EXPECT_DOUBLE_EQ(pos->StopLoss(), 1.09800);
}

TEST_F(CTradeTest, PositionModifyBySymbol) {
    trade.Buy(0.1, "EURUSD", 0.0, 1.09500, 1.11000);

    bool success = trade.PositionModify("EURUSD", 1.09700, 1.10800);
    EXPECT_TRUE(success);

    auto positions = trade.GetPositions("EURUSD");
    ASSERT_EQ(positions.size(), 1);
    EXPECT_DOUBLE_EQ(positions[0].StopLoss(), 1.09700);
    EXPECT_DOUBLE_EQ(positions[0].TakeProfit(), 1.10800);
}

// ===================================================================
// Position Closing Tests
// ===================================================================

TEST_F(CTradeTest, PositionCloseRemovesPosition) {
    trade.Buy(0.1, "EURUSD");
    auto positions = trade.GetPositions();
    uint64_t ticket = positions[0].Ticket();

    bool success = trade.PositionClose(ticket);
    EXPECT_TRUE(success);

    positions = trade.GetPositions();
    EXPECT_EQ(positions.size(), 0);

    // Verify deal created
    auto deals = trade.GetDeals();
    EXPECT_GE(deals.size(), 1);
}

TEST_F(CTradeTest, PositionCloseBySymbol) {
    trade.Buy(0.1, "EURUSD");

    bool success = trade.PositionClose("EURUSD");
    EXPECT_TRUE(success);

    auto positions = trade.GetPositions();
    EXPECT_EQ(positions.size(), 0);
}

TEST_F(CTradeTest, PositionClosePartial) {
    trade.Buy(0.5, "EURUSD");
    auto positions = trade.GetPositions();
    uint64_t ticket = positions[0].Ticket();

    bool success = trade.PositionClosePartial(ticket, 0.2);
    EXPECT_TRUE(success);

    const PositionInfo* pos = trade.GetPosition(ticket);
    ASSERT_NE(pos, nullptr);
    EXPECT_DOUBLE_EQ(pos->Volume(), 0.3); // 0.5 - 0.2 = 0.3
}

TEST_F(CTradeTest, PositionCloseByOpposite) {
    trade.Buy(0.1, "EURUSD");
    trade.Sell(0.1, "EURUSD");

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 2);

    uint64_t buy_ticket = positions[0].Ticket();
    uint64_t sell_ticket = positions[1].Ticket();

    bool success = trade.PositionCloseBy(buy_ticket, sell_ticket);
    EXPECT_TRUE(success);

    positions = trade.GetPositions();
    EXPECT_EQ(positions.size(), 0); // Both closed
}

// ===================================================================
// Profit/Loss Calculation Tests
// ===================================================================

TEST_F(CTradeTest, BuyPositionProfitCalculation) {
    trade.Buy(1.0, "EURUSD"); // 1 lot at 1.10005

    // Update price to 1.10105 (100 pips profit)
    trade.UpdatePrices("EURUSD", 1.10100, 1.10105, 2000000);

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 1);

    // Profit = (1.10100 - 1.10005) * 100000 = $95
    EXPECT_NEAR(positions[0].Profit(), 95.0, 1.0);
}

TEST_F(CTradeTest, SellPositionProfitCalculation) {
    trade.Sell(1.0, "EURUSD"); // 1 lot at 1.10000

    // Update price to 1.09900 (100 pips profit)
    trade.UpdatePrices("EURUSD", 1.09900, 1.09905, 2000000);

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 1);

    // Profit = (1.10000 - 1.09905) * 100000 = $95
    EXPECT_NEAR(positions[0].Profit(), 95.0, 1.0);
}

TEST_F(CTradeTest, EquityUpdatesWithUnrealizedPnL) {
    double initial_balance = trade.Account().Balance();

    trade.Buy(1.0, "EURUSD");

    // Price moves up 100 pips
    trade.UpdatePrices("EURUSD", 1.10100, 1.10105, 2000000);

    double equity = trade.Account().Equity();
    double expected_equity = initial_balance + 95.0; // $95 profit

    EXPECT_NEAR(equity, expected_equity, 1.0);
}

// ===================================================================
// Pending Order Tests
// ===================================================================

TEST_F(CTradeTest, BuyLimitOrderCreated) {
    bool success = trade.BuyLimit(0.1, 1.09500, "EURUSD");
    EXPECT_TRUE(success);

    auto orders = trade.GetOrders();
    ASSERT_EQ(orders.size(), 1);

    const auto& order = orders[0];
    EXPECT_EQ(order.OrderType(), ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT);
    EXPECT_DOUBLE_EQ(order.PriceOpen(), 1.09500);
    EXPECT_DOUBLE_EQ(order.VolumeInitial(), 0.1);
}

TEST_F(CTradeTest, SellStopOrderCreated) {
    bool success = trade.SellStop(0.1, 1.09500, "EURUSD");
    EXPECT_TRUE(success);

    auto orders = trade.GetOrders();
    ASSERT_EQ(orders.size(), 1);

    EXPECT_EQ(orders[0].OrderType(), ENUM_ORDER_TYPE::ORDER_TYPE_SELL_STOP);
}

TEST_F(CTradeTest, OrderModifyUpdatesPrice) {
    trade.BuyLimit(0.1, 1.09500, "EURUSD");
    auto orders = trade.GetOrders();
    uint64_t ticket = orders[0].Ticket();

    bool success = trade.OrderModify(ticket, 1.09400, 0.0, 0.0);
    EXPECT_TRUE(success);

    const OrderInfo* order = trade.GetOrder(ticket);
    ASSERT_NE(order, nullptr);
    EXPECT_DOUBLE_EQ(order->PriceOpen(), 1.09400);
}

TEST_F(CTradeTest, OrderDeleteRemovesOrder) {
    trade.BuyLimit(0.1, 1.09500, "EURUSD");
    auto orders = trade.GetOrders();
    uint64_t ticket = orders[0].Ticket();

    bool success = trade.OrderDelete(ticket);
    EXPECT_TRUE(success);

    orders = trade.GetOrders();
    EXPECT_EQ(orders.size(), 0);

    // Verify moved to history
    auto history = trade.GetHistoryOrders();
    EXPECT_GE(history.size(), 1);
}

// ===================================================================
// Quick Trade Method Tests
// ===================================================================

TEST_F(CTradeTest, QuickBuyMethod) {
    bool success = trade.Buy(0.1, "EURUSD", 0.0, 1.09500, 1.11000, "Test buy");
    EXPECT_TRUE(success);

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 1);
    EXPECT_EQ(positions[0].Comment(), "Test buy");
}

TEST_F(CTradeTest, QuickSellMethod) {
    bool success = trade.Sell(0.1, "EURUSD");
    EXPECT_TRUE(success);

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 1);
    EXPECT_EQ(positions[0].PositionType(), ENUM_POSITION_TYPE::POSITION_TYPE_SELL);
}

TEST_F(CTradeTest, AllPendingOrderMethods) {
    trade.BuyLimit(0.1, 1.09500, "EURUSD");
    trade.BuyStop(0.1, 1.10500, "EURUSD");
    trade.SellLimit(0.1, 1.10500, "EURUSD");
    trade.SellStop(0.1, 1.09500, "EURUSD");

    auto orders = trade.GetOrders();
    EXPECT_EQ(orders.size(), 4);
}

// ===================================================================
// Trailing Stop Tests
// ===================================================================

TEST_F(CTradeTest, TrailingStopEnableAndUpdate) {
    trade.Buy(1.0, "EURUSD"); // Opens at 1.10005
    auto positions = trade.GetPositions();
    uint64_t ticket = positions[0].Ticket();

    // Enable trailing stop: 50 points distance
    bool success = trade.TrailingStopEnable(ticket, 50, 0);
    EXPECT_TRUE(success);

    const PositionInfo* pos = trade.GetPosition(ticket);
    EXPECT_EQ(pos->GetTrailingDistance(), 50);

    // Price moves up 100 pips
    trade.UpdatePrices("EURUSD", 1.10100, 1.10105, 2000000);
    trade.UpdateTrailingStops();

    pos = trade.GetPosition(ticket);
    // SL should trail: 1.10100 - 50*0.00001 = 1.10050
    EXPECT_NEAR(pos->StopLoss(), 1.10050, 0.00002);
}

TEST_F(CTradeTest, TrailingStopWithStep) {
    trade.Buy(1.0, "EURUSD");
    auto positions = trade.GetPositions();
    uint64_t ticket = positions[0].Ticket();

    // Enable step trailing: 50 points distance, 20 points step
    trade.TrailingStopEnable(ticket, 50, 20);

    // Price moves up 15 pips (not enough for step)
    trade.UpdatePrices("EURUSD", 1.10020, 1.10025, 2000000);
    trade.UpdateTrailingStops();

    const PositionInfo* pos = trade.GetPosition(ticket);
    EXPECT_DOUBLE_EQ(pos->StopLoss(), 0.0); // SL not moved yet

    // Price moves up 30 pips total (enough for step)
    trade.UpdatePrices("EURUSD", 1.10035, 1.10040, 3000000);
    trade.UpdateTrailingStops();

    pos = trade.GetPosition(ticket);
    EXPECT_GT(pos->StopLoss(), 0.0); // SL should be set now
}

TEST_F(CTradeTest, TrailingStopDisable) {
    trade.Buy(1.0, "EURUSD");
    auto positions = trade.GetPositions();
    uint64_t ticket = positions[0].Ticket();

    trade.TrailingStopEnable(ticket, 50);
    trade.TrailingStopDisable(ticket);

    const PositionInfo* pos = trade.GetPosition(ticket);
    EXPECT_EQ(pos->GetTrailingDistance(), 0);
}

TEST_F(CTradeTest, TrailingStopNeverMovesDown) {
    trade.Buy(1.0, "EURUSD");
    auto positions = trade.GetPositions();
    uint64_t ticket = positions[0].Ticket();

    trade.TrailingStopEnable(ticket, 50);

    // Price moves up
    trade.UpdatePrices("EURUSD", 1.10100, 1.10105, 2000000);
    trade.UpdateTrailingStops();

    const PositionInfo* pos = trade.GetPosition(ticket);
    double sl1 = pos->StopLoss();

    // Price moves down (SL should not move)
    trade.UpdatePrices("EURUSD", 1.10050, 1.10055, 3000000);
    trade.UpdateTrailingStops();

    pos = trade.GetPosition(ticket);
    EXPECT_DOUBLE_EQ(pos->StopLoss(), sl1); // SL unchanged
}

// ===================================================================
// Account State Tests
// ===================================================================

TEST_F(CTradeTest, AccountBalanceTracking) {
    double initial_balance = trade.Account().Balance();
    EXPECT_DOUBLE_EQ(initial_balance, 10000.0);

    // Open and close position with profit
    trade.Buy(1.0, "EURUSD");
    trade.UpdatePrices("EURUSD", 1.10100, 1.10105, 2000000);

    auto positions = trade.GetPositions();
    trade.PositionClose(positions[0].Ticket());

    // Balance should increase (approximately $95 profit)
    EXPECT_GT(trade.Account().Balance(), initial_balance);
}

TEST_F(CTradeTest, MarginCalculation) {
    trade.Buy(1.0, "EURUSD");

    // Margin = (1 lot * 100000 * 1.10005) / 100 leverage = $1100.05
    double margin = trade.Account().Margin();
    EXPECT_NEAR(margin, 1100.0, 5.0);
}

TEST_F(CTradeTest, MarginFreeCalculation) {
    double initial = trade.Account().FreeMargin();

    trade.Buy(1.0, "EURUSD");

    double after = trade.Account().FreeMargin();
    EXPECT_LT(after, initial); // Free margin decreased
}

TEST_F(CTradeTest, MarginLevelCalculation) {
    trade.Buy(1.0, "EURUSD");

    double margin_level = trade.Account().MarginLevel();
    EXPECT_GT(margin_level, 100.0); // Should be well above 100%
}

// ===================================================================
// Request/Result Access Tests
// ===================================================================

TEST_F(CTradeTest, RequestAccessAfterTrade) {
    trade.Buy(0.5, "EURUSD", 0.0, 1.09500, 1.11000, "Test trade");

    EXPECT_EQ(trade.RequestSymbol(), "EURUSD");
    EXPECT_DOUBLE_EQ(trade.RequestVolume(), 0.5);
    EXPECT_DOUBLE_EQ(trade.RequestSL(), 1.09500);
    EXPECT_DOUBLE_EQ(trade.RequestTP(), 1.11000);
    EXPECT_EQ(trade.RequestComment(), "Test trade");
    EXPECT_EQ(trade.RequestMagic(), 0);
}

TEST_F(CTradeTest, ResultAccessAfterTrade) {
    trade.Buy(0.1, "EURUSD");

    EXPECT_EQ(trade.ResultRetcode(), ENUM_TRADE_RETCODE::TRADE_RETCODE_DONE);
    EXPECT_GT(trade.ResultOrder(), 0); // Ticket assigned
    EXPECT_DOUBLE_EQ(trade.ResultVolume(), 0.1);
    EXPECT_GT(trade.ResultPrice(), 0.0);
}

// ===================================================================
// Snapshot/Restore Tests
// ===================================================================

TEST_F(CTradeTest, SnapshotCapturesCompleteState) {
    trade.SetExpertMagicNumber(999);
    trade.Buy(0.1, "EURUSD");
    trade.BuyLimit(0.2, 1.09500, "EURUSD");

    auto snapshot = trade.CreateSnapshot();

    EXPECT_EQ(snapshot.positions.size(), 1);
    EXPECT_EQ(snapshot.orders.size(), 1);
    EXPECT_GT(snapshot.next_ticket, 1000);
    EXPECT_EQ(snapshot.symbols.size(), 1);
}

TEST_F(CTradeTest, RestoreSnapshotRecreatesState) {
    trade.Buy(0.1, "EURUSD");
    trade.Buy(0.2, "EURUSD");

    auto snapshot = trade.CreateSnapshot();

    // Clear state
    auto positions = trade.GetPositions();
    for (const auto& pos : positions) {
        trade.PositionClose(pos.Ticket());
    }

    EXPECT_EQ(trade.GetPositions().size(), 0);

    // Restore
    trade.RestoreSnapshot(snapshot);

    EXPECT_EQ(trade.GetPositions().size(), 2);
}

TEST_F(CTradeTest, SnapshotPreservesTicketCounter) {
    trade.Buy(0.1, "EURUSD");
    auto snapshot = trade.CreateSnapshot();
    uint64_t ticket1 = snapshot.next_ticket;

    trade.Buy(0.1, "EURUSD");
    trade.RestoreSnapshot(snapshot);

    trade.Buy(0.1, "EURUSD");
    auto positions = trade.GetPositions();
    uint64_t ticket2 = positions.back().Ticket();

    EXPECT_EQ(ticket2, ticket1); // Next ticket matches snapshot
}

// ===================================================================
// Deal History Tests
// ===================================================================

TEST_F(CTradeTest, DealsRecordedOnClose) {
    trade.Buy(0.1, "EURUSD");
    auto positions = trade.GetPositions();
    trade.PositionClose(positions[0].Ticket());

    auto deals = trade.GetDeals();
    EXPECT_GE(deals.size(), 1);

    const auto& deal = deals.back();
    EXPECT_EQ(deal.Symbol(), "EURUSD");
    EXPECT_DOUBLE_EQ(deal.Volume(), 0.1);
    EXPECT_EQ(deal.DealType(), ENUM_DEAL_TYPE::DEAL_TYPE_SELL); // Closing BUY = SELL deal
    EXPECT_EQ(deal.Entry(), ENUM_DEAL_ENTRY::DEAL_ENTRY_OUT);
}

TEST_F(CTradeTest, DealProfitRecorded) {
    trade.Buy(1.0, "EURUSD");
    trade.UpdatePrices("EURUSD", 1.10100, 1.10105, 2000000);

    auto positions = trade.GetPositions();
    trade.PositionClose(positions[0].Ticket());

    auto deals = trade.GetDeals();
    const auto& deal = deals.back();

    EXPECT_GT(deal.Profit(), 0.0); // Should have profit
    EXPECT_NEAR(deal.Profit(), 95.0, 5.0);
}

// ===================================================================
// Error Handling Tests
// ===================================================================

TEST_F(CTradeTest, InvalidSymbolRejected) {
    bool success = trade.Buy(0.1, "INVALID");
    EXPECT_FALSE(success);
    EXPECT_EQ(trade.ResultRetcode(), ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID);
}

TEST_F(CTradeTest, InvalidVolumeRejected) {
    bool success = trade.Buy(0.001, "EURUSD"); // Below min volume
    EXPECT_FALSE(success);
    EXPECT_EQ(trade.ResultRetcode(), ENUM_TRADE_RETCODE::TRADE_RETCODE_INVALID_VOLUME);
}

TEST_F(CTradeTest, ModifyNonexistentPositionFails) {
    bool success = trade.PositionModify(999999, 1.09500, 0.0);
    EXPECT_FALSE(success);
}

TEST_F(CTradeTest, CloseNonexistentPositionFails) {
    bool success = trade.PositionClose(999999);
    EXPECT_FALSE(success);
}

TEST_F(CTradeTest, DeleteNonexistentOrderFails) {
    bool success = trade.OrderDelete(999999);
    EXPECT_FALSE(success);
}

// ===================================================================
// Integration Tests
// ===================================================================

TEST_F(CTradeTest, CompleteTradeLifecycle) {
    // Open position
    EXPECT_TRUE(trade.Buy(0.5, "EURUSD", 0.0, 1.09500, 1.11000));

    auto positions = trade.GetPositions();
    ASSERT_EQ(positions.size(), 1);
    uint64_t ticket = positions[0].Ticket();

    // Price moves in favor
    trade.UpdatePrices("EURUSD", 1.10050, 1.10055, 2000000);

    // Modify SL/TP
    EXPECT_TRUE(trade.PositionModify(ticket, 1.09800, 1.10800));

    // Enable trailing stop
    EXPECT_TRUE(trade.TrailingStopEnable(ticket, 30));

    // Price moves more
    trade.UpdatePrices("EURUSD", 1.10100, 1.10105, 3000000);
    trade.UpdateTrailingStops();

    // Close position
    EXPECT_TRUE(trade.PositionClose(ticket));

    // Verify state
    EXPECT_EQ(trade.GetPositions().size(), 0);
    EXPECT_GE(trade.GetDeals().size(), 1);
    EXPECT_GT(trade.Account().Balance(), 10000.0);
}

TEST_F(CTradeTest, MultipleSymbolsSupported) {
    // Add GBPUSD
    SymbolInfo gbpusd;
    gbpusd.SetSymbolId(2);
    gbpusd.Name("GBPUSD");
    gbpusd.SetDigits(5);
    gbpusd.SetPoint(0.00001);
    gbpusd.SetContractSize(100000.0);
    gbpusd.SetVolumeMin(0.01);
    gbpusd.SetVolumeMax(100.0);
    gbpusd.SetVolumeStep(0.01);
    gbpusd.UpdatePrice(1.30000, 1.30005, 0);
    trade.RegisterSymbol(gbpusd);

    // Open positions on both
    EXPECT_TRUE(trade.Buy(0.1, "EURUSD"));
    EXPECT_TRUE(trade.Buy(0.1, "GBPUSD"));

    auto eur_positions = trade.GetPositions("EURUSD");
    auto gbp_positions = trade.GetPositions("GBPUSD");

    EXPECT_EQ(eur_positions.size(), 1);
    EXPECT_EQ(gbp_positions.size(), 1);
    EXPECT_EQ(trade.GetPositions().size(), 2);
}

// Main is provided by GTest::gtest_main
