import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sys
from apps.utils.logger import Logger


def main() -> None:
    print('--- Context Binding ---')
    logger = Logger(name='context-demo')
    logger.add(sys.stdout, level='INFO', format='{level} | {message} | {extra}')

    user_logger = logger.bind(user='alice')
    user_logger.info('User session started')

    with logger.contextualize(request_id='req-100') as ctx:
        ctx.info('Request processing')

    user_logger.info('Session complete')


if __name__ == '__main__':
    main()

