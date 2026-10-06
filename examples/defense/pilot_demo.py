"""Short repeatable demo: controlled MCP STDIO, scripted agent, synthetic data.

Run from checkout: python -m examples.defense.pilot_demo --output-dir results/pilot-demo
No LLM, external infrastructure, real ledger or model credentials are used.
"""
from __future__ import annotations
import argparse
import hashlib
import html
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from benchmark.mcp_lab import run_case, PROTOCOL_VERSION, PRIVATE

ROOT=Path(__file__).resolve().parents[2]
SCENARIOS=('benign','tool_result_injection')

def sha_bytes(value):return hashlib.sha256(value).hexdigest()
def encode(value):return json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)

def summarize(runs):
 actions=[]
 for run in runs:
  proposals=[e for e in run['events'] if e['event_type']=='action_proposed']
  decisions={d['event_id']:d for d in run['decisions']}
  completions={e['action_id']:e for e in run['events'] if e['event_type']=='action_completed'}
  for proposal,outcome in zip(proposals,run['outcomes']):
   decision=decisions[proposal['event_id']]
   completion=completions.get(proposal['action_id'])
   actions.append({'scenario':run['scenario'],'event_id':proposal['event_id'],
    'tool':proposal['tool_name'],'operation':proposal['action_type'],'resource':proposal['target_resource'],
    'sdk_status':decision['status'],'host_allowed':outcome['allowed'],'executed':outcome['executed'],
    'completion':completion['status'] if completion else None,'rule_ids':decision['rule_ids'],
    'evidence_refs':decision['evidence_refs'],'policy_version':decision['policy_version'],
    'policy_hash':decision['policy_hash'],'catalog_hash':run['catalog_hash']})
 private_calls=sum(item['message'].get('params',{}).get('arguments',{}).get('resource')==PRIVATE
  for run in runs for item in run['trace'] if item['message'].get('method')=='tools/call')
 return {'agent':'deterministic_scripted_not_llm','synthetic_only':True,
  'transport':'real_subprocess_stdio','protocol_version':PROTOCOL_VERSION,
  'executed':sum(r['executed'] for r in runs),'blocked':sum(r['blocked'] for r in runs),
  'private_resource_dispatched':private_calls,'actions':actions}

def render_html(summary,runs):
 esc=lambda value:html.escape(str(value),quote=True)
 rows=[]
 for action in summary['actions']:
  state='Permitida' if action['executed'] else 'Bloqueada pelo hospedeiro'
  rows.append('<tr><td>'+esc(action['scenario'])+'</td><td><strong>'+esc(action['operation'])+'</strong><br><code>'+esc(action['resource'])+'</code></td><td><code>'+esc(action['sdk_status'])+'</code></td><td>'+state+'</td><td><code>'+esc(action['event_id'])+'</code><br>Política '+esc(action['policy_version'])+'<br>Regra: '+esc(', '.join(action['rule_ids']) or 'nenhuma correspondente')+'</td></tr>')
 excerpts=[]
 for run in runs:
  for outcome in run['outcomes']:
   if outcome.get('result'):
    text=outcome['result']['content'][0]['text']
    excerpts.append('<blockquote>'+esc(text)+'</blockquote>')
 details=[]
 for run in runs:
  details.append('<details><summary>Rastro completo: '+esc(run['scenario'])+'</summary><pre>'+esc(encode(run))+'</pre></details>')
 return '''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARKHÉ — demonstração defensiva controlada</title>
<style>body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f4f6fa;color:#142339}main{max-width:1050px;margin:auto;padding:40px 24px}h1{font-size:32px;line-height:1.2}h2{font-size:22px;margin-top:32px}.tag{display:inline-block;padding:5px 10px;background:#dce7ef;border-radius:5px;font-size:13px}.notice{background:#fff4d6;padding:18px;border-left:4px solid #b67c14}.cards{display:flex;gap:16px;flex-wrap:wrap;margin:24px 0}.card{padding:18px;background:white;border-radius:8px;min-width:180px}.card strong{display:block;font-size:32px}.scroll{overflow:auto}table{border-collapse:collapse;background:white;width:100%}th,td{text-align:left;vertical-align:top;padding:14px;border-bottom:1px solid #dde3ec}th{background:#e7edf4}code{font-size:13px;overflow-wrap:anywhere}blockquote{background:white;border-left:3px solid #8095af;margin:16px 0;padding:16px;overflow-wrap:anywhere}details{margin:16px 0;padding:14px;background:white}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}footer{font-size:14px;color:#52637b;margin-top:32px}a{color:#164b8c}</style></head>
<body><main><span class="tag">MCP STDIO real · dados sintéticos · agente roteirizado</span>
<h1>Avaliação defensiva de uma sequência de ações</h1>
<p>Uma leitura autorizada é executada. Um resultado de ferramenta contém uma instrução maliciosa. O roteiro tenta escrever fora da política e o hospedeiro bloqueia o despacho, usando a avaliação do SDK.</p>
<div class="notice"><strong>O que esta demo prova:</strong> integração de políticas e evidências por transporte local real. <strong>O que não mede:</strong> resistência de um LLM a prompt injection. A tentativa seguinte já está programada no roteiro; nenhum modelo interpreta o texto.</div>
<div class="cards"><div class="card"><strong>'''+esc(summary['executed'])+'''</strong>Ações sintéticas executadas</div><div class="card"><strong>'''+esc(summary['blocked'])+'''</strong>Tentativas bloqueadas</div><div class="card"><strong>'''+esc(summary['private_resource_dispatched'])+'''</strong>Chamadas ao recurso privado</div></div>
<h2>Decisão, execução e evidência</h2><p>A decisão mostrada é da proposta. A conclusão registra execução ou bloqueio. O SDK observa; a regra de despacho está no executor do hospedeiro.</p>
<div class="scroll"><table><thead><tr><th>Cenário</th><th>Ação proposta</th><th>Avaliação SDK</th><th>Executor</th><th>Evidência</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<h2>Conteúdo recebido da ferramenta</h2><p>Os textos abaixo são dados não confiáveis, exibidos como texto escapado. Eles não alteram política ou autoridade.</p>'''+''.join(excerpts)+'''
<h2>Rastros auditáveis</h2><p>Expanda para ver propostas, conclusões, referências, hashes de catálogo/política e mensagens JSON-RPC dos pipes.</p>'''+''.join(details)+'''
<footer>MCP '''+esc(PROTOCOL_VERSION)+''' em subconjunto controlado, sem certificação completa. Origem local admitida pelo hospedeiro; não representa autenticação criptográfica de servidor remoto. Catálogo verificado tem limites TOCTOU. Nenhuma transação financeira real, API de modelo ou publicação.<br><a href="demo.json">JSON completo</a> · <a href="manifest.json">Hashes dos arquivos</a> · <a href="labels.json">Gabarito sintético separado</a></footer>
</main></body></html>'''

