"""Run three synthetic journeys with the same engine and no infrastructure access."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from arkhe_trajectory import JourneyConfig, JourneyEngine, TrajectoryEvent


def demonstrate(config_path, output_dir=None):
    config = JourneyConfig.from_dict(json.loads(config_path.read_text(encoding='utf-8-sig')))
    start = datetime.now(timezone.utc) - timedelta(seconds=80)
    clock = [start]
    engine = JourneyEngine(config, clock=lambda: clock[0])
    events, assessments = [], []
    monitor_step = config.steps[-1].step_id
    # Upstream aggregated metrics. Each event is one window, not one card transaction.
    for index in range(7):
        clock[0] = start + timedelta(seconds=index * 10)
        values = dict(config.baseline)
        if config.journey_id == 'card-authorization':
            values.update(p95_latency_ms=300 + index * 90, queue_lag=10 + index * 10,
                retry_rate=0.01 + index * 0.006)
        elif config.journey_id == 'request-serving':
            values.update(p95_latency_ms=100 + index * 25, queue_depth=5 + index * 5)
        else:
            values.update(pending_orders=10 + index * 5)
        event = TrajectoryEvent(tenant_id=config.tenant_id, journey_id=config.journey_id,
            journey_version=config.version, trajectory_id='aggregate:primary', event_id=f'window-{index}',
            step_id=monitor_step, event_time=clock[0], ingested_at=clock[0], metrics=values,
            dimensions={'environment':'synthetic','partition':'primary'})
        events.append(event.to_dict())
        assessment = engine.ingest(event)
        assessments.append(assessment.to_dict())
        print(json.dumps({'journey':config.journey_id,'sample':index,'status':assessment.status,
            'rules':[f.rule_id for f in assessment.findings], 'trends':dict(assessment.trends)},ensure_ascii=True))
    # A separate individual journey with no response demonstrates an explicit deadline check.
    first_step = config.steps[0]
    clock[0] += timedelta(seconds=1)
    unfinished = TrajectoryEvent(tenant_id=config.tenant_id, journey_id=config.journey_id,
        journey_version=config.version, trajectory_id='instance:unfinished', event_id='started',
        step_id=first_step.step_id, event_time=clock[0], ingested_at=clock[0], metrics={})
    engine.ingest(unfinished)
    clock[0] += timedelta(seconds=first_step.max_delay_seconds + config.max_lateness_seconds + 1)
    overdue = engine.check(config.tenant_id, unfinished.trajectory_id, as_of=clock[0])
    print(json.dumps({'journey':config.journey_id,'missing_steps':overdue.missing_expected_steps,
        'status':overdue.status},ensure_ascii=True))
    if output_dir is not None:
        output_dir.mkdir(parents=True,exist_ok=True)
        stem=config_path.stem
        (output_dir/(stem+'-events.jsonl')).write_text(''.join(json.dumps(e,ensure_ascii=True)+'\n' for e in events),encoding='utf8')
        (output_dir/(stem+'-assessments.jsonl')).write_text(''.join(json.dumps(a,ensure_ascii=True)+'\n' for a in assessments),encoding='utf8')
    return assessments


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    paths=[args.config] if args.config else [Path('configs/journeys')/(name+'.json') for name in ('cards','infrastructure','fulfillment')]
    for path in paths:
        demonstrate(path,args.output_dir)

if __name__=='__main__':main()
