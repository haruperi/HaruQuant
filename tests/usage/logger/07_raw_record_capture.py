import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.utils.logger import Logger


def main() -> None:
    print('--- Raw Record Capture ---')
    logger = Logger(name='raw-demo')
    captured = []

    handler_id = logger.add(captured.append, level='INFO', raw=True)
    logger.info('Startup event', event='startup', attempt=1)
    logger.warning('Latency elevated', ms=145)

    print(f'Captured records: {len(captured)}')
    if captured:
        rec = captured[-1]
        print(f'Last: {rec.level.name} {rec.file}:{rec.line} {rec.message}')

    logger.remove(handler_id)


if __name__ == '__main__':
    main()

