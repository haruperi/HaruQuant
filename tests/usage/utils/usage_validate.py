"""
TradeValidator Usage Examples

Purpose:
- Demonstrate comprehensive trading parameter validation
- Show symbol, volume, price, and SL/TP validation
- Illustrate order type and timeframe validation
- Examples for trade request validation and batch validation

Key Concepts:
- TradeValidator for parameter validation
- Symbol and volume validation with MT5 limits
- Price and stop level validation
- Order type and expiration validation
- Trade request validation
- Batch validation for multiple parameters

Usage:
    python tests/usage/utils/usage_validate.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.validate import TradeValidator
from apps.logger import logger


def example_01_symbol_validation():
    """Example 1: Validate trading symbols."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Symbol Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    symbols = ["EURUSD", "GBPUSD", "INVALID_SYMBOL", "USDJPY"]

    logger.info("Validating symbols:\n")

    for symbol in symbols:
        is_valid, message = validator.validate('symbol', symbol)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {symbol}: {status} - {message}")


def example_02_volume_validation():
    """Example 2: Validate trade volumes."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Volume Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    # Test volumes
    volumes = [0.01, 0.1, 1.0, 10.0, 0.001, -0.1, 0]

    logger.info("Validating volumes (without symbol):\n")

    for volume in volumes:
        is_valid, message = validator.validate('volume', volume)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {volume} lots: {status} - {message}")


def example_03_volume_with_symbol():
    """Example 3: Validate volume with symbol-specific limits."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Volume Validation with Symbol Limits")
    logger.info("=" * 70)

    validator = TradeValidator()

    symbol = "EURUSD"
    volumes = [0.01, 0.1, 1.0, 5.0, 10.0]

    logger.info(f"Validating volumes for {symbol}:\n")

    for volume in volumes:
        is_valid, message = validator.validate('volume', volume, symbol=symbol)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {volume} lots: {status}")
        if not is_valid:
            logger.info(f"    Reason: {message}")


def example_04_price_validation():
    """Example 4: Validate price values."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Price Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    prices = [1.1000, 0.0, -1.0, 150.50, 1.10001]

    logger.info("Validating prices:\n")

    for price in prices:
        is_valid, message = validator.validate('price', price)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {price}: {status} - {message}")


def example_05_stop_loss_validation():
    """Example 5: Validate stop loss levels."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Stop Loss Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    # BUY order: SL should be below entry
    entry_price = 1.1000
    order_type = "BUY"
    symbol = "EURUSD"

    stop_losses = [0, 1.0950, 1.0990, 1.1050]  # 0=no SL, too far, ok, invalid (above entry)

    logger.info(f"Validating SL for {order_type} at {entry_price}:\n")

    for sl in stop_losses:
        is_valid, message = validator.validate(
            'stop_loss',
            sl,
            entry_price=entry_price,
            order_type=order_type,
            symbol=symbol
        )
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  SL {sl}: {status} - {message}")


def example_06_take_profit_validation():
    """Example 6: Validate take profit levels."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Take Profit Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    # SELL order: TP should be below entry
    entry_price = 1.1000
    order_type = "SELL"
    symbol = "EURUSD"

    take_profits = [0, 1.0950, 1.0990, 1.1050]  # 0=no TP, ok, ok, invalid (above entry)

    logger.info(f"Validating TP for {order_type} at {entry_price}:\n")

    for tp in take_profits:
        is_valid, message = validator.validate(
            'take_profit',
            tp,
            entry_price=entry_price,
            order_type=order_type,
            symbol=symbol
        )
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  TP {tp}: {status} - {message}")


def example_07_order_type_validation():
    """Example 7: Validate order types."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: Order Type Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    order_types = ["BUY", "SELL", "BUY_LIMIT", "SELL_STOP", "INVALID", 0, 1]

    logger.info("Validating order types:\n")

    for order_type in order_types:
        is_valid, message = validator.validate('order_type', order_type)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {order_type}: {status} - {message}")


def example_08_timeframe_validation():
    """Example 8: Validate timeframes."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Timeframe Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    timeframes = ["M1", "M5", "H1", "H4", "D1", "W1", "INVALID", "M2"]

    logger.info("Validating timeframes:\n")

    for tf in timeframes:
        is_valid, message = validator.validate('timeframe', tf)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {tf}: {status} - {message}")


def example_09_date_range_validation():
    """Example 9: Validate date ranges."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Date Range Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    now = datetime.now()

    test_cases = [
        (now - timedelta(days=30), now - timedelta(days=1), "Valid 30-day range"),
        (now - timedelta(days=365), now, "Valid 1-year range"),
        (now + timedelta(days=1), now + timedelta(days=30), "Invalid future range"),
        (now - timedelta(days=4000), now, "Invalid too far in past"),
    ]

    logger.info("Validating date ranges:\n")

    for start, end, description in test_cases:
        is_valid, message = validator.validate('date_range', start, end_date=end)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {description}: {status}")
        if not is_valid:
            logger.info(f"    Reason: {message}")


