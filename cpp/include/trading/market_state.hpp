/**
 * @file market_state.hpp
 * @brief Real-time market state tracker
 *
 * Maintains current bid/ask/spread for all symbols.
 * Updates from tick data and provides fast price lookups.
 */

#pragma once

#include "symbol_info.hpp"
#include "data/tick.hpp"
#include <string>
#include <unordered_map>
#include <cmath>

namespace hqt {

/**
 * @brief Current market prices for a symbol
 */
struct MarketPrice {
    std::string symbol;     ///< Symbol name
    double bid;             ///< Current bid price
    double ask;             ///< Current ask price
    double last;            ///< Last trade price
    int64_t bid_volume;     ///< Bid volume
    int64_t ask_volume;     ///< Ask volume
    int64_t timestamp_us;   ///< Last update timestamp (microseconds)

    MarketPrice()
        : bid(0.0), ask(0.0), last(0.0),
          bid_volume(0), ask_volume(0), timestamp_us(0) {}

    /**
     * @brief Get spread in price units
     */
    double spread() const noexcept {
        return ask - bid;
    }

    /**
     * @brief Get spread in points
     * @param point_size Size of one point (e.g., 0.00001 for 5-digit)
     */
    int32_t spread_points(double point_size) const noexcept {
        if (point_size <= 0.0) return 0;
        return static_cast<int32_t>(spread() / point_size);
    }

    /**
     * @brief Get mid price
     */
    double mid() const noexcept {
        return (bid + ask) / 2.0;
    }

    /**
     * @brief Check if prices are valid
     */
    bool is_valid() const noexcept {
        return bid > 0.0 && ask > 0.0 && ask >= bid;
    }
};

/**
 * @brief Market state tracker for all symbols
 *
 * Maintains real-time market prices and provides fast lookups.
 * Updates from tick data during backtesting or live trading.
 *
 * Example:
 * @code
 * MarketState market;
 *
 * // Update prices from tick
 * Tick tick = ...;
 * market.on_tick(tick, symbol_info);
 *
 * // Get current prices
 * if (market.has_symbol("EURUSD")) {
 *     double bid = market.get_bid("EURUSD");
 *     double ask = market.get_ask("EURUSD");
 *     int32_t spread = market.get_spread_points("EURUSD");
 * }
 * @endcode
 */
class MarketState {
public:
    MarketState() = default;

    /**
     * @brief Update market prices from tick
     * @param tick Tick data
     * @param symbol Symbol information
     *
     * Converts tick prices from fixed-point to double and updates
     * the market state.
     */
    void on_tick(const Tick& tick, const SymbolInfo& symbol) noexcept {
        MarketPrice& price = prices_[symbol.Name()];

        price.symbol = symbol.Name();
        price.bid = symbol.NormalizePrice(static_cast<double>(tick.bid));
        price.ask = symbol.NormalizePrice(static_cast<double>(tick.ask));
        price.last = price.mid();
        price.bid_volume = tick.bid_volume;
        price.ask_volume = tick.ask_volume;
        price.timestamp_us = tick.timestamp_us;
    }

    /**
     * @brief Update prices directly
     * @param symbol Symbol name
     * @param bid Bid price
     * @param ask Ask price
     * @param timestamp_us Timestamp (default: 0)
     */
    void update_price(const std::string& symbol,
                     double bid,
                     double ask,
                     int64_t timestamp_us = 0) noexcept {
        MarketPrice& price = prices_[symbol];

        price.symbol = symbol;
        price.bid = bid;
        price.ask = ask;
        price.last = (bid + ask) / 2.0;
        price.timestamp_us = timestamp_us;
    }

    /**
     * @brief Check if symbol has prices
     * @param symbol Symbol name
     * @return True if symbol exists and has valid prices
     */
    bool has_symbol(const std::string& symbol) const noexcept {
        auto it = prices_.find(symbol);
        return it != prices_.end() && it->second.is_valid();
    }

