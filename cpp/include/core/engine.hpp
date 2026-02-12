/**
 * @file engine.hpp
 * @brief Main backtesting engine facade
 *
 * Wires together all components: EventLoop, CostsEngine, CTrade, DataFeed,
 * CurrencyConverter, and MarginCalculator into a unified interface.
 */

#pragma once

#include "core/event_loop.hpp"
#include "core/global_clock.hpp"
#include "core/zmq_broadcaster.hpp"
#include "core/write_ahead_log.hpp"
#include "data/data_feed.hpp"
#include "data/tick.hpp"
#include "trading/trade.hpp"
#include "trading/symbol_info.hpp"
#include "util/currency_converter.hpp"
#include "util/margin_calculator.hpp"
#include "costs/costs_engine.hpp"
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <stdexcept>

namespace hqt {

/**
 * @brief Engine exception
 */
class EngineError : public std::runtime_error {
public:
    explicit EngineError(const std::string& msg) : std::runtime_error(msg) {}
};

/**
 * @brief Callback function types
 */
using OnTickCallback = std::function<void(const Tick&, const SymbolInfo&)>;
using OnBarCallback = std::function<void(const Bar&, const SymbolInfo&, Timeframe)>;
using OnTradeCallback = std::function<void(const DealInfo&)>;
using OnOrderCallback = std::function<void(const OrderInfo&)>;

/**
 * @brief Main backtesting engine
 *
 * Central facade that coordinates all backtesting components:
 * - Event-driven simulation via EventLoop
 * - Market data access via DataFeed
 * - Trading operations via CTrade
 * - Execution costs via CostsEngine
 * - Currency conversion via CurrencyConverter
 * - Margin calculations via MarginCalculator
 *
 * Example:
 * @code
 * Engine engine(10000.0, "USD", 100);
 *
 * // Load symbols
 * engine.load_symbol("EURUSD", eurusd_info);
 * engine.load_conversion_pair("EUR", "USD", 1.10);
 *
 * // Register callbacks
 * engine.set_on_tick([](const Tick& tick, const SymbolInfo& symbol) {
 *     std::cout << "Tick: " << symbol.Name() << " @ " << tick.bid << std::endl;
 * });
 *
 * // Run simulation
 * engine.run();
 * @endcode
 */
class Engine {
private:
    // Core components
    EventLoop event_loop_;
    GlobalClock global_clock_;
    std::unique_ptr<IDataFeed> data_feed_;
    CTrade trade_;
    CurrencyConverter currency_converter_;
    std::unique_ptr<MarginCalculator> margin_calculator_;
    std::unique_ptr<CostsEngine> costs_engine_;

    // Observability & Recovery (optional)
    std::unique_ptr<ZmqBroadcaster> broadcaster_;
    std::unique_ptr<WriteAheadLog> wal_;

    // Callbacks
    OnTickCallback on_tick_;
    OnBarCallback on_bar_;
    OnTradeCallback on_trade_;
    OnOrderCallback on_order_;

    // Symbols
    std::unordered_map<std::string, SymbolInfo> symbols_;
    std::unordered_map<uint32_t, std::string> symbol_id_to_name_;

    // State
    bool running_;
    bool paused_;
    int64_t current_time_us_;

public:
    /**
     * @brief Construct engine with initial account state
     * @param initial_balance Initial account balance
     * @param currency Account currency (e.g., "USD")
     * @param leverage Account leverage (e.g., 100 for 1:100)
     */
    explicit Engine(double initial_balance = 10000.0,
                   const std::string& currency = "USD",
                   int leverage = 100)
        : event_loop_(),
          global_clock_(),
          data_feed_(std::make_unique<BarDataFeed>()),
          trade_(initial_balance, currency, leverage),
          currency_converter_(),
          margin_calculator_(std::make_unique<MarginCalculator>(currency_converter_)),
          costs_engine_(nullptr),
          on_tick_(),
          on_bar_(),
          on_trade_(),
          on_order_(),
          symbols_(),
          symbol_id_to_name_(),
          running_(false),
          paused_(false),
          current_time_us_(0) {
        // Initialize with default zero-cost models
        costs_engine_ = std::make_unique<CostsEngine>(
            std::make_unique<ZeroSlippage>(),
            std::make_unique<ZeroCommission>(),
            std::make_unique<ZeroSwap>(),
            std::make_unique<FixedSpread>(15)  // Default 1.5 pip spread
        );
    }

