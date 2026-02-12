/**
 * @file currency_converter.hpp
 * @brief Multi-hop currency conversion with dependency graph
 *
 * Implements BFS-based path finding for currency conversions.
 * Supports direct, inverted, and multi-hop conversion paths.
 */

#pragma once

#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <stdexcept>
#include <cmath>

namespace hqt {

/**
 * @brief Exception thrown when no conversion path exists
 */
class ConversionPathError : public std::runtime_error {
public:
    explicit ConversionPathError(const std::string& msg)
        : std::runtime_error(msg) {}
};

/**
 * @brief Currency pair exchange rate
 */
struct CurrencyPair {
    std::string base;      ///< Base currency (e.g., "EUR")
    std::string quote;     ///< Quote currency (e.g., "USD")
    double rate;           ///< Exchange rate (1 base = rate quote)
    int64_t timestamp_us;  ///< Last update timestamp (microseconds)

    CurrencyPair() : rate(1.0), timestamp_us(0) {}

    CurrencyPair(const std::string& b, const std::string& q, double r, int64_t ts = 0)
        : base(b), quote(q), rate(r), timestamp_us(ts) {}

    /**
     * @brief Get pair identifier "BASE/QUOTE"
     */
    std::string to_string() const {
        return base + "/" + quote;
    }
};

/**
 * @brief Multi-hop currency converter with BFS path finding
 *
 * Maintains a directed graph of currency pairs and finds optimal
 * conversion paths using breadth-first search.
 *
 * Example:
 * @code
 * CurrencyConverter conv;
 * conv.register_pair("EUR", "USD", 1.10);
 * conv.register_pair("USD", "JPY", 150.0);
 *
 * // Direct conversion
 * double result = conv.convert(100.0, "EUR", "USD"); // 110.0
 *
 * // Multi-hop conversion EUR -> USD -> JPY
 * double yen = conv.convert(100.0, "EUR", "JPY"); // 16500.0
 * @endcode
 */
class CurrencyConverter {
public:
    CurrencyConverter() = default;

    /**
     * @brief Register or update a currency pair
     * @param base Base currency code
     * @param quote Quote currency code
     * @param rate Exchange rate (1 base = rate quote)
     * @param timestamp_us Timestamp of rate (default: 0)
     *
     * Automatically registers both forward (base->quote) and
     * inverse (quote->base) edges in the graph.
     */
    void register_pair(const std::string& base,
                      const std::string& quote,
                      double rate,
                      int64_t timestamp_us = 0) noexcept {
        std::string pair_id = base + "/" + quote;
        pairs_[pair_id] = CurrencyPair(base, quote, rate, timestamp_us);

        // Build adjacency graph for BFS
        graph_[base].insert(quote);
        graph_[quote].insert(base);  // Inverse path
    }

    /**
     * @brief Update exchange rate for existing pair
     * @param base Base currency code
     * @param quote Quote currency code
     * @param rate New exchange rate
     * @param timestamp_us Timestamp of update
     * @throws ConversionPathError if pair not registered
     */
    void update_rate(const std::string& base,
                    const std::string& quote,
                    double rate,
                    int64_t timestamp_us) {
        std::string pair_id = base + "/" + quote;
        auto it = pairs_.find(pair_id);
        if (it == pairs_.end()) {
            throw ConversionPathError("Pair " + pair_id + " not registered");
        }
        it->second.rate = rate;
        it->second.timestamp_us = timestamp_us;
    }

    /**
     * @brief Check if direct pair exists
     * @param base Base currency
     * @param quote Quote currency
     * @return True if direct pair registered
     */
    bool has_pair(const std::string& base, const std::string& quote) const noexcept {
        return pairs_.find(base + "/" + quote) != pairs_.end();
    }

    /**
     * @brief Get exchange rate for direct pair
     * @param base Base currency
     * @param quote Quote currency
     * @return Exchange rate
     * @throws ConversionPathError if pair doesn't exist
     */
    double get_rate(const std::string& base, const std::string& quote) const {
        std::string pair_id = base + "/" + quote;
        auto it = pairs_.find(pair_id);
        if (it == pairs_.end()) {
            throw ConversionPathError("No direct pair: " + pair_id);
        }
        return it->second.rate;
    }

