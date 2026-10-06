"""Offline SDK artifact verifier. Stdlib orchestration; smoke needs SDK runtime deps.

No installation or download is performed. Optional --installed checks an already
installed interpreter; otherwise a validated wheel is extracted for isolated smoke.
"""
from __future__ import annotations
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PACKAGES={'arkhe-defense-sdk':('arkhe_defense','sdk','README_DEFENSIVE_SDK.md'),
          'arkhe-trajectory-sdk':('arkhe_trajectory','trajectory-sdk','README_TRAJECTORY_SDK.md')}

def require(condition,message):
 if not condition:raise ValueError(message)

def safe_name(name):
 normalized=name.replace('\\','/')
 path=PurePosixPath(normalized)
 require(bool(normalized) and bool(path.parts) and not path.is_absolute() and '\x00' not in normalized
         and ':' not in normalized and '..' not in path.parts,'unsafe archive/manifest path')
 return path

def sha(data):return hashlib.sha256(data).hexdigest()
def metadata(data,name,version):
 fields=BytesParser().parsebytes(data)
 require(fields['Name']==name and fields['Version']==version,'distribution metadata mismatch')
 return fields

def verify(output,python=None,installed=False,rebuild=False):
 output=Path(output).resolve()
 manifest=json.loads((output/'build-manifest.json').read_text(encoding='utf-8'))
 name,version=manifest['distribution'],manifest['version']
 require(name in PACKAGES,'unknown SDK distribution')
 namespace,project,readme=PACKAGES[name]
 expected_sources={}
 for rel,digest in manifest['sources'].items():
  path=safe_name(rel)
  require(path.parts[0]==namespace,'foreign source namespace in manifest')
  source=(ROOT/Path(*path.parts)).resolve()
  require(source.is_relative_to((ROOT/namespace).resolve()),'source escapes namespace')
  require(source.is_file() and sha(source.read_bytes())==digest,'checkout source hash mismatch: '+rel)
  expected_sources[path.as_posix()]=digest
 current={p.relative_to(ROOT).as_posix() for p in (ROOT/namespace).rglob('*')
          if p.is_file() and p.suffix in {'.py','.json'} and '__pycache__' not in p.parts}
 require(current==set(expected_sources),'manifest does not cover complete SDK sources')
 artifacts={}
 for filename,digest in manifest['artifacts'].items():
  path=safe_name(filename);require(len(path.parts)==1,'artifact must be a basename')
  artifact=output/filename
  require(artifact.is_file() and sha(artifact.read_bytes())==digest,'artifact hash mismatch: '+filename)
  artifacts[filename]=artifact
 wheels=[p for p in artifacts.values() if p.suffix=='.whl']
 sdists=[p for p in artifacts.values() if p.name.endswith('.tar.gz')]
 require(len(wheels)==len(sdists)==1 and len(artifacts)==2,'one wheel and one sdist required')
 wheel,sdist=wheels[0],sdists[0]
 license_bytes=(ROOT/'LICENSE').read_bytes()
 with zipfile.ZipFile(wheel) as archive:
  names=archive.namelist();require(len(names)==len(set(names)),'duplicate wheel entries')
  paths=[safe_name(n) for n in names]
  info_roots={p.parts[0] for p in paths if p.parts[0].endswith('.dist-info')}
  require(len(info_roots)==1,'one dist-info required')
  info=next(iter(info_roots))
  require(all(p.parts[0] in {namespace,info} for p in paths),'wheel contains foreign namespace')
  metadata(archive.read(info+'/METADATA'),name,version)
  licenses=[n for n in names if PurePosixPath(n).name=='LICENSE']
  require(bool(licenses) and all(archive.read(n)==license_bytes for n in licenses),'wheel LICENSE missing/mismatch')
  contained={n for n in names if n.startswith(namespace+'/') and not n.endswith('/')}
  require(contained==set(expected_sources),'wheel source inventory mismatch')
  for rel,digest in expected_sources.items():require(sha(archive.read(rel))==digest,'wheel source differs: '+rel)
 with tarfile.open(sdist,'r:gz') as archive:
  members=archive.getmembers();require(len(members)==len({m.name for m in members}),'duplicate sdist entries')
  paths=[safe_name(m.name) for m in members]
  prefixes={p.parts[0] for p in paths};require(len(prefixes)==1,'sdist must have one root')
  prefix=next(iter(prefixes));data={}
  for member,path in zip(members,paths):
   require(member.isfile() or member.isdir(),'sdist links/devices prohibited')
   if member.isfile():
    rel=PurePosixPath(*path.parts[1:]).as_posix()
    require(bool(path.parts[1:]),'sdist root cannot be a file')
    data[rel]=archive.extractfile(member).read()
  metadata(data['PKG-INFO'],name,version)
  require(data['LICENSE']==license_bytes,'sdist LICENSE mismatch')
  require(data['pyproject.toml']==(ROOT/project/'pyproject.toml').read_bytes(),'sdist pyproject differs from checkout')
  require(data['README.md']==(ROOT/readme).read_bytes(),'sdist README differs from checkout')
  allowed={'PKG-INFO','LICENSE','README.md','pyproject.toml','setup.cfg'}
  require(all(rel in allowed or rel.startswith(namespace+'/') or
              rel.startswith(name.replace('-','_')+'.egg-info/') for rel in data),'foreign sdist content')
  contained={rel for rel in data if rel.startswith(namespace+'/')}
  require(contained==set(expected_sources),'sdist source inventory mismatch')
  for rel,digest in expected_sources.items():require(sha(data[rel])==digest,'sdist source differs: '+rel)
 executable=str(Path(python).resolve()) if python else sys.executable
 with tempfile.TemporaryDirectory(prefix='arkhe-release-verify-') as tmp:
  temp=Path(tmp);extracted=temp/'wheel';extracted.mkdir()
  with zipfile.ZipFile(wheel) as archive:archive.extractall(extracted)
  smoke='''import importlib,importlib.metadata,importlib.resources,json,pathlib,sys,contextlib,io
root,name,version,namespace,checkout,installed=sys.argv[1:]
if installed!='1':sys.path.insert(0,root)
module=importlib.import_module(namespace)
location=pathlib.Path(module.__file__).resolve()
assert not location.is_relative_to((pathlib.Path(checkout)/namespace).resolve()),'import came from checkout namespace'
if installed=='1':assert location.is_relative_to(pathlib.Path(sys.prefix).resolve()),'import is not installed in selected interpreter'
if installed!='1':assert location.is_relative_to(pathlib.Path(root).resolve()),'wrong extracted namespace'
distribution=importlib.metadata.distribution(name)
assert distribution.version==version,'installed/extracted version mismatch'
for public in module.__all__:assert hasattr(module,public),public
entries=[]
for entry in distribution.entry_points:
 if entry.group=='console_scripts':
  entrymodule,function=entry.value.split(':',1)
  assert callable(getattr(importlib.import_module(entrymodule),function))
  entries.append(entry.name)
journal=importlib.import_module(namespace+'.journal')
cli=importlib.import_module(namespace+'.cli')
config_path=pathlib.Path('smoke-config.json')
if namespace=='arkhe_defense':configuration={'schema_version':'1','mode':'observe'}
else:
 configuration=json.loads(importlib.resources.files(namespace).joinpath('presets','cards.json').read_text(encoding='utf-8'))
 configuration.update(tenant_id='release-smoke',version='smoke')
config_path.write_text(json.dumps(configuration),encoding='utf-8')
diagnostics={}
for command in [['doctor'],['validate-config',str(config_path)]]:
 stream=io.StringIO()
 with contextlib.redirect_stdout(stream):code=cli.main(command)
 assert code==0,'CLI smoke failed: '+command[0]
 diagnostics[command[0]]=json.loads(stream.getvalue())
assert diagnostics['doctor']['sdk']==version
assert diagnostics['validate-config']['valid'] is True
print(json.dumps({'name':name,'version':distribution.version,'module_path':str(location),'entry_points':entries,'journal_imported':bool(journal),'installed':installed=='1','cli':diagnostics}))
'''
  result=subprocess.run([executable,'-I','-c',smoke,str(extracted),name,version,namespace,str(ROOT),'1' if installed else '0'],
                        cwd=temp,capture_output=True,text=True,encoding='utf-8',timeout=30)
  require(result.returncode==0,'isolated smoke failed: '+result.stderr.strip())
  require(len(result.stdout.splitlines())==1,'smoke stdout must contain only one metadata record')
  smoke_result=json.loads(result.stdout)
  rebuilt=None
  if rebuild:
   source=temp/'source';source.mkdir()
   for rel,content in data.items():
    destination=source/Path(*safe_name(rel).parts);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(content)
   target=temp/'rebuilt';target.mkdir()
   code='from setuptools import build_meta;import sys;build_meta.build_wheel(sys.argv[1])'
   result=subprocess.run([executable,'-I','-c',code,str(target)],cwd=source,capture_output=True,text=True,timeout=120)
   require(result.returncode==0,'sdist rebuild failed: '+result.stderr.strip())
   built=list(target.glob('*.whl'));require(len(built)==1,'sdist rebuild wheel count mismatch')
   with zipfile.ZipFile(built[0]) as archive:
    for rel,digest in expected_sources.items():require(sha(archive.read(rel))==digest,'rebuilt wheel source mismatch')
   rebuilt={'wheel':built[0].name,'sources_match':True}
 return {'distribution':name,'version':version,'namespace':namespace,'source_count':len(expected_sources),
         'manifest_hash':sha((output/'build-manifest.json').read_bytes()),'artifacts':manifest['artifacts'],
         'license_verified':True,'archive_paths_safe':True,'isolated_smoke':smoke_result,'sdist_rebuild':rebuilt}

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True,help='Directory containing build-manifest.json')
 parser.add_argument('--python',type=Path,help='Interpreter used for isolated import smoke')
 parser.add_argument('--installed',action='store_true',help='Smoke the already installed SDK, no sys.path injection')
 parser.add_argument('--rebuild-sdist',action='store_true',help='Rebuild validated sdist offline, setuptools required')
 args=parser.parse_args()
 try:result=verify(args.output,args.python,args.installed,args.rebuild_sdist)
 except (ValueError,KeyError,OSError,subprocess.SubprocessError,zipfile.BadZipFile,tarfile.TarError) as error:
  print(json.dumps({'verified':False,'error':str(error)}));return 1
 print(json.dumps({'verified':True,**result},indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