    // ========================================================================
    // Configuration
    // ========================================================================

    /**
     * @brief Load symbol into engine
     * @param symbol_name Symbol name (e.g., "EURUSD")
     * @param symbol_info Symbol information
     */
    void load_symbol(const std::string& symbol_name, const SymbolInfo& symbol_info) {
        SymbolInfo normalized = symbol_info;
        if (normalized.LotsMin() <= 0.0 || normalized.LotsMax() <= 0.0 || normalized.LotsStep() <= 0.0) {
            // TODO: Remove this fallback once symbol constraints are always sourced from MT5 metadata.
            normalized.SetVolumeMin(0.01);
            normalized.SetVolumeMax(100.0);
            normalized.SetVolumeStep(0.01);
        }

        symbols_[symbol_name] = normalized;
        symbol_id_to_name_[normalized.SymbolId()] = symbol_name;
        trade_.RegisterSymbol(normalized);
    }

    /**
     * @brief Load currency conversion pair
     * @param base Base currency (e.g., "EUR")
     * @param quote Quote currency (e.g., "USD")
     * @param rate Exchange rate (1 base = rate quote)
     */
    void load_conversion_pair(const std::string& base,
                             const std::string& quote,
                             double rate) {
        currency_converter_.register_pair(base, quote, rate);
    }

    /**
     * @brief Set execution cost models
     * @param slippage Slippage model
     * @param commission Commission model
     * @param swap Swap model
     * @param spread Spread model
     */
    void set_cost_models(std::unique_ptr<ISlippageModel> slippage,
                        std::unique_ptr<ICommissionModel> commission,
                        std::unique_ptr<ISwapModel> swap,
                        std::unique_ptr<ISpreadModel> spread) {
        costs_engine_ = std::make_unique<CostsEngine>(
            std::move(slippage),
            std::move(commission),
            std::move(swap),
            std::move(spread)
        );
    }

    /**
     * @brief Set data feed (replaces default BarDataFeed)
     * @param feed Data feed implementation
     */
    void set_data_feed(std::unique_ptr<IDataFeed> feed) {
        data_feed_ = std::move(feed);
    }

    /**
     * @brief Enable ZMQ broadcasting
     * @param endpoint ZMQ endpoint (e.g., "tcp://*:5555")
     */
    void enable_broadcasting(const std::string& endpoint = "tcp://*:5555") {
        broadcaster_ = std::make_unique<ZmqBroadcaster>(endpoint);
        broadcaster_->start();
    }

    /**
     * @brief Disable ZMQ broadcasting
     */
    void disable_broadcasting() {
        if (broadcaster_) {
            broadcaster_->stop();
            broadcaster_.reset();
        }
    }

    /**
     * @brief Check if broadcasting is enabled
     */
    bool is_broadcasting() const noexcept {
        return broadcaster_ && broadcaster_->is_running();
    }

    /**
     * @brief Enable Write-Ahead Log
     * @param file_path Path to WAL file
     * @param truncate If true, truncate existing WAL
     */
    void enable_wal(const std::string& file_path, bool truncate = false) {
        wal_ = std::make_unique<WriteAheadLog>(file_path);
        wal_->open(truncate);
    }

    /**
     * @brief Disable Write-Ahead Log
     */
    void disable_wal() {
        if (wal_) {
            wal_->close();
            wal_.reset();
        }
    }

    /**
     * @brief Check if WAL is enabled
     */
    bool is_wal_enabled() const noexcept {
        return wal_ && wal_->is_wal_open();
    }

