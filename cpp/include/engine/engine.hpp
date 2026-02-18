/**
 * @file engine.hpp
 * @brief Unified engine public API and simulation model declarations.
 */

#pragma once

#include "trading/trade.hpp"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

namespace hqt::sim {

using Dict = std::unordered_map<std::string, std::string>;

struct AccountInfoData {
    int64_t login{12345678};
    int32_t leverage{100};
    int32_t margin_mode{0};
    bool trade_allowed{true};
    bool trade_expert{true};

    double balance{10000.0};
    double credit{0.0};
    double profit{0.0};
    double equity{0.0};
    double margin{0.0};
    double margin_free{10000.0};
    double margin_level{0.0};
    double commission_blocked{0.0};

    std::string name{"Simulated Trader"};
    std::string server{"Sim-Server"};
    std::string currency{"USD"};
    std::string company{"Simulated Company"};

    [[nodiscard]] Dict to_dict() const;
};

struct SymbolTickData {
    int64_t time{0};
    double bid{0.0};
    double ask{0.0};
    double last{0.0};
    int64_t volume{0};
    int64_t time_msc{0};
    int32_t flags{0};
    double volume_real{0.0};

    [[nodiscard]] Dict to_dict() const;
};

struct SymbolInfoData {
    std::string symbol{"EURUSD"};

    int32_t digits{5};
    int32_t spread{10};
    bool spread_float{true};
    double point{0.00001};

    int32_t trade_calc_mode{0};
    int32_t trade_mode{4};
    int32_t trade_stops_level{0};
    int32_t trade_freeze_level{0};
    int32_t trade_exemode{1};

    double volume_min{0.01};
    double volume_max{100.0};
    double volume_step{0.01};
    double volume_limit{0.0};

    double trade_tick_value{1.0};
    double trade_tick_value_profit{1.0};
    double trade_tick_value_loss{1.0};
    double trade_tick_size{0.00001};
    double trade_contract_size{100000.0};
    double margin_initial{0.0};

    int32_t swap_mode{1};
    double swap_long{-1.0};
    double swap_short{-1.0};
    int32_t swap_rollover3days{3};

    double bid{0.0};
    double ask{0.0};
    double last{0.0};

    bool select{true};
    bool visible{true};

    [[nodiscard]] Dict to_dict() const;
};

struct TradeRecordData {
    uint64_t ticket{0};
    uint64_t order{0};
    int64_t time{0};
    int64_t time_msc{0};
    int64_t expiration{0};
    uint64_t type{0};
    uint64_t type_time{0};
    uint64_t magic{0};
    uint64_t identifier{0};
    uint64_t reason{0};
    double volume{0.0};
    double price_open{0.0};
    double sl{0.0};
    double tp{0.0};
    double price_current{0.0};
    double swap{0.0};
    double profit{0.0};
    std::string symbol{};
    std::string comment{};

    [[nodiscard]] Dict to_dict() const;
};

struct SimulatorState {
    bool running{false};
    bool paused{false};
    int64_t current_time_us{0};
    std::size_t current_bar_index{0};
    std::size_t processed_events{0};

    void reset() noexcept;
};

double calc_margin(
    int trade_calc_mode,
    double volume,
    double price,
    double contract_size,
    double leverage,
    double tick_size,
    double tick_value,
    double margin_initial);

double calc_profit(
    int action,
    double volume,
    double price_open,
    double price_close,
    double tick_size,
    double tick_value,
    double contract_size);

struct TradeRequest {
    int action{0};
    int type{0};
    uint64_t order{0};
    std::string symbol{};
    double volume{0.0};
    double price{0.0};
    double stoplimit{0.0};
    double sl{0.0};
    double tp{0.0};
    int type_time{0};
    int64_t expiration{0};
    std::string comment{};
};

struct TradeResult {
    int retcode{10011};
    uint64_t deal{0};
    uint64_t order{0};
    double volume{0.0};
    double price{0.0};
    double bid{0.0};
    double ask{0.0};
    std::string comment{};
};

class TradeGateway {
public:
    explicit TradeGateway(const AccountInfoData& account);

    void register_symbol(const SymbolInfoData& symbol);
    [[nodiscard]] TradeResult order_send(const TradeRequest& request, const SymbolTickData* tick);

    [[nodiscard]] const hqt::CTrade& trade() const noexcept { return trade_; }
    [[nodiscard]] hqt::CTrade& trade() noexcept { return trade_; }

private:
    static hqt::SymbolInfo to_symbol_info(const SymbolInfoData& data);

