/**
 * @file random.hpp
 * @brief Seeded pseudo-random number generator wrapper
 *
 * Provides deterministic random number generation for reproducible backtests.
 * Uses std::mt19937_64 (Mersenne Twister) for high-quality random numbers.
 */

#pragma once

#include <cstdint>
#include <random>
#include <limits>

namespace hqt {

/**
 * @brief Seeded random number generator for deterministic behavior
 *
 * All randomness in the system (slippage models, Monte Carlo, etc.)
 * uses this seeded RNG to ensure bit-identical reproducibility.
 * The seed is stored with backtest results for exact replay.
 */
class SeededRNG {
public:
    /**
     * @brief Construct with specific seed
     * @param seed Random seed (use same seed for identical results)
     */
    explicit SeededRNG(uint64_t seed) noexcept
        : engine_(seed)
        , seed_(seed)
    {}

    /**
     * @brief Construct with random seed from std::random_device
     */
    SeededRNG() noexcept
        : engine_(std::random_device{}())
        , seed_(engine_())
    {}

    /**
     * @brief Get the seed used to initialize this RNG
     * @return Seed value
     */
    [[nodiscard]] uint64_t get_seed() const noexcept {
        return seed_;
    }

    /**
     * @brief Reset RNG to initial seed
     */
    void reset() noexcept {
        engine_.seed(seed_);
    }

    /**
     * @brief Reset with new seed
     * @param new_seed New seed value
     */
    void reset(uint64_t new_seed) noexcept {
        seed_ = new_seed;
        engine_.seed(seed_);
    }

    /**
     * @brief Generate random integer in range [min, max] (inclusive)
     * @param min Minimum value (inclusive)
     * @param max Maximum value (inclusive)
     * @return Random integer in [min, max]
     */
    [[nodiscard]] int64_t next_int(int64_t min, int64_t max) noexcept {
        if (min >= max) return min;
        std::uniform_int_distribution<int64_t> dist(min, max);
        return dist(engine_);
    }

    /**
     * @brief Generate random integer in range [0, max] (inclusive)
     * @param max Maximum value (inclusive)
     * @return Random integer in [0, max]
     */
    [[nodiscard]] int64_t next_int(int64_t max) noexcept {
        return next_int(0, max);
    }

    /**
     * @brief Generate random double in range [min, max) (max exclusive)
     * @param min Minimum value (inclusive)
     * @param max Maximum value (exclusive)
     * @return Random double in [min, max)
     */
    [[nodiscard]] double next_double(double min, double max) noexcept {
        if (min >= max) return min;
        std::uniform_real_distribution<double> dist(min, max);
        return dist(engine_);
    }

    /**
     * @brief Generate random double in range [0.0, 1.0) (1.0 exclusive)
     * @return Random double in [0.0, 1.0)
     */
    [[nodiscard]] double next_double() noexcept {
        return next_double(0.0, 1.0);
    }

    /**
     * @brief Generate random boolean with given probability
     * @param probability Probability of returning true (0.0 to 1.0)
     * @return true with given probability, false otherwise
     */
    [[nodiscard]] bool next_bool(double probability = 0.5) noexcept {
        if (probability <= 0.0) return false;
        if (probability >= 1.0) return true;
        return next_double() < probability;
    }

    /**
     * @brief Generate random number from normal distribution
     * @param mean Mean of the distribution
     * @param stddev Standard deviation
     * @return Random value from N(mean, stddev²)
     */
    [[nodiscard]] double next_normal(double mean = 0.0, double stddev = 1.0) noexcept {
        std::normal_distribution<double> dist(mean, stddev);
        return dist(engine_);
    }

    /**
     * @brief Generate random number from exponential distribution
     * @param lambda Rate parameter (λ)
     * @return Random value from Exp(λ)
     */
    [[nodiscard]] double next_exponential(double lambda = 1.0) noexcept {
        std::exponential_distribution<double> dist(lambda);
        return dist(engine_);
    }

    /**
     * @brief Shuffle a range of elements
     * @tparam RandomIt Random access iterator type
     * @param first Iterator to first element
     * @param last Iterator past last element
     */
    template<typename RandomIt>
    void shuffle(RandomIt first, RandomIt last) noexcept {
        std::shuffle(first, last, engine_);
    }

    /**
     * @brief Get raw engine for advanced use cases
     * @return Reference to underlying mt19937_64 engine
     */
    [[nodiscard]] std::mt19937_64& engine() noexcept {
        return engine_;
    }

    /**
     * @brief Get raw engine (const version)
     */
    [[nodiscard]] const std::mt19937_64& engine() const noexcept {
        return engine_;
    }

private:
    std::mt19937_64 engine_;  ///< Mersenne Twister 64-bit engine
    uint64_t seed_;           ///< Seed used to initialize the engine
};

/**
 * @brief Global default RNG (NOT RECOMMENDED for production use)
 *
 * For quick prototyping only. Production code should use explicit
 * SeededRNG instances with known seeds for reproducibility.
 */
inline SeededRNG& global_rng() {
    static SeededRNG rng;
    return rng;
}

} // namespace hqt