    /**
     * @brief Recover from WAL
     *
     * Replays all uncommitted operations from WAL.
     * Should be called before run() if recovering from crash.
     */
    void recover_from_wal() {
        if (!wal_ || !wal_->is_wal_open()) {
            throw EngineError("WAL not enabled");
        }

        auto entries = wal_->read_uncommitted();
        for (const auto& [type, data] : entries) {
            replay_wal_entry(type, data);
        }

        // Mark checkpoint after successful recovery
        wal_->mark_checkpoint();
    }

    // ========================================================================
    // Callbacks
    // ========================================================================

    /**
     * @brief Register callback for tick events
     * @param callback Function called on each tick
     */
    void set_on_tick(OnTickCallback callback) {
        on_tick_ = std::move(callback);
    }

    /**
     * @brief Register callback for bar close events
     * @param callback Function called when bar closes
     */
    void set_on_bar(OnBarCallback callback) {
        on_bar_ = std::move(callback);
    }

    /**
     * @brief Register callback for trade events
     * @param callback Function called when deal is executed
     */
    void set_on_trade(OnTradeCallback callback) {
        on_trade_ = std::move(callback);
    }

    /**
     * @brief Register callback for order events
     * @param callback Function called when order state changes
     */
    void set_on_order(OnOrderCallback callback) {
        on_order_ = std::move(callback);
    }

    // ========================================================================
    // Event Loop Control
    // ========================================================================

    /**
     * @brief Run simulation until all events processed
     */
    void run() {
        running_ = true;
        paused_ = false;

        event_loop_.run([this](const Event& event) {
            if (!running_) {
                event_loop_.stop();
                return;
            }
            if (paused_) return;  // Continue but don't process

            process_event(event);
        });

        running_ = false;
    }

    /**
     * @brief Run N simulation steps
     * @param steps Number of events to process
     * @return Number of events actually processed
     */
    size_t run_steps(size_t steps) {
        running_ = true;

        size_t processed = 0;
        event_loop_.step(steps, [this, &processed](const Event& event) {
            if (!running_) {
                event_loop_.stop();
                return;
            }
            if (paused_) {
                // Preserve deterministic replay: do not drop events while paused.
                event_loop_.push(event);
                event_loop_.stop();
                return;
            }

            process_event(event);
            processed++;
        });

        running_ = false;
        return processed;
    }

    /**
     * @brief Pause simulation (can be resumed)
     */
    void pause() noexcept {
        paused_ = true;
    }

    /**
     * @brief Resume paused simulation
     */
    void resume() noexcept {
        paused_ = false;
    }

    /**
     * @brief Stop simulation completely
     */
    void stop() noexcept {
        running_ = false;
        event_loop_.stop();
    }

    /**
     * @brief Check if engine is running
     */
    bool is_running() const noexcept {
        return running_;
    }

    /**
     * @brief Check if engine is paused
     */
    bool is_paused() const noexcept {
        return paused_;
    }

    // ========================================================================
    // Trading Commands (with margin checks)
    // ========================================================================

    /**
     * @brief Open BUY position
     * @param volume Volume in lots
     * @param symbol Symbol name
     * @param sl Stop loss (0 = none)
     * @param tp Take profit (0 = none)
     * @param comment Order comment
     * @return True if successful
     */
    bool buy(double volume,
            const std::string& symbol,
            double sl = 0.0,
            double tp = 0.0,
            const std::string& comment = "") {
        // Margin check
        if (!check_margin_for_order(symbol, volume)) {
            return false;
        }

        return trade_.Buy(volume, symbol, 0.0, sl, tp, comment);
    }

    /**
     * @brief Open SELL position
     * @param volume Volume in lots
     * @param symbol Symbol name
     * @param sl Stop loss (0 = none)
     * @param tp Take profit (0 = none)
     * @param comment Order comment
     * @return True if successful
     */
    bool sell(double volume,
             const std::string& symbol,
             double sl = 0.0,
             double tp = 0.0,
             const std::string& comment = "") {
        // Margin check
        if (!check_margin_for_order(symbol, volume)) {
            return false;
        }

        return trade_.Sell(volume, symbol, 0.0, sl, tp, comment);
    }

