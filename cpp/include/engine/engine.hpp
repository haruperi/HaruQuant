/**
 * @file engine.hpp
 * @brief Unified engine public API and simulation model declarations.
 */

#pragma once

#include "trading/trade.hpp"
#include "risk/risk_engine.hpp"

#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <memory>
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
    std::string client_order_id{};
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

enum class OmsOrderState {
    Unknown = 0,
    New = 1,
    Accepted = 2,
    PartiallyFilled = 3,
    Filled = 4,
    Canceled = 5,
    Expired = 6,
    Rejected = 7,
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
    [[nodiscard]] OmsOrderState order_state(uint64_t ticket) const;
    [[nodiscard]] std::string order_state_name(uint64_t ticket) const;
    [[nodiscard]] std::size_t idempotency_cache_size() const noexcept;
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
    struct IdempotencyEntry {
        std::string fingerprint{};
        TradeResult result{};
    };

    [[nodiscard]] static std::string submission_fingerprint(const TradeRequest& request);
    [[nodiscard]] static OmsOrderState map_order_state(uint64_t raw_state) noexcept;
    [[nodiscard]] static std::string order_state_label(OmsOrderState state);
    void set_order_state(uint64_t ticket, OmsOrderState state);
    void rebuild_order_states_from_snapshots();
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
    std::unordered_map<uint64_t, OmsOrderState> order_states_{};
    std::unordered_map<std::string, IdempotencyEntry> idempotency_by_client_order_id_{};

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

enum class PositionMode {
    Netting = 0,
    Hedging = 1,
};

struct PositionLeg {
    uint64_t leg_id{0};
    bool is_buy{true};
    double volume{0.0};
    double price{0.0};
    int64_t time_msc{0};
};

struct FillEvent {
    std::string symbol{};
    bool is_buy{true};
    double volume{0.0};
    double price{0.0};
    double commission{0.0};
    double swap{0.0};
    int64_t time_msc{0};
};

struct ReconciliationReport {
    bool ok{true};
    std::string trigger{"manual"};
    std::size_t position_mismatch_count{0};
    std::size_t account_mismatch_count{0};
    std::vector<std::string> issues{};
    std::string severity{"none"};
    bool requires_manual_resolution{false};
    bool block_new_orders{false};
};

enum class ReconcilePolicy {
    Auto = 0,
    Manual = 1,
};

struct EscalationDecision {
    bool allow_new_orders{true};
    bool requires_manual_resolution{false};
    bool escalate_alert{false};
    std::string policy{"auto"};
    std::string reason{"ok"};
};

class PositionBook {
public:
    explicit PositionBook(PositionMode mode = PositionMode::Netting);

    void set_mode(PositionMode mode);
    [[nodiscard]] PositionMode mode() const noexcept;
    void reset();

    void apply_fill(const FillEvent& fill);
    void apply_account_snapshot(const AccountInfoData& account);

    [[nodiscard]] std::unordered_map<std::string, PositionAggregate> snapshot_positions() const;
    [[nodiscard]] AccountInfoData snapshot_account() const;
    [[nodiscard]] std::vector<PositionLeg> legs_for_symbol(const std::string& symbol) const;

    [[nodiscard]] ReconciliationReport reconcile_with_broker(
        const std::unordered_map<std::string, PositionAggregate>& broker_positions,
        const AccountInfoData& broker_account,
        const std::string& trigger = "manual") const;
    [[nodiscard]] ReconciliationReport periodic_reconcile(
        const std::unordered_map<std::string, PositionAggregate>& broker_positions,
        const AccountInfoData& broker_account) const;
    [[nodiscard]] ReconciliationReport reconnect_reconcile(
        const std::unordered_map<std::string, PositionAggregate>& broker_positions,
        const AccountInfoData& broker_account) const;
    [[nodiscard]] EscalationDecision evaluate_reconciliation(
        const ReconciliationReport& report,
        ReconcilePolicy policy = ReconcilePolicy::Auto,
        std::size_t major_threshold = 2) const;
    bool write_incident_report(
        const std::string& path,
        const ReconciliationReport& report,
        const EscalationDecision& decision) const;

private:
    [[nodiscard]] static bool almost_equal(double lhs, double rhs, double eps = 1e-9) noexcept;
    void apply_fill_netting_unlocked(const FillEvent& fill);
    void apply_fill_hedging_unlocked(const FillEvent& fill);
    [[nodiscard]] std::unordered_map<std::string, PositionAggregate> snapshot_positions_unlocked() const;

