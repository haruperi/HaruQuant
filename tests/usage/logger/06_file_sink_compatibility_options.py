import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.utils.logger import Logger


def main() -> None:
    print('--- File Sink Compatibility Options ---')
    logger = Logger(name='file-demo')

    # These options are accepted for compatibility with previous logger usage.
    # The current adapter writes to file, but does not implement full rotation/retention/compression logic.
    handler_id = logger.add(
        'logs/logger_file_sink.log',
        level='INFO',
        format='{time} | {level} | {message}',
        rotation='1 KB',
        retention=3,
        compression='gz',
    )

    for i in range(20):
        logger.info('File message {i}', i=i)

    logger.remove(handler_id)


if __name__ == '__main__':
    main()

