/**
 * @file fixed_point.hpp
 * @brief Fixed-point arithmetic utilities
 *
 * All monetary calculations use int64_t fixed-point arithmetic to avoid
 * floating-point precision errors in profit/loss calculations.
 * Floating-point is only used for final display to users.
 */

#pragma once

#include <cstdint>
#include <cmath>
#include <stdexcept>

namespace hqt {

/**
 * @brief Fixed-point arithmetic utilities
 *
 * Represents decimal values as int64_t with implicit scaling factor.
 * Example with 5 digits: 1.10523 is stored as 110523
 *
 * This approach guarantees:
 * - No rounding errors in PnL accumulation
 * - Exact representation of decimal prices
 * - Fast integer arithmetic
 * - Deterministic reproducibility
 */
class FixedPoint {
public:
    /**
     * @brief Convert double to fixed-point representation
     * @param value Value in decimal form
     * @param digits Number of decimal places
     * @return Fixed-point representation (value × 10^digits)
     */
    [[nodiscard]] static constexpr int64_t from_double(double value, int32_t digits) noexcept {
        double multiplier = 1.0;
        for (int32_t i = 0; i < digits; ++i) {
            multiplier *= 10.0;
        }
        // Add 0.5 for rounding (if positive) or -0.5 (if negative)
        double scaled = value * multiplier;
        return static_cast<int64_t>(scaled + (scaled >= 0.0 ? 0.5 : -0.5));
    }

    /**
     * @brief Convert fixed-point to double representation
     * @param fixed_value Fixed-point value
     * @param digits Number of decimal places
     * @return Value as double
     */
    [[nodiscard]] static constexpr double to_double(int64_t fixed_value, int32_t digits) noexcept {
        double divisor = 1.0;
        for (int32_t i = 0; i < digits; ++i) {
            divisor *= 10.0;
        }
        return static_cast<double>(fixed_value) / divisor;
    }

    /**
     * @brief Add two fixed-point values
     * @param a First value
     * @param b Second value
     * @return Sum (a + b)
     */
    [[nodiscard]] static constexpr int64_t add(int64_t a, int64_t b) noexcept {
        return a + b;
    }

    /**
     * @brief Subtract two fixed-point values
     * @param a First value
     * @param b Second value
     * @return Difference (a - b)
     */
    [[nodiscard]] static constexpr int64_t subtract(int64_t a, int64_t b) noexcept {
        return a - b;
    }

    /**
     * @brief Multiply fixed-point value by integer
     * @param fixed_value Fixed-point value
     * @param multiplier Integer multiplier
     * @return Product
     */
    [[nodiscard]] static constexpr int64_t multiply_int(int64_t fixed_value, int64_t multiplier) noexcept {
        return fixed_value * multiplier;
    }

    /**
     * @brief Multiply two fixed-point values
     * @param a First value (with digits_a decimal places)
     * @param b Second value (with digits_b decimal places)
     * @param digits_a Decimal places in a
     * @param digits_b Decimal places in b
     * @param result_digits Desired decimal places in result
     * @return Product with result_digits decimal places
     *
     * Example: 1.1 (1 digit) × 2.5 (1 digit) = 2.75 (2 digits)
     *          11 × 25 = 275 (but needs adjustment for scaling)
     */
    [[nodiscard]] static constexpr int64_t multiply(int64_t a, int64_t b,
                                                     int32_t digits_a, int32_t digits_b,
                                                     int32_t result_digits) noexcept {
        // Product has (digits_a + digits_b) decimal places
        // Need to scale to result_digits
        const int32_t product_digits = digits_a + digits_b;
        const int32_t scale_diff = product_digits - result_digits;

        int64_t product = a * b;

        if (scale_diff > 0) {
            // Need to divide to reduce decimal places
            int64_t divisor = 1;
            for (int32_t i = 0; i < scale_diff; ++i) {
                divisor *= 10;
            }
            // Add half divisor for rounding
            product += (product >= 0 ? divisor / 2 : -divisor / 2);
            return product / divisor;
        } else if (scale_diff < 0) {
            // Need to multiply to increase decimal places
            int64_t multiplier = 1;
            for (int32_t i = 0; i < -scale_diff; ++i) {
                multiplier *= 10;
            }
            return product * multiplier;
        } else {
            // No scaling needed
            return product;
        }
    }

