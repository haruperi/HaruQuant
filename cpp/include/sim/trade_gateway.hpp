/**
 * @file trade_gateway.hpp
 * @brief Adapter from simulator requests to CTrade execution.
 */

#pragma once

#include "sim/sim_data.hpp"
#include "trading/trade.hpp"

#include <string>
#include <unordered_map>

namespace hqt::sim {

/**
 * @brief Minimal MT5-like request for order_send market flow.
 */
struct TradeRequest {
    int action{0};
    int type{0};
    std::string symbol{};
    double volume{0.0};
    double price{0.0};
    double sl{0.0};
    double tp{0.0};
    std::string comment{};
};

/**
 * @brief Minimal MT5-like result payload.
 */
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

/**
 * @brief Executes simulator trade requests through CTrade.
 */
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

}  // namespace hqt::sim