    PositionMode mode_{PositionMode::Netting};
    AccountInfoData account_{};
    uint64_t next_leg_id_{1};
    std::unordered_map<std::string, PositionAggregate> net_positions_{};
    std::unordered_map<std::string, std::vector<PositionLeg>> hedged_legs_{};
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

struct BrokerSnapshot {
    AccountInfoData account{};
    std::unordered_map<std::string, PositionAggregate> positions{};
};

class BrokerAdapter {
public:
    virtual ~BrokerAdapter() = default;
    virtual bool connect() = 0;
    [[nodiscard]] virtual TradeResult submit(const TradeRequest& request) = 0;
    [[nodiscard]] virtual TradeResult cancel(uint64_t order_id) = 0;
    [[nodiscard]] virtual BrokerSnapshot fetch_state() const = 0;
};

class MockBroker final : public BrokerAdapter {
public:
    explicit MockBroker(SimulatorClient client = SimulatorClient{});

    void set_partial_fill_ratio(double ratio);
    void set_deterministic_price(double price);
    void clear_deterministic_price();

    bool connect() override;
    [[nodiscard]] TradeResult submit(const TradeRequest& request) override;
    [[nodiscard]] TradeResult cancel(uint64_t order_id) override;
    [[nodiscard]] BrokerSnapshot fetch_state() const override;

private:
    static TradeRequest scaled_request(const TradeRequest& request, double ratio);
    [[nodiscard]] std::unordered_map<std::string, PositionAggregate> aggregate_positions() const;

    SimulatorClient client_{};
    bool connected_{false};
    double partial_fill_ratio_{1.0};
    std::optional<double> deterministic_price_{};
};

class PaperTradingEngine {
public:
    explicit PaperTradingEngine(std::shared_ptr<BrokerAdapter> adapter);

    bool connect();
    [[nodiscard]] TradeResult submit_order(const TradeRequest& request);
    [[nodiscard]] TradeResult cancel_order(uint64_t order_id);
    [[nodiscard]] BrokerSnapshot snapshot_state() const;

private:
    std::shared_ptr<BrokerAdapter> adapter_;
};

struct ExecutionPolicy {
    int max_retries{2};
    std::size_t max_orders_per_window{20};
    int64_t rate_limit_window_ms{1000};
    std::size_t escalation_after_failures{3};
};

struct ExecutionRouteResult {
    TradeResult result{};
    int attempts{0};
    bool risk_blocked{false};
    bool rate_limited{false};
    bool retried{false};
    bool escalated{false};
    std::string policy_code{"OK"};
    std::string reason{"ok"};
    std::string escalation_reason{};
};

struct ExecutionSlice {
    int64_t scheduled_time_ms{0};
    double volume{0.0};
    double weight{0.0};
};

class ExecutionAlgoTWAP {
public:
    [[nodiscard]] static std::vector<ExecutionSlice> build_schedule(
        double total_volume,
        int64_t start_time_ms,
        int64_t end_time_ms,
        std::size_t slices);
};

class ExecutionAlgoVWAP {
public:
    [[nodiscard]] static std::vector<ExecutionSlice> build_schedule(
        double total_volume,
        int64_t start_time_ms,
        int64_t end_time_ms,
        const std::vector<double>& market_volume_profile);
};

struct ExecutionQualitySummary {
    std::size_t samples{0};
    std::size_t partial_fill_count{0};
    double partial_fill_rate{0.0};
    double avg_slippage{0.0};
    double avg_spread{0.0};
    double avg_latency_ms{0.0};
    double p99_latency_ms{0.0};
};

class ExecutionRouter {
public:
    explicit ExecutionRouter(
        std::shared_ptr<BrokerAdapter> adapter,
        ExecutionPolicy policy = {});

    bool connect();
    void set_policy(const ExecutionPolicy& policy);
    [[nodiscard]] ExecutionPolicy policy() const;
    void set_risk_account_state(
        double equity,
        double peak_equity,
        double gross_exposure,
        double net_exposure);
    [[nodiscard]] std::size_t consecutive_failures() const;

    [[nodiscard]] ExecutionRouteResult submit(
        const TradeRequest& request,
        double candidate_gross_add = 0.0,
        double candidate_net_delta = 0.0,
        double margin_required = 0.0,
        double free_margin = -1.0,
        bool live_mode = true);

