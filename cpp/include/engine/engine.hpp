/**
FILE: include\engine\engine.hpp

PURPOSE:
Defines engine.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in engine.hpp.
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
#include <unordered_set>
#include <utility>
#include <vector>

namespace haruquant::sim {

using Dict = std::unordered_map<std::string, std::string>;

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
    int trade_calc_mode,
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

struct TradeCheckResult {
    int retcode{10011};
    double balance{0.0};
    double equity{0.0};
    double profit{0.0};
    double margin{0.0};
    double margin_free{0.0};
    double margin_level{0.0};
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
    explicit TradeGateway(const haruquant::AccountInfo& account);

    // Register per-symbol metadata used by CTrade for validation and pricing.
    void register_symbol(const haruquant::SymbolInfo& symbol);
    // Submit one trade request through the underlying CTrade execution path.
    [[nodiscard]] TradeResult order_send(const TradeRequest& request, const SymbolTickData* tick);

    // Direct access to the underlying CTrade engine.
    [[nodiscard]] const haruquant::CTrade& trade() const noexcept { return trade_; }
    [[nodiscard]] haruquant::CTrade& trade() noexcept { return trade_; }

private:
    // Core execution engine (opens/closes positions, places orders, produces deals).
    haruquant::CTrade trade_;
    // Local symbol registry by symbol name (for request-time lookup).
    std::unordered_map<std::string, haruquant::SymbolInfo> symbols_;
};

/**
 * High-level simulator facade used by backtest/runtime components.
 *
 * Responsibilities:
 * - Hold account, symbol, tick, and order lifecycle state snapshots.
 * - Route order/close requests into CTrade via TradeGateway.
 * - Expose MT5-like query APIs (positions/orders/deals/history).
 *
 * Note:
 * - The authoritative execution logic is in CTrade.
 * - TradeSimulator mirrors CTrade state into map-based containers
 *   for fast lookup by ticket and easy filtering.
 */
class TradeSimulator {
public:
    TradeSimulator();
    explicit TradeSimulator(haruquant::AccountInfo account);

    // ----- Read-only snapshots -----
    [[nodiscard]] const haruquant::AccountInfo& account_info() const noexcept;
    [[nodiscard]] const haruquant::SymbolInfo* symbol_info(const std::string& symbol) const noexcept;
    [[nodiscard]] const SymbolTickData* symbol_info_tick(const std::string& symbol) const noexcept;

    // MT5-style query methods (name/signature parity with MetaTrader5 Python API).
    [[nodiscard]] std::vector<haruquant::PositionInfo> positions_get(
        std::optional<std::string> symbol = std::nullopt,
        std::optional<std::string> group = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt) const;
    [[nodiscard]] std::size_t positions_total() const noexcept;

    [[nodiscard]] std::vector<haruquant::OrderInfo> orders_get(
        std::optional<std::string> symbol = std::nullopt,
        std::optional<std::string> group = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt) const;
    [[nodiscard]] std::size_t orders_total() const noexcept;

    [[nodiscard]] std::vector<haruquant::HistoryOrderInfo> history_orders_get(
        std::optional<uint64_t> ticket = std::nullopt) const;
    [[nodiscard]] std::vector<haruquant::HistoryOrderInfo> history_orders_get(
        int64_t date_from_sec,
        int64_t date_to_sec,
        std::optional<std::string> group = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt) const;
    [[nodiscard]] std::size_t history_orders_total() const noexcept;

    [[nodiscard]] std::vector<haruquant::DealInfo> history_deals_get(
        std::optional<uint64_t> ticket = std::nullopt) const;
    [[nodiscard]] std::vector<haruquant::DealInfo> history_deals_get(
        int64_t date_from_sec,
        int64_t date_to_sec,
        std::optional<std::string> group = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt) const;
    [[nodiscard]] std::size_t history_deals_total() const noexcept;

    bool symbol_select(const std::string& symbol, bool enable = true);
    [[nodiscard]] std::vector<haruquant::SymbolInfo> symbols_get(
        std::optional<std::string> group = std::nullopt) const;
    [[nodiscard]] std::size_t symbols_total() const noexcept;

