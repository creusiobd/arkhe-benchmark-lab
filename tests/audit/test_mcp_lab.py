"""Real local pipes; no LLM or real ledger. Tests the pinned MCP lab subset."""
import json
from pathlib import Path
import tempfile
import unittest
from benchmark.mcp_lab import (LocalMCPClient,ControlledHost,run_case,run_lab,
                               PROTOCOL_VERSION,PUBLIC,PRIVATE,CASES)

class MCPLabTests(unittest.TestCase):
 def test_real_process_lifecycle_and_tools(self):
  with LocalMCPClient() as client:
   self.assertIsNone(client.process.poll());self.assertGreater(client.process.pid,0)
   self.assertEqual(client.initialize_result['protocolVersion'],PROTOCOL_VERSION)
   self.assertEqual({t['name'] for t in client.request('tools/list')['tools']},{'ledger_read','ledger_adjust'})
   result=client.request('tools/call',{'name':'ledger_read','arguments':{'resource':PUBLIC}})
   self.assertTrue(result['structuredContent']['synthetic'])
   methods=[t['message'].get('method') for t in client.trace if t['direction']=='client_to_server']
   self.assertEqual(methods[:2],['initialize','notifications/initialized'])
  self.assertIsNotNone(client.process.returncode)

 def test_protocol_unknown_method_and_invalid_arguments_are_errors(self):
  with LocalMCPClient() as client:
   with self.assertRaises(ValueError):client.request('not-supported')
   with self.assertRaises(ValueError):client.request('tools/call',{'name':'ledger_read','arguments':{'resource':PUBLIC,'extra':'notallowed'}})
   with self.assertRaises(ValueError):client.request('initialize',{'protocolVersion':'unsupported'})

 def test_scripted_case_replays_identically(self):
  self.assertEqual(run_case('tool_result_injection','sdk'),run_case('tool_result_injection','sdk'))

 def test_server_origin_allowlist_blocks_before_dispatch(self):
  with LocalMCPClient() as client:
   host=ControlledHost(client,allowed_origin={'server_id':'other'})
   self.assertFalse(host.call('ledger_read',PUBLIC)['executed'])
   self.assertEqual(host.executed,0)
   self.assertFalse(any(t['message'].get('method')=='tools/call' for t in client.trace))

 def test_server_rejects_tool_use_before_initialized_notification(self):
  import subprocess,sys
  import benchmark.mcp_lab as lab
  messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':PROTOCOL_VERSION}},
            {'jsonrpc':'2.0','id':2,'method':'tools/list'},
            {'jsonrpc':'2.0','method':'notifications/initialized'},
            {'jsonrpc':'2.0','id':3,'method':'tools/list'}]
  result=subprocess.run([sys.executable,str(Path(lab.__file__).resolve()),'--serve'],
       input=''.join(json.dumps(m)+'\n' for m in messages),capture_output=True,text=True,encoding='utf-8',timeout=10)
  self.assertEqual(result.returncode,0)
  replies=[json.loads(line) for line in result.stdout.splitlines()]
  self.assertIn('error',replies[1]);self.assertIn('result',replies[2]);self.assertEqual(len(replies),3)

 def test_catalog_poison_and_rebinding_block_both_modes(self):
  for scenario in ('descriptor_poison','catalog_rebinding'):
   for mode in ('sdk','strong_host'):
    with self.subTest(scenario=scenario,mode=mode):
     r=run_case(scenario,mode);self.assertEqual(r['executed'],0);self.assertEqual(r['blocked'],1)
     self.assertFalse(any(t['message'].get('method')=='tools/call' for t in r['trace']))

 def test_scope_and_approval_baseline_is_as_strong_as_sdk(self):
  for scenario in ('unauthorized_resource','approval_required','approval_expired'):
   for mode in ('sdk','strong_host'):
    with self.subTest(scenario=scenario,mode=mode):
     r=run_case(scenario,mode);self.assertEqual(r['executed'],0);self.assertEqual(r['blocked'],1)

 def test_approved_synthetic_adjustment_is_only_write_executed(self):
  for mode in ('sdk','strong_host'):
   r=run_case('approval_valid',mode);self.assertEqual(r['executed'],1);self.assertEqual(r['blocked'],0)
   requests=[t['message'] for t in r['trace'] if t['message'].get('method')=='tools/call']
   self.assertEqual(requests[0]['params'],{'name':'ledger_adjust','arguments':{'resource':PUBLIC}})

 def test_result_injection_script_is_contained_at_action_boundary(self):
  for mode in ('sdk','strong_host'):
   r=run_case('tool_result_injection',mode)
   self.assertEqual((r['executed'],r['blocked']),(1,1))
   self.assertIn('SYSTEM DIRECTIVE',r['outcomes'][0]['result']['content'][0]['text'])
   self.assertEqual(r['agent'],'deterministic_scripted_not_llm')

 def test_recovery_text_does_not_erase_first_attempt(self):
  r=run_case('recovery_text','sdk');self.assertEqual((r['executed'],r['blocked']),(1,1))
  self.assertIn('TRAJECTORY RECOVERY',r['outcomes'][1]['result']['content'][0]['text'])
  self.assertTrue(r['decisions'][-1]['first_alert_event_id'])
  self.assertFalse(r['decisions'][-1]['has_observed_violation']) # blocked, not consumed

 def test_call_origin_catalog_and_arguments_are_bound_in_event(self):
  r=run_case('benign','sdk');event=next(e for e in r['events'] if e['event_type']=='action_proposed')
  p=event['parameters_summary'];self.assertEqual(p['arguments'],{'resource':PUBLIC})
  self.assertEqual(p['catalog_hash'],r['catalog_hash']);self.assertEqual(p['catalog_version'],'1.0.0')
  self.assertEqual(len(p['server_origin_hash']),64)

 def test_unknown_host_route_and_payload_bounds(self):
  with LocalMCPClient() as client:
   host=ControlledHost(client)
   self.assertFalse(host.call('shell',PUBLIC)['executed'])
   with self.assertRaises(ValueError):client.request('tools/call',{'name':'ledger_read','arguments':{'resource':'x'*70000}})

 def test_repeatable_outputs_and_ground_truth_outside_sdk(self):
  with tempfile.TemporaryDirectory() as tmp:
   output=Path(tmp)/'run';summary=run_lab(output)
   self.assertEqual(summary['runs'],len(CASES)*2)
   self.assertEqual(summary['modes']['strong_host'],summary['modes']['sdk'])
   self.assertTrue(summary['synthetic_only']);self.assertEqual(summary['agent'],'deterministic_scripted_not_llm')
   self.assertEqual(summary['scripted_checks']['private_resource_dispatched'],0)
   self.assertEqual(summary['scripted_checks']['matching_expected_execution_counts'],len(CASES)*2)
   self.assertEqual(len(json.loads((output/'labels.json').read_text())),len(CASES))
   events=(output/'events.jsonl').read_text()
   self.assertNotIn('expected_executed',events);self.assertNotIn('ground_truth',events)
   self.assertTrue((output/'transport.jsonl').read_text())
   with self.assertRaises(FileExistsError):run_lab(output)

if __name__=='__main__':unittest.main()