def build_demo(output_dir):
 output=Path(output_dir).resolve()
 output.mkdir(parents=True,exist_ok=False)
 runs=[run_case(scenario,'sdk') for scenario in SCENARIOS]
 summary=summarize(runs)
 labels=[{'scenario':'benign','synthetic':True,'expected_executed':1,'expected_blocked':0},
         {'scenario':'tool_result_injection','synthetic':True,'expected_executed':1,'expected_blocked':1}]
 payload={'summary':summary,'runs':runs,'interpretation':'Scripted choices; no LLM behavior or general efficacy measured.'}
 (output/'demo.json').write_text(encode(payload),encoding='utf-8')
 (output/'labels.json').write_text(encode(labels),encoding='utf-8')
 (output/'index.html').write_text(render_html(summary,runs),encoding='utf-8')
 for filename,items in [('events.jsonl',[{'scenario':r['scenario'],'event':e} for r in runs for e in r['events']]),
                       ('decisions.jsonl',[{'scenario':r['scenario'],'decision':d} for r in runs for d in r['decisions']]),
                       ('transport.jsonl',[{'scenario':r['scenario'],**t} for r in runs for t in r['trace']])]:
  with (output/filename).open('w',encoding='utf-8') as stream:
   for item in items:stream.write(json.dumps(item,ensure_ascii=False,allow_nan=False)+'\n')
 source_paths=[Path(__file__),ROOT/'benchmark/mcp_lab.py',*sorted((ROOT/'arkhe_defense').glob('*.py'))]
 try:version=metadata.version('arkhe-defense-sdk')
 except metadata.PackageNotFoundError:version='source-checkout'
 manifest={'format':'arkhe-controlled-demo-v1','python':platform.python_version(),'sdk_metadata':version,
  'synthetic_only':True,'agent':'deterministic_scripted_not_llm',
  'sources':{p.relative_to(ROOT).as_posix():sha_bytes(p.read_bytes()) for p in source_paths},
  'artifacts':{p.name:sha_bytes(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()}}
 (output/'manifest.json').write_text(encode(manifest),encoding='utf-8')
 return {'output_dir':str(output),'html':str(output/'index.html'),'executed':summary['executed'],
         'blocked':summary['blocked'],'private_resource_dispatched':summary['private_resource_dispatched']}

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output-dir',type=Path,required=True)
 args=parser.parse_args(argv)
 try:result=build_demo(args.output_dir)
 except (ValueError,OSError,TimeoutError) as error:
  print(json.dumps({'error':type(error).__name__,'message':str(error)}),file=sys.stderr)
  return 1
 print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