    [[nodiscard]] TradeResult cancel(uint64_t order_id);
    void reset_quality_metrics();
    [[nodiscard]] ExecutionQualitySummary quality_summary() const;

private:
    [[nodiscard]] bool check_rate_limit_unlocked(int64_t now_ms);

    std::shared_ptr<BrokerAdapter> adapter_{};
    hqt::risk::RiskGovernor governor_{};
    hqt::risk::RiskAccountState risk_state_{10000.0, 10000.0, 0.0, 0.0};
    ExecutionPolicy policy_{};
    std::deque<int64_t> recent_submissions_ms_{};
    std::size_t consecutive_failures_{0};
    std::vector<double> latencies_ms_{};
    double latency_sum_ms_{0.0};
    double slippage_sum_{0.0};
    double spread_sum_{0.0};
    std::size_t quality_samples_{0};
    std::size_t partial_fill_count_{0};
    bool connected_{false};
    mutable std::mutex mutex_{};
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
using TickProcessedCallback = std::function<void(const ModelTick&, const SimulatorState&)>;

struct BacktestTradeEvent {
    std::string event_type{};  // open / close
    TradeRecordData trade{};
};

using TradeEventCallback = std::function<void(const BacktestTradeEvent&, const SimulatorState&)>;

class BacktestEngine {
public:
    explicit BacktestEngine(SimulatorClient& client);

    void set_on_bar_processed(BarProcessedCallback callback);
    void set_on_tick_processed(TickProcessedCallback callback);
    void set_on_trade_event(TradeEventCallback callback);

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
    TickProcessedCallback on_tick_processed_{};
    TradeEventCallback on_trade_event_{};
};

struct PortfolioSymbolInput {
    std::string symbol{};
    std::vector<BacktestBarStep> bars{};
};

struct ExposureConstraints {
    double max_total_exposure{1.0};
    double max_symbol_exposure{1.0};
    std::unordered_map<std::string, double> max_strategy_exposure{};
    std::unordered_map<std::string, double> max_asset_exposure{};
};

struct RebalancePolicy {
    int64_t schedule_interval_msc{0};
    double drift_threshold{0.0};
};

class PortfolioAllocator {
public:
    [[nodiscard]] static std::unordered_map<std::string, double> equal_weight(
        const std::vector<std::string>& symbols,
        double max_total_exposure = 1.0);
    [[nodiscard]] static std::unordered_map<std::string, double> risk_parity(
        const std::unordered_map<std::string, double>& symbol_volatility,
        double max_total_exposure = 1.0);
    [[nodiscard]] static std::unordered_map<std::string, double> custom(
        const std::unordered_map<std::string, double>& raw_weights,
        double max_total_exposure = 1.0,
        bool normalize = true);
    [[nodiscard]] static std::unordered_map<std::string, double> apply_exposure_constraints(
        const std::unordered_map<std::string, double>& target_allocations,
        const std::unordered_map<std::string, std::string>& symbol_to_strategy,
        const std::unordered_map<std::string, std::string>& symbol_to_asset,
        const ExposureConstraints& constraints);
};

class RebalanceController {
public:
    explicit RebalanceController(RebalancePolicy policy);

    [[nodiscard]] bool should_rebalance(
        int64_t now_msc,
        const std::unordered_map<std::string, double>& current_allocations,
        const std::unordered_map<std::string, double>& target_allocations) const;
    void mark_rebalanced(int64_t now_msc);
    [[nodiscard]] int64_t last_rebalance_msc() const noexcept;

private:
    RebalancePolicy policy_{};
    int64_t last_rebalance_msc_{0};
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

class VectorizedBacktestEngine {
public:
    explicit VectorizedBacktestEngine(SimulatorClient& client);

    void run(
        const std::string& symbol,
        double volume,
        const std::vector<BacktestBarStep>& bars);

    [[nodiscard]] const AccountInfoData& account_snapshot() const noexcept;
    [[nodiscard]] std::size_t processed_bars() const noexcept;
    [[nodiscard]] std::size_t total_trades() const noexcept;

private:
    static double normalize_volume(double requested, const SymbolInfoData& symbol_info);

    SimulatorClient& client_;
    AccountInfoData account_snapshot_{};
    std::size_t processed_bars_{0};
    std::size_t total_trades_{0};
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
