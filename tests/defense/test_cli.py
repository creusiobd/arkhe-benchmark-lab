import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from arkhe_defense.cli import main

class CLITests(unittest.TestCase):
    def invoke(self,args):
        output,error=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(error):
            result=main(args)
        return result,output.getvalue(),error.getvalue()
    def test_doctor_local(self):
        code,out,err=self.invoke(['doctor'])
        self.assertEqual(code,0)
        self.assertFalse(json.loads(out)['network_required'])
    def test_invalid_config_does_not_echo_value(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'config.json'
            path.write_text(json.dumps({'secret':'do-not-echo'}),encoding='utf8')
            code,out,err=self.invoke(['validate-config',str(path)])
            self.assertEqual(code,2)
            self.assertNotIn('do-not-echo',err)
    def test_empty_trusted_context_registry_rejects_event(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'contexts.json').write_text('[]')
            (root/'policy.json').write_text(json.dumps({'tenant_id':'t','policy_id':'p','version':'v1','mission':'Read','rules':[]}))
            event={'event_type':'action_proposed','event_id':'e','tenant_id':'t','trajectory_id':'r','agent_id':'a','producer_id':'a','occurred_at':'2026-01-01T00:00:00Z','ingested_at':'2026-01-01T00:00:00Z','action_id':'x','tool_name':'read','action_type':'read','target_resource':'/data','policy_version':'v1'}
            (root/'events.jsonl').write_text(json.dumps(event))
            code,out,err=self.invoke(['replay',str(root/'events.jsonl'),'--contexts',str(root/'contexts.json'),'--policy',str(root/'policy.json')])
            self.assertEqual(code,2)
            self.assertEqual(out,'')

if __name__=='__main__': unittest.main()