    // ----- Validation/helpers and execution -----
    [[nodiscard]] std::pair<int, std::string> last_error() const;
    [[nodiscard]] std::string trade_retcode_description(int retcode) const;
    [[nodiscard]] TradeCheckResult order_check(const TradeRequest& request) const;
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
    [[nodiscard]] TradeResult PositionOpen(
        const std::string& symbol,
        int order_type,
        double volume,
        double price = 0.0,
        double sl = 0.0,
        double tp = 0.0,
        const std::string& comment = "");
    [[nodiscard]] TradeResult PositionModify(
        std::optional<std::string> symbol = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt,
        double sl = 0.0,
        double tp = 0.0);
    [[nodiscard]] TradeResult PositionClose(
        std::optional<std::string> symbol = std::nullopt,
        std::optional<uint64_t> ticket = std::nullopt,
        uint64_t deviation = 0);
    [[nodiscard]] TradeResult OrderOpen(
        const std::string& symbol,
        int order_type,
        double volume,
        double price,
        double stoplimit = 0.0,
        double sl = 0.0,
        double tp = 0.0,
        int type_time = 0,
        int64_t expiration = 0,
        const std::string& comment = "");
    [[nodiscard]] TradeResult OrderModify(
        uint64_t ticket,
        double price,
        double sl = 0.0,
        double tp = 0.0,
        double stoplimit = 0.0,
        int64_t expiration = 0,
        const std::string& comment = "");
    [[nodiscard]] TradeResult OrderDelete(
        uint64_t ticket,
        const std::string& comment = "");
    [[nodiscard]] TradeResult order_send(const TradeRequest& request);
    [[nodiscard]] TradeResult close_position(uint64_t ticket);
    [[nodiscard]] OmsOrderState order_state(uint64_t ticket) const;
    [[nodiscard]] std::string order_state_name(uint64_t ticket) const;
    [[nodiscard]] std::size_t idempotency_cache_size() const noexcept;
    bool set_history_order_state(uint64_t ticket, uint64_t state);
    bool set_history_order_done_time(uint64_t ticket, int64_t time_sec, int64_t time_msc);

    // ----- Direct state upsert/  (used by bridge/tests/tools) -----
    void set_account_info(const haruquant::AccountInfo& data);
    void set_symbol_info(const haruquant::SymbolInfo& data);
    void set_symbol_tick(const std::string& symbol, const SymbolTickData& tick);
    void upsert_position_info(const haruquant::PositionInfo& data);
    void upsert_order_info(const haruquant::OrderInfo& data);
    void upsert_history_order_info(const haruquant::HistoryOrderInfo& data);
    void upsert_deal_info(const haruquant::DealInfo& data);
    void set_last_error(int code, const std::string& message);

private:
    struct IdempotencyEntry {
        // Deterministic fingerprint generated from request fields.
        std::string fingerprint{};
        // Cached result returned when fingerprint matches a prior submission.
        TradeResult result{};
    };

    // Build a stable key used to deduplicate repeated submissions.
    [[nodiscard]] static std::string submission_fingerprint(const TradeRequest& request);
    // Map low-level order state code to OMS state enum.
    [[nodiscard]] static OmsOrderState map_order_state(uint64_t raw_state) noexcept;
    // Human-readable name for OMS state.
    [[nodiscard]] static std::string order_state_label(OmsOrderState state);
    void set_order_state(uint64_t ticket, OmsOrderState state);
    // Recompute derived state maps after manual state injection.
    void rebuild_order_states_from_snapshots();
    // Pull latest positions/orders/deals/history from CTrade into local containers.
    void sync_state_from_trade();

    // Account snapshot used by simulation and exposed to callers.
    haruquant::AccountInfo account_info_{};
    // Execution gateway wrapping CTrade.
    TradeGateway trade_gateway_{account_info_};
    // Symbol metadata and latest tick cache by symbol.
    std::unordered_map<std::string, haruquant::SymbolInfo> symbols_data_{};
    std::unordered_map<std::string, SymbolTickData> ticks_data_{};

    // Core TradeSimulator lifecycle containers (Database-like) (ticket -> record).
    std::unordered_map<uint64_t, haruquant::PositionInfo> positions_info_data_{};
    std::unordered_map<uint64_t, haruquant::OrderInfo> orders_info_data_{};
    std::unordered_map<uint64_t, haruquant::HistoryOrderInfo> history_orders_info_data_{};
    std::unordered_map<uint64_t, haruquant::DealInfo> deals_info_data_{};
    // Derived OMS status per order ticket.
    std::unordered_map<uint64_t, OmsOrderState> order_states_{};
    // Idempotency cache keyed by client order id.
    std::unordered_map<std::string, IdempotencyEntry> idempotency_by_client_order_id_{};

    // Last public error exposed by last_error().
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

    [[nodiscard]] haruquant::AccountInfo account_snapshot() const;
    [[nodiscard]] double total_realized_pnl() const;
    [[nodiscard]] double total_unrealized_pnl() const;
    [[nodiscard]] std::unordered_map<std::string, PositionAggregate> positions_by_symbol() const;
    [[nodiscard]] std::unordered_map<std::string, PositionAggregate> positions_by_strategy(
        const std::string& strategy_id) const;

private:
    void recompute_unlocked();

