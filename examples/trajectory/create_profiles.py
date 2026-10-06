import json
from pathlib import Path
from arkhe_trajectory import JourneyConfig
root=Path('configs/journeys')
profiles=[
 dict(tenant_id='example-bank',journey_id='card-authorization',version='1',window_seconds=300,
  steps=[{'step_id':'receipt','expected_next':['validation'],'max_delay_seconds':1},
         {'step_id':'validation','expected_next':['fraud_check'],'max_delay_seconds':1},
         {'step_id':'fraud_check','expected_next':['limit_lookup'],'max_delay_seconds':1},
         {'step_id':'limit_lookup','expected_next':['authorization'],'max_delay_seconds':2},
         {'step_id':'authorization','expected_next':['response'],'max_delay_seconds':1},
         {'step_id':'response'},{'step_id':'channel_window'}],
  baseline={'p95_latency_ms':300,'timeout_rate':0.005,'retry_rate':0.01,'queue_lag':10,'technical_decline_rate':0.005},
  rules=[{'rule_id':'latency-slo','metric':'p95_latency_ms','operator':'gt','threshold':1500,'step_id':'channel_window','severity':'critical'},
         {'rule_id':'latency-drift','metric':'p95_latency_ms','operator':'gt','threshold':1,'reference':'relative','step_id':'channel_window','persistence':2},
         {'rule_id':'queue-rising','metric':'queue_lag','operator':'gt','threshold':0.5,'aggregation':'slope','min_samples':3,'persistence':2,'step_id':'channel_window'},
         {'rule_id':'retry-budget','metric':'retry_rate','operator':'gt','threshold':0.03,'aggregation':'mean','min_samples':3,'step_id':'channel_window'},
         {'rule_id':'timeouts','metric':'timeout_rate','operator':'gt','threshold':0.03,'step_id':'channel_window','severity':'critical'},
         {'rule_id':'technical-declines','metric':'technical_decline_rate','operator':'gt','threshold':0.02,'step_id':'channel_window'}]),
 dict(tenant_id='example-platform',journey_id='request-serving',version='1',window_seconds=300,
  steps=[{'step_id':'received','expected_next':['processed'],'max_delay_seconds':5},
         {'step_id':'processed','expected_next':['responded'],'max_delay_seconds':5},
         {'step_id':'responded'},{'step_id':'service_window'}],
  baseline={'p95_latency_ms':100,'error_rate':0.001,'queue_depth':5},
  rules=[{'rule_id':'latency','metric':'p95_latency_ms','operator':'gt','threshold':500,'step_id':'service_window'},
         {'rule_id':'errors','metric':'error_rate','operator':'gt','threshold':0.02,'step_id':'service_window','severity':'critical'},
         {'rule_id':'queue-rising','metric':'queue_depth','operator':'gt','threshold':0.25,'aggregation':'slope','min_samples':3,'step_id':'service_window'}]),
 dict(tenant_id='example-commerce',journey_id='order-fulfillment',version='1',window_seconds=3600,
  steps=[{'step_id':'accepted','expected_next':['packed'],'max_delay_seconds':1800},
         {'step_id':'packed','expected_next':['shipped'],'max_delay_seconds':3600},
         {'step_id':'shipped'},{'step_id':'operations_window'}],
  baseline={'pending_orders':10,'failure_rate':0.001},
  rules=[{'rule_id':'backlog','metric':'pending_orders','operator':'gt','threshold':30,'aggregation':'mean','min_samples':3,'step_id':'operations_window'},
         {'rule_id':'backlog-rising','metric':'pending_orders','operator':'gt','threshold':0.05,'aggregation':'slope','min_samples':3,'step_id':'operations_window'},
         {'rule_id':'failures','metric':'failure_rate','operator':'gt','threshold':0.01,'step_id':'operations_window'}])]
for profile,name in zip(profiles,['cards','infrastructure','fulfillment']):
 profile.update(ttl_seconds=7200,max_events=500,max_trajectories=1000,max_lateness_seconds=5)
 config=JourneyConfig.from_dict(profile)
 (root/(name+'.json')).write_text(json.dumps(config.to_dict(),indent=2),encoding='utf8')
 print(name,config.configuration_hash)
