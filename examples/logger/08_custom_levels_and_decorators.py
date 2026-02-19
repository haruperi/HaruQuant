import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sys
from apps.utils.logger import Logger


def helper(logger: Logger) -> None:
    logger.info('Caller metadata demo')


def main() -> None:
    print('--- Levels and Callsite ---')
    logger = Logger(name='level-demo')
    logger.add(sys.stdout, level='DEBUG', format='{level} | {file}:{function}:{line} | {message}')

    logger.log('INFO', 'Generic log(level, message) call')
    logger.log(30, 'Numeric level call maps to WARNING')
    helper(logger)


if __name__ == '__main__':
    main()