    haruquant::AccountInfo account_{};
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
    void apply_account_snapshot(const haruquant::AccountInfo& account);

    [[nodiscard]] std::unordered_map<std::string, PositionAggregate> snapshot_positions() const;
    [[nodiscard]] haruquant::AccountInfo snapshot_account() const;
    [[nodiscard]] std::vector<PositionLeg> legs_for_symbol(const std::string& symbol) const;

    [[nodiscard]] ReconciliationReport reconcile_with_broker(
        const std::unordered_map<std::string, PositionAggregate>& broker_positions,
        const haruquant::AccountInfo& broker_account,
        const std::string& trigger = "manual") const;
    [[nodiscard]] ReconciliationReport periodic_reconcile(
        const std::unordered_map<std::string, PositionAggregate>& broker_positions,
        const haruquant::AccountInfo& broker_account) const;
    [[nodiscard]] ReconciliationReport reconnect_reconcile(
        const std::unordered_map<std::string, PositionAggregate>& broker_positions,
        const haruquant::AccountInfo& broker_account) const;
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
    haruquant::AccountInfo account_{};
    uint64_t next_leg_id_{1};
    std::unordered_map<std::string, PositionAggregate> net_positions_{};
    std::unordered_map<std::string, std::vector<PositionLeg>> hedged_legs_{};
    mutable std::mutex mutex_{};
};

class AccountMonitor {
public:
    [[nodiscard]] PositionTotals monitor_positions(
        const TradeSimulator& client,
        const std::string& symbol,
        double bid,
        double ask) const;

    [[nodiscard]] haruquant::AccountInfo monitor_account(
        const haruquant::AccountInfo& base,
        const PositionTotals& totals) const;
};

struct BrokerSnapshot {
    haruquant::AccountInfo account{};
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
    explicit MockBroker(TradeSimulator client = TradeSimulator{});

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

    TradeSimulator client_{};
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
    haruquant::risk::RiskGovernor governor_{};
    haruquant::risk::RiskAccountState risk_state_{10000.0, 10000.0, 0.0, 0.0};
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
    TradeRecord trade{};
};

using TradeEventCallback = std::function<void(const BacktestTradeEvent&, const SimulatorState&)>;

class BacktestEngine {
public:
    explicit BacktestEngine(TradeSimulator& client);

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
    [[nodiscard]] const haruquant::AccountInfo& account_snapshot() const noexcept;
    [[nodiscard]] std::optional<AutoCloseReason> close_reason(uint64_t ticket) const;
    [[nodiscard]] const std::vector<TradeRecord>& completed_trades() const noexcept;

private:
    void ensure_trade_record_for_position(const haruquant::PositionInfo& pos, int64_t now_msc);
    void close_position_and_track(const haruquant::PositionInfo& pos, int64_t now_msc, double close_price);
    double lookup_deal_profit_or_fallback(uint64_t deal_ticket, const haruquant::PositionInfo& pos, double close_price) const;
    void monitor_pending_orders(const std::string& symbol, double bid, double ask, int64_t current_time_msc);
    void monitor_positions_and_account(const std::string& symbol, double bid, double ask);
    static bool should_trigger_order(const haruquant::OrderInfo& order, double bid, double ask);
    void apply_exit_signal(const std::string& symbol, int exit_signal);
    void apply_entry_signal(
        const std::string& symbol,
        double volume,
        int entry_signal,
        double bid,
        double ask,
        double sl,
        double tp);

    TradeSimulator& client_;
    SimulatorState state_{};
    AccountMonitor account_monitor_{};
    TradeRecordTracker trade_record_tracker_{};
    haruquant::AccountInfo account_snapshot_{};
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
    explicit PortfolioEngine(TradeSimulator& client);

    void run_equal_weight(
        const std::vector<PortfolioSymbolInput>& inputs,
        double base_volume);

    void run_with_allocations(
        const std::vector<PortfolioSymbolInput>& inputs,
        double base_volume,
        const std::unordered_map<std::string, double>& allocations);

    [[nodiscard]] const std::unordered_map<std::string, double>& effective_allocations() const noexcept;

private:
    static double normalize_volume(double requested, const haruquant::SymbolInfo& symbol_info);
    void process_bar(const std::string& symbol, const BacktestBarStep& bar, double base_volume);

    TradeSimulator& client_;
    std::unordered_map<std::string, double> effective_allocations_{};
};