    /**
     * @brief Divide fixed-point value by integer
     * @param fixed_value Fixed-point value
     * @param divisor Integer divisor (must be non-zero)
     * @return Quotient
     */
    [[nodiscard]] static constexpr int64_t divide_int(int64_t fixed_value, int64_t divisor) noexcept {
        if (divisor == 0) return 0;  // Avoid division by zero
        // Add half divisor for rounding
        int64_t adjustment = divisor / 2;
        if ((fixed_value < 0) != (divisor < 0)) {
            adjustment = -adjustment;  // Opposite sign
        }
        return (fixed_value + adjustment) / divisor;
    }

    /**
     * @brief Divide two fixed-point values
     * @param a Numerator (with digits_a decimal places)
     * @param b Denominator (with digits_b decimal places)
     * @param digits_a Decimal places in a
     * @param digits_b Decimal places in b
     * @param result_digits Desired decimal places in result
     * @return Quotient with result_digits decimal places
     */
    [[nodiscard]] static constexpr int64_t divide(int64_t a, int64_t b,
                                                   int32_t digits_a, int32_t digits_b,
                                                   int32_t result_digits) noexcept {
        if (b == 0) return 0;  // Avoid division by zero

        // a / b with result having result_digits decimal places
        // Need to scale numerator by 10^(result_digits - digits_a + digits_b)
        const int32_t scale_diff = result_digits - digits_a + digits_b;

        int64_t scaled_a = a;
        if (scale_diff > 0) {
            for (int32_t i = 0; i < scale_diff; ++i) {
                scaled_a *= 10;
            }
        } else if (scale_diff < 0) {
            int64_t divisor = 1;
            for (int32_t i = 0; i < -scale_diff; ++i) {
                divisor *= 10;
            }
            scaled_a /= divisor;
        }

        // Add half divisor for rounding
        int64_t adjustment = b / 2;
        if ((scaled_a < 0) != (b < 0)) {
            adjustment = -adjustment;
        }

        return (scaled_a + adjustment) / b;
    }

    /**
     * @brief Get absolute value
     * @param fixed_value Fixed-point value
     * @return Absolute value
     */
    [[nodiscard]] static constexpr int64_t abs(int64_t fixed_value) noexcept {
        return fixed_value >= 0 ? fixed_value : -fixed_value;
    }

    /**
     * @brief Compare two fixed-point values
     * @param a First value
     * @param b Second value
     * @return -1 if a < b, 0 if a == b, 1 if a > b
     */
    [[nodiscard]] static constexpr int compare(int64_t a, int64_t b) noexcept {
        if (a < b) return -1;
        if (a > b) return 1;
        return 0;
    }

    /**
     * @brief Get minimum of two values
     */
    [[nodiscard]] static constexpr int64_t min(int64_t a, int64_t b) noexcept {
        return a < b ? a : b;
    }

    /**
     * @brief Get maximum of two values
     */
    [[nodiscard]] static constexpr int64_t max(int64_t a, int64_t b) noexcept {
        return a > b ? a : b;
    }

    /**
     * @brief Clamp value to range
     * @param value Value to clamp
     * @param min_val Minimum allowed value
     * @param max_val Maximum allowed value
     * @return Clamped value in [min_val, max_val]
     */
    [[nodiscard]] static constexpr int64_t clamp(int64_t value, int64_t min_val, int64_t max_val) noexcept {
        if (value < min_val) return min_val;
        if (value > max_val) return max_val;
        return value;
    }
};

} // namespace hqt
