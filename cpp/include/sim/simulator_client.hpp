/**
 * @file simulator_client.hpp
 * @brief MT5-like simulator client read API.
 *
 * PR-003 scope: non-mutating getter surface parity.
 */

#pragma once

#include "sim/sim_data.hpp"
#include "sim/trade_gateway.hpp"

#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

namespace hqt::sim {

/**
 * @brief Low-level simulated client with MT5-like getter API.
 */
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

    // Test/data-seeding helpers used by incremental migration PRs.
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

}  // namespace hqt::sim