class VectorizedBacktestEngine {
public:
    explicit VectorizedBacktestEngine(TradeSimulator& client);

    void run(
        const std::string& symbol,
        double volume,
        const std::vector<BacktestBarStep>& bars);

    [[nodiscard]] const haruquant::AccountInfo& account_snapshot() const noexcept;
    [[nodiscard]] std::size_t processed_bars() const noexcept;
    [[nodiscard]] std::size_t total_trades() const noexcept;

private:
    static double normalize_volume(double requested, const haruquant::SymbolInfo& symbol_info);

    TradeSimulator& client_;
    haruquant::AccountInfo account_snapshot_{};
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

struct ReplayTradeEvent {
    int64_t time_msc{0};
    std::string symbol{};
    std::string side{};
    double price{0.0};
    double volume{0.0};
    uint64_t ticket{0};
};

struct ReplayCertificationResult {
    bool consistent{false};
    std::string baseline_fingerprint{};
    std::string candidate_fingerprint{};
    std::string message{};
};

class ReplayCertifier {
public:
    [[nodiscard]] static std::string fingerprint(const std::vector<ReplayTradeEvent>& events);
    [[nodiscard]] static ReplayCertificationResult compare(
        const std::vector<ReplayTradeEvent>& baseline,
        const std::vector<ReplayTradeEvent>& candidate);
};

struct WfoSpec {
    std::size_t train_bars{0};
    std::size_t test_bars{0};
    std::size_t step_bars{0};
};

struct WfoWindow {
    std::size_t train_start{0};
    std::size_t train_end{0};
    std::size_t test_start{0};
    std::size_t test_end{0};
};

struct WfoWindowResult {
    WfoWindow window{};
    double train_score{0.0};
    double test_score{0.0};
};

struct WfoSummary {
    std::size_t num_windows{0};
    double avg_train_score{0.0};
    double avg_test_score{0.0};
    double std_train_score{0.0};
    double std_test_score{0.0};
    double train_test_correlation{0.0};
    double overfitting_ratio{0.0};
};

struct WfmCellResult {
    WfoSpec spec{};
    WfoSummary summary{};
};

class WfoWfmOrchestrator {
public:
    [[nodiscard]] static std::vector<WfoWindow> build_windows(std::size_t total_bars, const WfoSpec& spec);

    [[nodiscard]] static std::vector<WfoWindowResult> run_wfo(
        std::size_t total_bars,
        const WfoSpec& spec,
        const std::function<double(const WfoWindow&, bool)>& evaluator);

    [[nodiscard]] static WfoSummary summarize(const std::vector<WfoWindowResult>& results);