    /**
     * @brief Get current bid price
     * @param symbol Symbol name
     * @return Bid price (0.0 if not found)
     */
    double get_bid(const std::string& symbol) const noexcept {
        auto it = prices_.find(symbol);
        return (it != prices_.end()) ? it->second.bid : 0.0;
    }

    /**
     * @brief Get current ask price
     * @param symbol Symbol name
     * @return Ask price (0.0 if not found)
     */
    double get_ask(const std::string& symbol) const noexcept {
        auto it = prices_.find(symbol);
        return (it != prices_.end()) ? it->second.ask : 0.0;
    }

    /**
     * @brief Get last trade price
     * @param symbol Symbol name
     * @return Last price (0.0 if not found)
     */
    double get_last(const std::string& symbol) const noexcept {
        auto it = prices_.find(symbol);
        return (it != prices_.end()) ? it->second.last : 0.0;
    }

    /**
     * @brief Get mid price
     * @param symbol Symbol name
     * @return Mid price (0.0 if not found)
     */
    double get_mid(const std::string& symbol) const noexcept {
        auto it = prices_.find(symbol);
        return (it != prices_.end()) ? it->second.mid() : 0.0;
    }

    /**
     * @brief Get spread in price units
     * @param symbol Symbol name
     * @return Spread (0.0 if not found)
     */
    double get_spread(const std::string& symbol) const noexcept {
        auto it = prices_.find(symbol);
        return (it != prices_.end()) ? it->second.spread() : 0.0;
    }

    /**
     * @brief Get spread in points
     * @param symbol Symbol name
     * @param point_size Size of one point (default: 0.00001 for 5-digit)
     * @return Spread in points (0 if not found)
     */
    int32_t get_spread_points(const std::string& symbol,
                             double point_size = 0.00001) const noexcept {
        auto it = prices_.find(symbol);
        return (it != prices_.end()) ? it->second.spread_points(point_size) : 0;
    }

    /**
     * @brief Get complete market price data
     * @param symbol Symbol name
     * @return MarketPrice struct (empty if not found)
     */
    MarketPrice get_price(const std::string& symbol) const noexcept {
        auto it = prices_.find(symbol);
        return (it != prices_.end()) ? it->second : MarketPrice();
    }

    /**
     * @brief Get all market prices
     * @return Map of symbol -> MarketPrice
     */
    const std::unordered_map<std::string, MarketPrice>& prices() const noexcept {
        return prices_;
    }

    /**
     * @brief Get number of symbols tracked
     */
    size_t size() const noexcept {
        return prices_.size();
    }

    /**
     * @brief Clear all prices
     */
    void clear() noexcept {
        prices_.clear();
    }

    /**
     * @brief Remove symbol from tracking
     * @param symbol Symbol name
     */
    void remove_symbol(const std::string& symbol) noexcept {
        prices_.erase(symbol);
    }

    /**
     * @brief Get timestamp of last update for symbol
     * @param symbol Symbol name
     * @return Timestamp in microseconds (0 if not found)
     */
    int64_t get_timestamp(const std::string& symbol) const noexcept {
        auto it = prices_.find(symbol);
        return (it != prices_.end()) ? it->second.timestamp_us : 0;
    }

    /**
     * @brief Check if prices are stale
     * @param symbol Symbol name
     * @param current_time_us Current timestamp
     * @param max_age_us Maximum age in microseconds
     * @return True if prices are too old
     */
    bool is_stale(const std::string& symbol,
                 int64_t current_time_us,
                 int64_t max_age_us = 60'000'000) const noexcept {
        auto it = prices_.find(symbol);
        if (it == prices_.end()) return true;

        int64_t age = current_time_us - it->second.timestamp_us;
        return age > max_age_us;
    }

private:
    /// Map of symbol name -> current prices
    std::unordered_map<std::string, MarketPrice> prices_;
};

} // namespace hqt
