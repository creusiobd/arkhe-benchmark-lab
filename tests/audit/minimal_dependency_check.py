"""Optional audit runner: assert tests/audit need no legacy/HTTP/scientific extras."""
import argparse
import importlib.abc
import sys
import os
from pathlib import Path

EXTRAS={'scipy','numpy','yaml','fastapi','httpx','opentelemetry','websockets'}
class BlockExtras(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in EXTRAS:
   raise RuntimeError('Forbidden optional dependency: '+fullname)

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--dependency-dir',type=Path,help='Local pytest packages, if not installed in interpreter')
 args=parser.parse_args()
 root=Path(__file__).resolve().parents[2]
 sys.path.insert(0,str(root))
 if args.dependency_dir:sys.path.insert(0,str(args.dependency_dir.resolve()))
 os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
 sys.meta_path.insert(0,BlockExtras())
 import pytest
 code=pytest.main([str(root/'tests/audit'),'-q'])
 loaded=sorted(name for name in EXTRAS if name in sys.modules)
 print('Loaded forbidden extras:',loaded)
 return code or bool(loaded)

if __name__=='__main__':raise SystemExit(main())