    [[nodiscard]] static std::vector<WfmCellResult> run_wfm(
        std::size_t total_bars,
        const std::vector<WfoSpec>& matrix_specs,
        const std::function<double(const WfoWindow&, bool)>& evaluator);
};

struct EdgeDetectorReport {
    std::size_t windows{0};
    double mean_test_score{0.0};
    double p_value{1.0};
    bool skill_confirmed{false};
    std::string verdict{"NO_EDGE"};
};

class EdgeDetector {
public:
    [[nodiscard]] static EdgeDetectorReport from_wfo(
        const std::vector<WfoWindowResult>& results,
        double alpha = 0.05);
};

struct ExperimentRecord {
    std::string experiment_id{};
    std::string strategy{};
    std::string symbol{};
    std::string timeframe{};
    int64_t period_start_msc{0};
    int64_t period_end_msc{0};
    Dict metadata{};
};

class ExperimentRegistry {
public:
    void upsert(const ExperimentRecord& record);
    [[nodiscard]] std::vector<ExperimentRecord> all() const;
    [[nodiscard]] std::vector<ExperimentRecord> query(
        std::optional<std::string_view> strategy = std::nullopt,
        std::optional<std::string_view> symbol = std::nullopt,
        std::optional<int64_t> period_start_msc = std::nullopt,
        std::optional<int64_t> period_end_msc = std::nullopt) const;

private:
    std::unordered_map<std::string, ExperimentRecord> records_{};
};

struct SymbolClassification {
    std::string asset_class{"unknown"};
    std::string volatility_regime{"normal"};
};

class SymbolClassifier {
public:
    [[nodiscard]] static SymbolClassification classify(
        std::string_view symbol,
        double annualized_volatility);
};

struct SeasonalBucket {
    int key{0};
    std::size_t count{0};
    double mean_return{0.0};
};

struct SeasonalAnalysis {
    std::vector<SeasonalBucket> day_of_week{};
    std::vector<SeasonalBucket> holiday_vs_non_holiday{};
};

class SeasonalPatternAnalyzer {
public:
    [[nodiscard]] static SeasonalAnalysis analyze(
        const std::vector<int64_t>& timestamps_msc,
        const std::vector<double>& returns,
        const std::unordered_set<int64_t>& holiday_days_epoch = {});
};

using OptimizationParamSpace = std::unordered_map<std::string, std::vector<double>>;

struct OptimizationTrial {
    std::unordered_map<std::string, double> params{};
    double score{0.0};
    std::size_t iteration{0};
    std::size_t generation{0};
};

struct OptimizationWorkerPolicy {
    std::size_t max_workers{4};
    std::size_t max_restarts{1};
    int64_t task_timeout_ms{30000};
    int64_t heartbeat_ms{100};
};

struct OptimizationWorkerHealth {
    std::size_t submitted{0};
    std::size_t completed{0};
    std::size_t failed{0};
    std::size_t restarted{0};
    std::size_t timeout_restarts{0};
};

struct DistributedOptimizationResult {
    std::vector<OptimizationTrial> trials{};
    OptimizationWorkerHealth health{};
};

class GridSearchRunner {
public:
    [[nodiscard]] static std::vector<OptimizationTrial> run(
        const OptimizationParamSpace& space,
        const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
        std::size_t max_evals = 0);
};

class RandomSearchRunner {
public:
    [[nodiscard]] static std::vector<OptimizationTrial> run(
        const OptimizationParamSpace& space,
        std::size_t samples,
        std::uint64_t seed,
        const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator);
};

class GeneticSearchRunner {
public:
    [[nodiscard]] static std::vector<OptimizationTrial> run(
        const OptimizationParamSpace& space,
        std::size_t population_size,
        std::size_t generations,
        std::uint64_t seed,
        const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
        double mutation_rate = 0.15);
};

class BayesianSearchRunner {
public:
    [[nodiscard]] static std::vector<OptimizationTrial> run(
        const OptimizationParamSpace& space,
        std::size_t iterations,
        std::uint64_t seed,
        const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
        std::size_t random_warmup = 5,
        double exploration_weight = 0.20);
};

class DistributedOptimizationRunner {
public:
    [[nodiscard]] static DistributedOptimizationResult run(
        const std::vector<std::unordered_map<std::string, double>>& params_list,
        const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
        OptimizationWorkerPolicy policy = {});
};

struct MonteCarloSummary {
    std::size_t simulations{0};
    double mean{0.0};
    double stddev{0.0};
    double p05{0.0};
    double p50{0.0};
    double p95{0.0};
    double probability_positive{0.0};
};

enum class MonteCarloMode {
    Shuffle = 0,
    Bootstrap = 1,
    Perturb = 2,
};

struct SensitivityPoint {
    std::string param{};
    double value{0.0};
    double score{0.0};
};

struct SensitivityReport {
    std::size_t evaluations{0};
    double stability_score{0.0};
    std::unordered_map<std::string, double> normalized_sensitivity{};
    std::vector<SensitivityPoint> points{};
};

class MonteCarloAnalyzer {
public:
    [[nodiscard]] static MonteCarloSummary simulate(
        const std::vector<double>& pnl_series,
        std::size_t simulations,
        std::uint64_t seed = 7,
        MonteCarloMode mode = MonteCarloMode::Bootstrap,
        double perturb_scale = 0.10);
};

class SensitivityAnalyzer {
public:
    [[nodiscard]] static SensitivityReport analyze(
        const OptimizationParamSpace& space,
        const std::function<double(const std::unordered_map<std::string, double>&)>& evaluator,
        std::size_t max_points = 0);
};

}  // namespace haruquant::sim

namespace haruquant::engine {

class Engine {
public:
    explicit Engine(haruquant::sim::TradeSimulator& client);

    void run_trading_timeframe(
        const std::string& symbol,
        double volume,
        const std::vector<haruquant::sim::BacktestBarStep>& bars);

    void run_trading_timeframe_with_ticks(
        const std::string& symbol,
        double volume,
        const std::vector<haruquant::sim::BacktestBarStep>& bars,
        const std::vector<haruquant::sim::ModelTick>& ticks);

    [[nodiscard]] const haruquant::sim::SimulatorState& state() const noexcept;
    [[nodiscard]] const haruquant::AccountInfo& account_snapshot() const noexcept;
    [[nodiscard]] const std::vector<haruquant::sim::TradeRecord>& completed_trades() const noexcept;

private:
    haruquant::sim::BacktestEngine impl_;
};

}  // namespace haruquant::engine