    /**
     * @brief Modify position SL/TP
     * @param ticket Position ticket
     * @param sl New stop loss
     * @param tp New take profit
     * @return True if successful
     */
    bool modify(uint64_t ticket, double sl, double tp) {
        return trade_.PositionModify(ticket, sl, tp);
    }

    /**
     * @brief Close position
     * @param ticket Position ticket
     * @return True if successful
     */
    bool close(uint64_t ticket) {
        return trade_.PositionClose(ticket);
    }

    /**
     * @brief Cancel pending order
     * @param ticket Order ticket
     * @return True if successful
     */
    bool cancel(uint64_t ticket) {
        return trade_.OrderDelete(ticket);
    }

    // ========================================================================
    // State Access
    // ========================================================================

    /**
     * @brief Get account info
     */
    const AccountInfo& account() const noexcept {
        return trade_.Account();
    }

    /**
     * @brief Get all open positions
     */
    std::vector<PositionInfo> positions() const {
        return trade_.GetPositions();
    }

    /**
     * @brief Get all pending orders
     */
    std::vector<OrderInfo> orders() const {
        return trade_.GetOrders();
    }

    /**
     * @brief Get all deals
     */
    const std::vector<DealInfo>& deals() const {
        return trade_.GetDeals();
    }

    /**
     * @brief Get symbol info
     * @param symbol_name Symbol name
     * @return Const pointer to symbol info, or nullptr if not found
     */
    const SymbolInfo* get_symbol(const std::string& symbol_name) const noexcept {
        auto it = symbols_.find(symbol_name);
        return (it != symbols_.end()) ? &it->second : nullptr;
    }

    /**
     * @brief Get data feed
     */
    IDataFeed& data_feed() noexcept {
        return *data_feed_;
    }

    const IDataFeed& data_feed() const noexcept {
        return *data_feed_;
    }

    /**
     * @brief Get current simulation timestamp
     */
    int64_t current_time() const noexcept {
        return current_time_us_;
    }

    /**
     * @brief Get event loop
     */
    EventLoop& event_loop() noexcept {
        return event_loop_;
    }

