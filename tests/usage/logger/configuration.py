import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sys
from apps.utils.logger import logger


def development_configuration() -> None:
    print('--- Development Configuration ---')
    logger.remove()
    logger.add(
        sys.stderr,
        level='DEBUG',
        format='{time} | {level} | {file}:{function}:{line} | {message} | {extra}',
    )
    logger.debug('Debug message (dev)', mode='dev')


def production_configuration() -> None:
    print('\n--- Production Configuration ---')
    logger.remove()
    logger.add(sys.stderr, level='WARNING', format='{time} | {level} | {message}')
    logger.add('logs/app_prod.log', level='INFO', format='{time} | {level} | {message}')

    logger.info('Informational message (file)')
    logger.warning('Warning message (console + file)')
    logger.error('Error message (console + file)')


def main() -> None:
    development_configuration()
    production_configuration()


if __name__ == '__main__':
    main()