    hqt::CTrade trade_;
    std::unordered_map<std::string, SymbolInfoData> symbols_;
};

class SimulatorClient {
public:
    SimulatorClient() = default;
    explicit SimulatorClient(AccountInfoData account_data);

    [[nodiscard]] const AccountInfoData& account_info() const noexcept;
    [[nodiscard]] const SymbolInfoData* symbol_info(const std::string& symbol) const noexcept;
    [[nodiscard]] const SymbolTickData* symbol_info_tick(const std::string& symbol) const noexcept;

    [[nodiscard]] std::vector<TradeRecordData> positions_get(
        std::optional<uint64_t> ticket = std::nullopt,
        std::optional<std::string_view> symbol = std::nullopt) const;

    [[nodiscard]] std::vector<TradeRecordData> orders_get(
        std::optional<uint64_t> ticket = std::nullopt,
        std::optional<std::string_view> symbol = std::nullopt) const;

    [[nodiscard]] std::vector<TradeRecordData> history_orders_get(
        std::optional<uint64_t> ticket = std::nullopt) const;

    [[nodiscard]] std::vector<TradeRecordData> history_deals_get(
        std::optional<uint64_t> ticket = std::nullopt) const;

    [[nodiscard]] std::pair<int, std::string> last_error() const;
    [[nodiscard]] std::string trade_retcode_description(int retcode) const;
    [[nodiscard]] double order_calc_margin(
        int action,
        const std::string& symbol,
        double volume,
        double price) const;
    [[nodiscard]] double order_calc_profit(
        int action,
        const std::string& symbol,
        double volume,
        double price_open,
        double price_close) const;
    [[nodiscard]] TradeResult order_send(const TradeRequest& request);
    [[nodiscard]] TradeResult close_position(uint64_t ticket);
    bool set_history_order_state(uint64_t ticket, uint64_t state);
    bool set_history_order_done_time(uint64_t ticket, int64_t time_sec, int64_t time_msc);

    void set_account_info(const AccountInfoData& data);
    void set_symbol_info(const SymbolInfoData& data);
    void set_symbol_tick(const std::string& symbol, const SymbolTickData& tick);
    void upsert_position(const TradeRecordData& data);
    void upsert_order(const TradeRecordData& data);
    void upsert_history_order(const TradeRecordData& data);
    void upsert_deal(const TradeRecordData& data);
    void set_last_error(int code, const std::string& message);

private:
    void sync_state_from_trade();

    template <typename Container>
    [[nodiscard]] static std::vector<TradeRecordData> collect_records(
        const Container& records,
        std::optional<uint64_t> ticket,
        std::optional<std::string_view> symbol);

    AccountInfoData account_data_{};
    TradeGateway trade_gateway_{account_data_};
    std::unordered_map<std::string, SymbolInfoData> symbols_data_{};
    std::unordered_map<std::string, SymbolTickData> ticks_data_{};

    std::unordered_map<uint64_t, TradeRecordData> positions_data_{};
    std::unordered_map<uint64_t, TradeRecordData> orders_data_{};
    std::unordered_map<uint64_t, TradeRecordData> history_orders_data_{};
    std::unordered_map<uint64_t, TradeRecordData> deals_data_{};

    int last_error_code_{1};
    std::string last_error_message_{"Success"};
};

struct PositionTotals {
    double profit{0.0};
    double margin{0.0};
    double commission{0.0};
    double fee{0.0};
    double swap{0.0};
};

struct PositionAggregate {
    double net_volume{0.0};
    double long_volume{0.0};
    double short_volume{0.0};
    double margin{0.0};
    double realized_pnl{0.0};
    double unrealized_pnl{0.0};
};

class PortfolioState {
public:
    explicit PortfolioState(double initial_balance = 10000.0, std::string currency = "USD");

    void reset(double initial_balance = 10000.0, const std::string& currency = "USD");
    void set_capital(double balance, double credit = 0.0);
    void upsert_position(
        const std::string& strategy_id,
        const std::string& symbol,
        double net_volume,
        double margin,
        double unrealized_pnl);
    void clear_position(const std::string& strategy_id, const std::string& symbol);
    void apply_realized_pnl(
        const std::string& strategy_id,
        const std::string& symbol,
        double realized_pnl,
        double commission = 0.0,
        double swap = 0.0);

