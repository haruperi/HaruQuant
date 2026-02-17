import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sys
from apps.utils.logger import logger


def main() -> None:
    print('--- Formatting ---')
    logger.remove()

    logger.add(sys.stderr, level='INFO', format='{time} | {level} | {message}')
    logger.info('Simple format output')

    logger.remove()
    logger.add(
        sys.stderr,
        level='INFO',
        format='{time} | {level} | {file}:{function}:{line} | {message} | {extra}',
    )
    logger.info('Detailed format output', component='format-demo')


if __name__ == '__main__':
    main()