    const EventLoop& event_loop() const noexcept {
        return event_loop_;
    }

private:
    /**
     * @brief Process a single event
     */
    void process_event(const Event& event) {
        current_time_us_ = event.timestamp_us;

        switch (event.type) {
            case EventType::TICK: {
                uint32_t symbol_id = event.data.tick_data.symbol_id;
                auto symbol_name_it = symbol_id_to_name_.find(symbol_id);
                if (symbol_name_it == symbol_id_to_name_.end()) break;

                auto symbol_it = symbols_.find(symbol_name_it->second);
                if (symbol_it == symbols_.end()) break;

                // For tick events, we need to get the tick from data feed
                // Events just trigger the callback, actual data comes from feed
                // This is simplified - actual implementation would pull tick from feed
                const auto& sym = symbol_it->second;
                Tick tick{
                    event.timestamp_us,
                    symbol_id,
                    static_cast<int64_t>(sym.Bid() * 1e6),
                    static_cast<int64_t>(sym.Ask() * 1e6),
                    0, 0, 0
                };

                // Update symbol prices (already done, but kept for consistency)
                trade_.UpdatePrices(symbol_it->second.Name(),
                                  sym.Bid(),
                                  sym.Ask(),
                                  tick.timestamp_us);

                // Broadcast tick (if enabled)
                if (broadcaster_ && broadcaster_->is_running()) {
                    broadcaster_->publish_tick(tick.symbol_id, tick.timestamp_us,
                                              tick.bid, tick.ask);
                }

                // Invoke callback
                if (on_tick_) {
                    on_tick_(tick, symbol_it->second);
                }
                break;
            }

            case EventType::BAR_CLOSE: {
                uint32_t symbol_id = event.data.bar_data.symbol_id;
                auto symbol_name_it = symbol_id_to_name_.find(symbol_id);
                if (symbol_name_it == symbol_id_to_name_.end()) break;

                auto symbol_it = symbols_.find(symbol_name_it->second);
                if (symbol_it == symbols_.end()) break;

                // Get bar from data feed
                try {
                    Timeframe tf = static_cast<Timeframe>(event.data.bar_data.timeframe);
                    Bar bar = data_feed_->get_last_bar(symbol_it->second.Name(), tf, event.timestamp_us);

                    // Broadcast bar (if enabled)
                    if (broadcaster_ && broadcaster_->is_running()) {
                        broadcaster_->publish_bar(bar.symbol_id, static_cast<uint16_t>(tf),
                                                 bar.timestamp_us, bar.open, bar.high,
                                                 bar.low, bar.close, bar.tick_volume);
                    }

                    // Invoke callback
                    if (on_bar_) {
                        on_bar_(bar, symbol_it->second, tf);
                    }
                } catch (const DataFeedError&) {
                    // Bar not available - skip
                }
                break;
            }

            case EventType::ORDER_TRIGGER:
            case EventType::TIMER:
                // Not implemented yet
                break;
        }

        // Update global clock (get symbol_id from appropriate event data)
        uint32_t symbol_id = 0;
        if (event.type == EventType::TICK) {
            symbol_id = event.data.tick_data.symbol_id;
        } else if (event.type == EventType::BAR_CLOSE) {
            symbol_id = event.data.bar_data.symbol_id;
        }
        if (symbol_id != 0) {
            global_clock_.update_symbol(symbol_id, event.timestamp_us);
        }
    }

    /**
     * @brief Check if sufficient margin for new order
     */
    bool check_margin_for_order(const std::string& symbol, double volume) {
        auto symbol_it = symbols_.find(symbol);
        if (symbol_it == symbols_.end()) return false;

        const SymbolInfo& symbol_info = symbol_it->second;

        // Calculate required margin
        double price = symbol_info.Ask();  // Use ask for margin calculation
        double margin = margin_calculator_->required_margin(
            symbol_info,
            ENUM_POSITION_TYPE::POSITION_TYPE_BUY,
            volume,
            price,
            trade_.Account().Leverage()
        );

        // Check if sufficient margin
        auto positions = trade_.GetPositions();
        std::unordered_map<std::string, SymbolInfo> symbols_map(symbols_.begin(), symbols_.end());

        return margin_calculator_->has_sufficient_margin(
            trade_.Account(),
            positions,
            symbols_map,
            margin,
            100.0  // Min 100% margin level
        );
    }

    /**
     * @brief Replay WAL entry during recovery
     * @param type Entry type
     * @param data Entry data
     */
    void replay_wal_entry(WALEntryType type, const std::vector<uint8_t>& data) {
        (void)data;  // Unused for now, will be used during deserialization
        // WAL replay is simplified for now
        // In production, this would deserialize the data and replay operations
        // For Task 3.8, we implement basic structure

        switch (type) {
            case WALEntryType::POSITION_OPEN:
                // TODO: Deserialize and replay position open
                break;

            case WALEntryType::POSITION_CLOSE:
                // TODO: Deserialize and replay position close
                break;

            case WALEntryType::POSITION_MODIFY:
                // TODO: Deserialize and replay position modify
                break;

            case WALEntryType::ORDER_PLACE:
                // TODO: Deserialize and replay order placement
                break;

            case WALEntryType::ORDER_CANCEL:
                // TODO: Deserialize and replay order cancellation
                break;

            case WALEntryType::BALANCE_CHANGE:
                // TODO: Deserialize and replay balance change
                break;

            case WALEntryType::CHECKPOINT:
                // Checkpoint marker - no action needed
                break;
        }
    }
};

} // namespace hqt