    /**
     * @brief Convert amount from one currency to another
     * @param amount Amount in source currency
     * @param from Source currency code
     * @param to Target currency code
     * @return Converted amount in target currency
     * @throws ConversionPathError if no conversion path exists
     *
     * Uses BFS to find shortest conversion path. Supports:
     * - Direct conversion (EUR->USD)
     * - Inverted conversion (USD->EUR using EUR/USD rate)
     * - Multi-hop conversion (EUR->USD->JPY)
     */
    double convert(double amount,
                  const std::string& from,
                  const std::string& to) const {
        // Same currency - no conversion needed
        if (from == to) return amount;

        // Try direct conversion
        std::string direct_pair = from + "/" + to;
        auto it = pairs_.find(direct_pair);
        if (it != pairs_.end()) {
            return amount * it->second.rate;
        }

        // Try inverted conversion
        std::string inverse_pair = to + "/" + from;
        it = pairs_.find(inverse_pair);
        if (it != pairs_.end()) {
            return amount / it->second.rate;
        }

        // Multi-hop conversion using BFS
        auto path = find_path(from, to);
        if (path.empty()) {
            throw ConversionPathError(
                "No conversion path from " + from + " to " + to
            );
        }

        // Apply conversions along path
        double result = amount;
        for (size_t i = 0; i < path.size() - 1; ++i) {
            const std::string& curr = path[i];
            const std::string& next = path[i + 1];

            // Try direct pair
            std::string pair_id = curr + "/" + next;
            it = pairs_.find(pair_id);
            if (it != pairs_.end()) {
                result *= it->second.rate;
                continue;
            }

            // Try inverse pair
            pair_id = next + "/" + curr;
            it = pairs_.find(pair_id);
            if (it != pairs_.end()) {
                result /= it->second.rate;
                continue;
            }

            // Should never happen if find_path worked correctly
            throw ConversionPathError(
                "Path validation failed: " + curr + " -> " + next
            );
        }

        return result;
    }

    /**
     * @brief Find shortest conversion path using BFS
     * @param from Source currency
     * @param to Target currency
     * @return Vector of currencies forming path (empty if no path)
     *
     * Example: ["EUR", "USD", "JPY"] means EUR->USD->JPY
     */
    std::vector<std::string> find_path(const std::string& from,
                                       const std::string& to) const {
        if (from == to) return {from};

        // Check if currencies exist in graph
        if (graph_.find(from) == graph_.end()) return {};
        if (graph_.find(to) == graph_.end()) return {};

        // BFS to find shortest path
        std::unordered_map<std::string, std::string> parent;
        std::unordered_set<std::string> visited;
        std::vector<std::string> queue;

        queue.push_back(from);
        visited.insert(from);
        parent[from] = "";

        while (!queue.empty()) {
            std::string current = queue.front();
            queue.erase(queue.begin());

            if (current == to) {
                // Reconstruct path
                std::vector<std::string> path;
                std::string node = to;
                while (!node.empty()) {
                    path.push_back(node);
                    node = parent[node];
                }
                std::reverse(path.begin(), path.end());
                return path;
            }

            // Explore neighbors
            auto neighbors_it = graph_.find(current);
            if (neighbors_it != graph_.end()) {
                for (const auto& neighbor : neighbors_it->second) {
                    if (visited.find(neighbor) == visited.end()) {
                        visited.insert(neighbor);
                        parent[neighbor] = current;
                        queue.push_back(neighbor);
                    }
                }
            }
        }

        return {};  // No path found
    }

    /**
     * @brief Get all registered currency pairs
     */
    const std::unordered_map<std::string, CurrencyPair>& pairs() const noexcept {
        return pairs_;
    }

    /**
     * @brief Get number of registered pairs
     */
    size_t pair_count() const noexcept {
        return pairs_.size();
    }

    /**
     * @brief Validate that all paths are reachable
     * @throws ConversionPathError if graph has disconnected components
     *
     * Useful for configuration validation at startup.
     */
    void validate_paths() const {
        if (graph_.empty()) return;

        // Get all unique currencies
        std::unordered_set<std::string> all_currencies;
        for (const auto& [pair_id, pair] : pairs_) {
            all_currencies.insert(pair.base);
            all_currencies.insert(pair.quote);
        }

        // Check if all currencies are reachable from first currency
        if (all_currencies.empty()) return;

        std::string start = *all_currencies.begin();
        std::unordered_set<std::string> reachable;
        std::vector<std::string> queue = {start};
        reachable.insert(start);

        while (!queue.empty()) {
            std::string current = queue.front();
            queue.erase(queue.begin());

            auto neighbors_it = graph_.find(current);
            if (neighbors_it != graph_.end()) {
                for (const auto& neighbor : neighbors_it->second) {
                    if (reachable.find(neighbor) == reachable.end()) {
                        reachable.insert(neighbor);
                        queue.push_back(neighbor);
                    }
                }
            }
        }

        // Check if all currencies are reachable
        for (const auto& currency : all_currencies) {
            if (reachable.find(currency) == reachable.end()) {
                throw ConversionPathError(
                    "Currency " + currency + " is not reachable from " + start +
                    ". Graph has disconnected components."
                );
            }
        }
    }

    /**
     * @brief Clear all registered pairs
     */
    void clear() noexcept {
        pairs_.clear();
        graph_.clear();
    }

private:
    /// Map of "BASE/QUOTE" -> CurrencyPair
    std::unordered_map<std::string, CurrencyPair> pairs_;

    /// Adjacency list for BFS (currency -> set of connected currencies)
    std::unordered_map<std::string, std::unordered_set<std::string>> graph_;
};

} // namespace hqt