    [[nodiscard]] AccountInfoData account_snapshot() const;
    [[nodiscard]] double total_realized_pnl() const;
    [[nodiscard]] double total_unrealized_pnl() const;
    [[nodiscard]] std::unordered_map<std::string, PositionAggregate> positions_by_symbol() const;
    [[nodiscard]] std::unordered_map<std::string, PositionAggregate> positions_by_strategy(
        const std::string& strategy_id) const;

private:
    void recompute_unlocked();

    AccountInfoData account_{};
    double total_realized_pnl_{0.0};
    std::unordered_map<std::string, std::unordered_map<std::string, PositionAggregate>>
        strategy_symbol_positions_{};
    std::unordered_map<std::string, PositionAggregate> symbol_positions_{};
    mutable std::mutex mutex_{};
};

class AccountMonitor {
public:
    [[nodiscard]] PositionTotals monitor_positions(
        const SimulatorClient& client,
        const std::string& symbol,
        double bid,
        double ask) const;

    [[nodiscard]] AccountInfoData monitor_account(
        const AccountInfoData& base,
        const PositionTotals& totals) const;
};

struct TradeRecord {
    uint64_t ticket{0};
    std::string symbol{};
    bool is_buy{true};
    double volume{0.0};
    double open_price{0.0};
    double close_price{0.0};
    double stop_loss{0.0};
    double take_profit{0.0};

    int64_t open_time_msc{0};
    int64_t close_time_msc{0};
    double time_in_trade_seconds{0.0};
    int bars_in_trade{0};

    double initial_risk_usd{0.0};
    double profit_loss{0.0};
    double mae_usd{0.0};
    double mfe_usd{0.0};
    double r_multiple{0.0};
};

class TradeRecordTracker {
public:
    void reset();

    bool has_open(uint64_t ticket) const;
    void on_open(
        uint64_t ticket,
        const std::string& symbol,
        bool is_buy,
        double volume,
        double open_price,
        double sl,
        double tp,
        int64_t open_time_msc,
        double initial_risk_usd);
    void on_update(uint64_t ticket, double profit_usd);
    bool on_close(
        uint64_t ticket,
        int64_t close_time_msc,
        double close_price,
        double profit_loss_usd);

    [[nodiscard]] const std::vector<TradeRecord>& completed_trades() const noexcept;

private:
    struct OpenTradeState {
        TradeRecord record;
        double mfe_usd{0.0};
        double mae_usd{0.0};
    };

    std::unordered_map<uint64_t, OpenTradeState> open_;
    std::vector<TradeRecord> completed_;
};

struct TickModelBar {
    int64_t time_msc{0};
    double open{0.0};
    double high{0.0};
    double low{0.0};
    double close{0.0};
    double spread_points{-1.0};
};

struct ModelTick {
    int64_t time_msc{0};
    double bid{0.0};
    double ask{0.0};
    double last{0.0};

    friend bool operator==(const ModelTick& lhs, const ModelTick& rhs) {
        return lhs.time_msc == rhs.time_msc &&
            lhs.bid == rhs.bid &&
            lhs.ask == rhs.ask &&
            lhs.last == rhs.last;
    }
};

class TickModel {
public:
    [[nodiscard]] static std::vector<ModelTick> generate_m1_ohlc(
        const std::vector<TickModelBar>& bars,
        double point,
        double spread_default_points);

    [[nodiscard]] static std::vector<ModelTick> generate_synthetic_ticks(
        const std::vector<TickModelBar>& bars,
        double point,
        double spread_default_points,
        int support_points = 2);

    [[nodiscard]] static std::vector<ModelTick> passthrough_real_ticks(
        const std::vector<ModelTick>& ticks);

private:
    [[nodiscard]] static std::vector<double> support_point_split(
        double start,
        double end,
        int support_points);
};

struct BacktestBarStep {
    int64_t time_msc{0};
    double close{0.0};
    double spread_points{-1.0};
    int entry_signal{0};
    int exit_signal{0};
    double sl{0.0};
    double tp{0.0};
};

enum class AutoCloseReason {
    StopLoss = 1,
    TakeProfit = 2,
};

using BarProcessedCallback = std::function<void(std::size_t, const BacktestBarStep&, const SimulatorState&)>;

class BacktestEngine {
public:
    explicit BacktestEngine(SimulatorClient& client);

    void set_on_bar_processed(BarProcessedCallback callback);

