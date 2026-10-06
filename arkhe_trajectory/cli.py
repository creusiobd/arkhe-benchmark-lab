"""Local JSON configuration, validation and replay. No infrastructure connection."""
import argparse
from importlib import metadata, resources
import json
from pathlib import Path
import sys
from .config import JourneyConfig
from .contracts import TrajectoryEvent, timestamp
from .engine import JourneyEngine
from .errors import TrajectoryError


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main(argv=None):
    parser = argparse.ArgumentParser(prog='arkhe-trajectory')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor')
    initialize = commands.add_parser('init')
    initialize.add_argument('--preset', choices=('cards','infrastructure','fulfillment'), required=True)
    initialize.add_argument('--tenant', required=True)
    initialize.add_argument('--version', default='1')
    initialize.add_argument('--output', required=True)
    validate = commands.add_parser('validate-config')
    validate.add_argument('config')
    replay = commands.add_parser('replay')
    replay.add_argument('events')
    replay.add_argument('--config', required=True)
    replay.add_argument('--output')
    replay.add_argument('--check-at', help='optional historical deadline check after replay (ISO UTC)')
    args = parser.parse_args(argv)
    output = None
    try:
        if args.command == 'doctor':
            try:
                version = metadata.version('arkhe-trajectory-sdk')
            except metadata.PackageNotFoundError:
                version = 'source-checkout'
            print(json.dumps({'sdk': version, 'mode': 'observe', 'network_required': False,
                'runtime_dependencies': [], 'persistence': 'process_memory'}, ensure_ascii=True))
            return 0
        if args.command == 'init':
            template = resources.files('arkhe_trajectory').joinpath('presets', args.preset + '.json')
            values = json.loads(template.read_text(encoding='utf-8'))
            values.update(tenant_id=args.tenant, version=args.version)
            config = JourneyConfig.from_dict(values)
            with Path(args.output).open('x', encoding='utf-8') as file:
                json.dump(config.to_dict(), file, indent=2, ensure_ascii=True)
            print(json.dumps({'created': args.output, 'configuration_hash': config.configuration_hash, 'calibration': 'illustrative; requires local validation'}, ensure_ascii=True))
            return 0
        config = JourneyConfig.from_dict(read_json(args.config))
        if args.command == 'validate-config':
            print(json.dumps({'valid': True, 'tenant_id': config.tenant_id, 'journey_id': config.journey_id,
                'version': config.version, 'configuration_hash': config.configuration_hash}, ensure_ascii=True))
            return 0
        # The process/operator selects the trusted tenant config. Payload cannot change it.
        # Replay is an explicit historical simulation, with receipt times as its clock.
        virtual_clock = [None]
        engine = JourneyEngine(config, clock=lambda: virtual_clock[0])
        source = Path(args.events).resolve()
        if args.output:
            target = Path(args.output).resolve()
            if target in (source, Path(args.config).resolve()):
                raise TrajectoryError('output: cannot overwrite events or configuration')
            # Existing exports are preserved. Replay output is created exclusively.
            output = target.open('x', encoding='utf-8')
        trajectories, count = set(), 0
        def emit(assessment):
            line = json.dumps(assessment.to_dict(), ensure_ascii=True, allow_nan=False)
            print(line)
            if output:
                output.write(line + '\n')
        with source.open(encoding='utf-8-sig') as events:
            # Bounded read: oversize JSONL records cannot allocate unbounded payloads.
            line_number = 0
            while True:
                line = events.readline(config.max_payload_bytes + 1)
                if not line:
                    break
                line_number += 1
                if len(line.encode('utf-8')) > config.max_payload_bytes:
                    raise TrajectoryError(f'events line {line_number}: payload limit exceeded')
                if not line.strip():
                    continue
                event = TrajectoryEvent.from_dict(json.loads(line))
                virtual_clock[0] = max(virtual_clock[0], event.ingested_at) if virtual_clock[0] is not None else event.ingested_at
                emit(engine.ingest(event))
                trajectories.add(event.trajectory_id)
                if len(trajectories) > config.max_trajectories:
                    raise TrajectoryError('replay: trajectory registry capacity exceeded')
                count += 1
        if args.check_at:
            at = timestamp(args.check_at, 'check_at')
            if virtual_clock[0] is not None:
                virtual_clock[0] = max(virtual_clock[0], at)
            for trajectory in sorted(trajectories):
                emit(engine.check(config.tenant_id, trajectory, as_of=at))
        print(json.dumps({'events': count, 'mode': 'observe', 'state': engine.state.stats()}), file=sys.stderr)
        return 0
    except (TrajectoryError, OSError, ValueError) as error:
        # Never print JSON parse excerpts or financial payloads.
        reason = 'invalid_json' if isinstance(error, json.JSONDecodeError) else type(error).__name__
        message = 'Invalid JSON document' if reason == 'invalid_json' else str(error)
        print(json.dumps({'error': reason, 'message': message}, ensure_ascii=True), file=sys.stderr)
        return 2
    finally:
        if output:
            output.close()


if __name__ == '__main__':
    raise SystemExit(main())
