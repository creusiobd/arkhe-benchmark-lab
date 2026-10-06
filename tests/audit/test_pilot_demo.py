"""Demo verification through real synthetic MCP server plus safe standalone HTML."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from examples.defense.pilot_demo import build_demo,render_html

class PilotDemoTests(unittest.TestCase):
 def test_real_synthetic_demo_has_evidence_and_valid_manifest(self):
  with tempfile.TemporaryDirectory() as directory:
   output=Path(directory)/'demo';summary=build_demo(output)
   self.assertEqual((summary['executed'],summary['blocked'],summary['private_resource_dispatched']),(2,1,0))
   data=json.loads((output/'demo.json').read_text(encoding='utf-8'))
   actions=data['summary']['actions']
   self.assertEqual([a['sdk_status'] for a in actions],['within_policy','within_policy','policy_violation'])
   self.assertEqual([a['executed'] for a in actions],[True,True,False])
   self.assertEqual(actions[-1]['completion'],'blocked');self.assertTrue(actions[-1]['evidence_refs'])
   methods=[t['message'].get('method') for r in data['runs'] for t in r['trace'] if t['direction']=='client_to_server']
   self.assertIn('initialize',methods);self.assertIn('notifications/initialized',methods);self.assertIn('tools/call',methods)
   self.assertNotIn('expected_executed',(output/'events.jsonl').read_text())
   self.assertNotIn('ground_truth',(output/'events.jsonl').read_text())
   self.assertEqual(len(json.loads((output/'labels.json').read_text())),2)
   manifest=json.loads((output/'manifest.json').read_text())
   self.assertTrue(manifest['synthetic_only']);self.assertEqual(manifest['agent'],'deterministic_scripted_not_llm')
   for name,digest in manifest['artifacts'].items():self.assertEqual(hashlib.sha256((output/name).read_bytes()).hexdigest(),digest)
   markup=(output/'index.html').read_text(encoding='utf-8')
   self.assertIn('sem certificação completa',markup);self.assertIn('nenhum modelo interpreta',markup)
   self.assertNotIn('<script',markup);self.assertNotIn('cdn.',markup)
   # Escaping check uses an adversarial display string, without executing it.
   altered=copy.deepcopy(data['runs']);altered[0]['outcomes'][0]['result']['content'][0]['text']='<script>alert("untrusted")</script>'
   escaped=render_html(data['summary'],altered)
   self.assertNotIn('<script>',escaped);self.assertIn('&lt;script&gt;',escaped)

 def test_existing_output_refused_before_starting_server(self):
  with tempfile.TemporaryDirectory() as existing:
   with patch('examples.defense.pilot_demo.run_case',side_effect=AssertionError('server must not start')):
    with self.assertRaises(FileExistsError):build_demo(existing)

if __name__=='__main__':unittest.main()
