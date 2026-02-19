import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sys
from apps.utils.logger import Logger


def main() -> None:
    print('--- Exceptions and Diagnostics ---')
    logger = Logger(name='exceptions-demo')
    logger.add(sys.stderr, level='DEBUG', format='{level} | {message} | {file}:{line}')

    try:
        _ = 1 / 0
    except ZeroDivisionError:
        logger.exception('Division failed')

    try:
        int('not-a-number')
    except ValueError:
        logger.error('Parsing failed', exc_info=True)


if __name__ == '__main__':
    main()

