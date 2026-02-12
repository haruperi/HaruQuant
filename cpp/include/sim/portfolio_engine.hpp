/**
 * @file portfolio_engine.hpp
 * @brief Minimal multi-symbol synchronized portfolio engine.
 */

#pragma once

#include "sim/backtest_engine.hpp"
#include "sim/simulator_client.hpp"

#include <string>
#include <unordered_map>
#include <vector>

namespace hqt::sim {

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

}  // namespace hqt::sim

