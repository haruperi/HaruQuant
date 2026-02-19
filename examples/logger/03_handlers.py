import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sys
from apps.utils.logger import logger


def main() -> None:
    print('--- Handlers ---')
    logger.remove()

    logger.add(sys.stderr, level='INFO', format='{level} | {message}')
    file_handler = logger.add('logs/app_usage.log', level='DEBUG', format='{time} | {level} | {message}')

    captured = []
    cb_handler = logger.add(captured.append, level='ERROR', raw=True)

    logger.info('Console and file log')
    logger.debug('File-only log example')
    logger.error('Callback captured error', service='usage')

    print(f'Captured callback records: {len(captured)}')

    logger.remove(cb_handler)
    logger.remove(file_handler)


if __name__ == '__main__':
    main()

