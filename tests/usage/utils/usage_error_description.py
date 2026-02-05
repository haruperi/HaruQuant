"""
Error Description Usage Examples

Purpose:
- Demonstrate MT5 error code lookup and descriptions
- Show error handling in trading operations
- Illustrate common MT5 error scenarios
- Examples for debugging trading issues

Key Concepts:
- TradeErrorDescriptions for error lookup
- MT5 error code categories
- Error handling best practices
- Common trading errors and solutions

Usage:
    python tests/usage/utils/usage_error_description.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.error_description import TradeErrorDescriptions
from apps.logger import logger


def example_01_basic_error_lookup():
    """Example 1: Basic error code lookup."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Basic Error Code Lookup")
    logger.info("=" * 70)

    # Common error codes
    error_codes = [0, 10004, 10006, 10013, 10014, 10015, 10019]

    logger.info("Looking up common MT5 error codes:\n")

    for code in error_codes:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Error {code}: {description}")


def example_02_success_codes():
    """Example 2: Success and completion codes."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Success and Completion Codes")
    logger.info("=" * 70)

    success_codes = [
        0,      # Operation completed successfully
        10008,  # Order placed
        10009,  # Request completed
    ]

    logger.info("Success codes:\n")

    for code in success_codes:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Code {code}: {description}")


def example_03_rejection_errors():
    """Example 3: Order rejection errors."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Order Rejection Errors")
    logger.info("=" * 70)

    rejection_codes = [
        10006,  # Request rejected
        10007,  # Request canceled by trader
        10013,  # Invalid request
        10017,  # Trade is disabled
        10018,  # Market is closed
    ]

    logger.info("Common rejection errors:\n")

    for code in rejection_codes:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Error {code}: {description}")


def example_04_parameter_errors():
    """Example 4: Invalid parameter errors."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Invalid Parameter Errors")
    logger.info("=" * 70)

    parameter_errors = [
        10014,  # Invalid volume
        10015,  # Invalid price
        10016,  # Invalid stops
        10022,  # Invalid expiration
        10030,  # Invalid order filling type
    ]

    logger.info("Parameter validation errors:\n")

    for code in parameter_errors:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Error {code}: {description}")


def example_05_market_conditions():
    """Example 5: Market condition errors."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Market Condition Errors")
    logger.info("=" * 70)

    market_errors = [
        10004,  # Requote
        10018,  # Market is closed
        10020,  # Prices changed
        10021,  # There are no quotes to process the request
        10024,  # Too frequent requests
    ]

    logger.info("Market condition errors:\n")

    for code in market_errors:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Error {code}: {description}")


def example_06_account_errors():
    """Example 6: Account and margin errors."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Account and Margin Errors")
    logger.info("=" * 70)

    account_errors = [
        10019,  # There is not enough money to complete the request
        10026,  # Autotrading disabled by server
        10027,  # Autotrading disabled by client
        10031,  # No connection with the trade server
    ]

    logger.info("Account-related errors:\n")

    for code in account_errors:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Error {code}: {description}")


def example_07_position_errors():
    """Example 7: Position and order errors."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: Position and Order Errors")
    logger.info("=" * 70)

    position_errors = [
        4704,   # Position not found
        4705,   # Order not found
        4706,   # Deal not found
        10029,  # Order or position frozen
        10035,  # Position closed
    ]

    logger.info("Position/order management errors:\n")

    for code in position_errors:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Error {code}: {description}")


def example_08_runtime_errors():
    """Example 8: Runtime and system errors."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Runtime and System Errors")
    logger.info("=" * 70)

    runtime_errors = [
        1,   # Unexpected internal error
        2,   # Wrong parameter in the inner call
        4,   # Not enough memory to perform the system function
        10,  # Invalid date and/or time
    ]

    logger.info("Runtime/system errors:\n")

    for code in runtime_errors:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Error {code}: {description}")


def example_09_chart_errors():
    """Example 9: Chart and indicator errors."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Chart and Indicator Errors")
    logger.info("=" * 70)

    chart_errors = [
        4001,  # Wrong chart ID
        4003,  # Chart not found
        4013,  # Error adding an indicator to chart
        4015,  # Indicator not found on the specified chart
        4301,  # Unknown symbol
    ]

    logger.info("Chart/indicator errors:\n")

    for code in chart_errors:
        description = TradeErrorDescriptions.error_description(code)
        logger.info(f"Error {code}: {description}")


def example_10_error_handling_pattern():
    """Example 10: Error handling pattern in trading code."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Error Handling Pattern")
    logger.info("=" * 70)

    def simulate_trade_operation(result_code):
        """Simulate a trading operation that returns an error code."""
        return result_code

    # Simulate different scenarios
    scenarios = [
        (0, "Successful trade"),
        (10004, "Requote received"),
        (10014, "Invalid volume"),
        (10019, "Insufficient margin"),
        (10018, "Market closed"),
    ]

    logger.info("Error handling pattern:\n")

    for code, scenario in scenarios:
        logger.info(f"\nScenario: {scenario}")

        result = simulate_trade_operation(code)

        if result == 0:
            logger.info("  Status: SUCCESS")
        else:
            error_msg = TradeErrorDescriptions.error_description(result)
            logger.info(f"  Status: FAILED")
            logger.info(f"  Error Code: {result}")
            logger.info(f"  Description: {error_msg}")

            # Suggest actions based on error
            if result == 10004:
                logger.info("  Action: Retry with updated price")
            elif result == 10014:
                logger.info("  Action: Adjust volume to meet requirements")
            elif result == 10019:
                logger.info("  Action: Reduce position size or add funds")
            elif result == 10018:
                logger.info("  Action: Wait for market to open")


def main():
    """Run all error description examples."""
    logger.info("\n" + "=" * 80)
    logger.info("ERROR DESCRIPTION - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_basic_error_lookup()
    example_02_success_codes()
    example_03_rejection_errors()
    example_04_parameter_errors()
    example_05_market_conditions()
    example_06_account_errors()
    example_07_position_errors()
    example_08_runtime_errors()
    example_09_chart_errors()
    example_10_error_handling_pattern()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)

    logger.info("\nKEY TAKEAWAYS:")
    logger.info("1. Use TradeErrorDescriptions.error_description() for error lookup")
    logger.info("2. Error code 0 means success")
    logger.info("3. 10xxx codes are trade-related errors")
    logger.info("4. 4xxx codes are runtime/system errors")
    logger.info("5. Always check return codes from MT5 operations")
    logger.info("6. Log error descriptions for debugging")
    logger.info("7. Implement retry logic for recoverable errors (requote, prices changed)")

    logger.info("\nCOMMON ERROR SOLUTIONS:")
    logger.info("  10004 (Requote) -> Retry with updated price")
    logger.info("  10014 (Invalid volume) -> Check symbol min/max/step volume")
    logger.info("  10015 (Invalid price) -> Verify price within allowed range")
    logger.info("  10016 (Invalid stops) -> Check SL/TP distance from current price")
    logger.info("  10018 (Market closed) -> Wait for trading session")
    logger.info("  10019 (Insufficient margin) -> Reduce position size")
    logger.info("  10031 (No connection) -> Check MT5 connection status")


if __name__ == "__main__":
    main()