def example_10_trade_request_validation():
    """Example 10: Validate complete trade request."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Trade Request Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    # Valid trade request
    valid_request = {
        'action': 1,  # Trade
        'symbol': 'EURUSD',
        'volume': 0.1,
        'type': 0,  # BUY
        'price': 1.1000,
        'sl': 1.0950,
        'tp': 1.1050,
        'deviation': 20,
        'magic': 12345,
    }

    logger.info("Validating trade request:\n")

    is_valid, message = validator.validate('trade_request', valid_request)

    logger.info(f"Valid request: {is_valid}")
    logger.info(f"Message: {message}")

    # Invalid trade request (missing required fields)
    invalid_request = {
        'symbol': 'EURUSD',
        'volume': 0.1,
        # Missing 'action' and 'type'
    }

    logger.info("\nValidating invalid request (missing fields):\n")

    is_valid, message = validator.validate('trade_request', invalid_request)

    logger.info(f"Valid request: {is_valid}")
    logger.info(f"Message: {message}")


def example_11_batch_validation():
    """Example 11: Batch validation of multiple parameters."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 11: Batch Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    # Multiple validations in one call
    validations = [
        {'type': 'symbol', 'value': 'EURUSD'},
        {'type': 'volume', 'value': 0.1, 'symbol': 'EURUSD'},
        {'type': 'price', 'value': 1.1000, 'symbol': 'EURUSD'},
        {'type': 'order_type', 'value': 'BUY'},
        {'type': 'timeframe', 'value': 'H1'},
    ]

    logger.info("Running batch validation:\n")

    all_valid, errors = validator.validate_multiple(validations)

    logger.info(f"All valid: {all_valid}")

    if errors:
        logger.info("\nErrors found:")
        for error in errors:
            logger.info(f"  - {error}")
    else:
        logger.info("No errors found - all validations passed!")


def example_12_magic_number_validation():
    """Example 12: Validate magic numbers."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 12: Magic Number Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    magic_numbers = [0, 12345, 999999, 2147483647, -1, 2147483648]

    logger.info("Validating magic numbers:\n")

    for magic in magic_numbers:
        is_valid, message = validator.validate('magic', magic)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {magic}: {status} - {message}")


def example_13_deviation_validation():
    """Example 13: Validate price deviation."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 13: Price Deviation Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    deviations = [0, 10, 20, 50, 100, -5, 150]

    logger.info("Validating price deviations (in points):\n")

    for deviation in deviations:
        is_valid, message = validator.validate('deviation', deviation)
        status = "VALID" if is_valid else "INVALID"
        logger.info(f"  {deviation} points: {status} - {message}")


def example_14_credentials_validation():
    """Example 14: Validate MT5 credentials."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 14: MT5 Credentials Validation")
    logger.info("=" * 70)

    validator = TradeValidator()

    # Valid credentials
    valid_creds = {
        'login': 12345678,
        'password': 'SecurePassword123',
        'server': 'BrokerServer-Live'
    }

    logger.info("Validating credentials:\n")

    is_valid, message = validator.validate('credentials', valid_creds)
    logger.info(f"Valid credentials: {is_valid} - {message}")

    # Invalid credentials (missing fields)
    invalid_creds = {
        'login': 12345678,
        # Missing password and server
    }

    is_valid, message = validator.validate('credentials', invalid_creds)
    logger.info(f"\nInvalid credentials: {is_valid} - {message}")


def example_15_validation_rules():
    """Example 15: View and update validation rules."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 15: Validation Rules Management")
    logger.info("=" * 70)

    validator = TradeValidator()

    # Get current rules
    rules = validator.get_validation_rules()

    logger.info("Current validation rules:\n")

    for rule_type, rule_values in rules.items():
        logger.info(f"{rule_type}:")
        for key, value in rule_values.items():
            logger.info(f"  {key}: {value}")

    # Update a rule
    logger.info("\nUpdating volume minimum to 0.001...")
    validator.update_validation_rule('volume', 'min', 0.001)

    updated_rules = validator.get_validation_rules()
    logger.info(f"New volume minimum: {updated_rules['volume']['min']}")


def main():
    """Run all trade validator examples."""
    logger.info("\n" + "=" * 80)
    logger.info("TRADE VALIDATOR - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_symbol_validation()
    example_02_volume_validation()
    example_03_volume_with_symbol()
    example_04_price_validation()
    example_05_stop_loss_validation()
    example_06_take_profit_validation()
    example_07_order_type_validation()
    example_08_timeframe_validation()
    example_09_date_range_validation()
    example_10_trade_request_validation()
    example_11_batch_validation()
    example_12_magic_number_validation()
    example_13_deviation_validation()
    example_14_credentials_validation()
    example_15_validation_rules()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)

    logger.info("\nKEY TAKEAWAYS:")
    logger.info("1. TradeValidator provides comprehensive parameter validation")
    logger.info("2. Use validate() method with validation type and value")
    logger.info("3. Symbol validation checks MT5 symbol availability")
    logger.info("4. Volume validation enforces symbol-specific limits")
    logger.info("5. SL/TP validation checks price relationships and minimum distances")
    logger.info("6. validate_multiple() for batch validation")
    logger.info("7. Validation prevents invalid trades before sending to MT5")
    logger.info("8. Always validate parameters before executing trades")

    logger.info("\nVALIDATION TYPES:")
    logger.info("  - symbol: Trading symbol validation")
    logger.info("  - volume: Trade volume validation")
    logger.info("  - price: Price value validation")
    logger.info("  - stop_loss: SL level validation")
    logger.info("  - take_profit: TP level validation")
    logger.info("  - order_type: Order type validation")
    logger.info("  - magic: Magic number validation")
    logger.info("  - deviation: Price deviation validation")
    logger.info("  - timeframe: Timeframe validation")
    logger.info("  - date_range: Date range validation")
    logger.info("  - trade_request: Complete request validation")
    logger.info("  - credentials: MT5 credentials validation")


if __name__ == "__main__":
    main()
