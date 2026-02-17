import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.utils.logger import logger


def main() -> None:
    print('--- Basic Usage ---')
    logger.info('Application started')
    logger.success('Operation completed successfully')
    logger.warning('Low disk space')
    logger.error('Failed to connect to database')

    print('\n--- Message Formatting ---')
    logger.info('User {} logged in', 'john_doe')
    logger.info('Order {order_id} filled for {symbol}', order_id=123, symbol='EURUSD')

    print('\n--- Structured Fields ---')
    logger.info('Trade executed', symbol='EURUSD', side='BUY', volume=1.0)
    logger.error('Order failed', order_id=124, reason='Insufficient margin')


if __name__ == '__main__':
    main()