    void run_trading_timeframe(
        const std::string& symbol,
        double volume,
        const std::vector<BacktestBarStep>& bars);
    void run_trading_timeframe_with_ticks(
        const std::string& symbol,
        double volume,
        const std::vector<BacktestBarStep>& bars,
        const std::vector<ModelTick>& ticks);

    [[nodiscard]] const SimulatorState& state() const noexcept;
    [[nodiscard]] const AccountInfoData& account_snapshot() const noexcept;
    [[nodiscard]] std::optional<AutoCloseReason> close_reason(uint64_t ticket) const;
    [[nodiscard]] const std::vector<TradeRecord>& completed_trades() const noexcept;

private:
    void ensure_trade_record_for_position(const TradeRecordData& pos, int64_t now_msc);
    void close_position_and_track(const TradeRecordData& pos, int64_t now_msc, double close_price);
    double lookup_deal_profit_or_fallback(uint64_t deal_ticket, const TradeRecordData& pos, double close_price) const;
    void monitor_pending_orders(const std::string& symbol, double bid, double ask, int64_t current_time_msc);
    void monitor_positions_and_account(const std::string& symbol, double bid, double ask);
    static bool should_trigger_order(const TradeRecordData& order, double bid, double ask);
    void apply_exit_signal(const std::string& symbol, int exit_signal);
    void apply_entry_signal(
        const std::string& symbol,
        double volume,
        int entry_signal,
        double bid,
        double ask,
        double sl,
        double tp);

    SimulatorClient& client_;
    SimulatorState state_{};
    AccountMonitor account_monitor_{};
    TradeRecordTracker trade_record_tracker_{};
    AccountInfoData account_snapshot_{};
    std::unordered_map<uint64_t, AutoCloseReason> close_reasons_{};
    BarProcessedCallback on_bar_processed_{};
};

struct PortfolioSymbolInput {
    std::string symbol{};
    std::vector<BacktestBarStep> bars{};
};

class PortfolioEngine {
public:
    explicit PortfolioEngine(SimulatorClient& client);

    void run_equal_weight(
        const std::vector<PortfolioSymbolInput>& inputs,
        double base_volume);

    void run_with_allocations(
        const std::vector<PortfolioSymbolInput>& inputs,
        double base_volume,
        const std::unordered_map<std::string, double>& allocations);

    [[nodiscard]] const std::unordered_map<std::string, double>& effective_allocations() const noexcept;

private:
    static double normalize_volume(double requested, const SymbolInfoData& symbol_info);
    void process_bar(const std::string& symbol, const BacktestBarStep& bar, double base_volume);

    SimulatorClient& client_;
    std::unordered_map<std::string, double> effective_allocations_{};
};

struct ResultMetricsSummary {
    double initial_balance{0.0};
    double final_balance{0.0};
    double total_return{0.0};
    double total_return_pct{0.0};

    std::size_t total_trades{0};
    std::size_t winning_trades{0};
    std::size_t losing_trades{0};
    std::size_t breakeven_trades{0};

    double win_rate{0.0};
    double gross_profit{0.0};
    double gross_loss{0.0};
    double profit_factor{0.0};

    double max_drawdown{0.0};
    double max_drawdown_pct{0.0};
    double sharpe_ratio{0.0};
};

class ResultMetrics {
public:
    [[nodiscard]] static ResultMetricsSummary from_trades(
        const std::vector<TradeRecord>& trades,
        double initial_balance,
        double final_balance);
};

}  // namespace hqt::sim

namespace hqt::engine {

class Engine {
public:
    explicit Engine(hqt::sim::SimulatorClient& client);

    void run_trading_timeframe(
        const std::string& symbol,
        double volume,
        const std::vector<hqt::sim::BacktestBarStep>& bars);

    void run_trading_timeframe_with_ticks(
        const std::string& symbol,
        double volume,
        const std::vector<hqt::sim::BacktestBarStep>& bars,
        const std::vector<hqt::sim::ModelTick>& ticks);

    [[nodiscard]] const hqt::sim::SimulatorState& state() const noexcept;
    [[nodiscard]] const hqt::sim::AccountInfoData& account_snapshot() const noexcept;
    [[nodiscard]] const std::vector<hqt::sim::TradeRecord>& completed_trades() const noexcept;

private:
    hqt::sim::BacktestEngine impl_;
};

}  // namespace hqt::engine
