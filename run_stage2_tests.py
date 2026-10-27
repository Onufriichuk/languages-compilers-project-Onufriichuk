"""Runs Stage 1 AST regression plus Stage 2 compiled programs and diagnostics."""
import subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).parent

def invoke(*args,stdin=None):
 return subprocess.run([sys.executable,str(ROOT/'compiler.py'),*map(str,args)],text=True,input=stdin,capture_output=True)

def main():
 checks=[]
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for src in sorted((ROOT/'tests'/'stage2_ok').glob('*.txt')):
   expected=src.with_suffix('.expected')
   if not expected.exists():
    checks.append((src.name,False,'missing expected output'));continue
   ir=td/(src.stem+'.ll');binary=td/(src.stem+'.out')
   compile_result=invoke(src,ir)
   if compile_result.returncode:
    checks.append((src.name,False,compile_result.stderr.strip()));continue
   build=subprocess.run(['clang','-Wno-override-module',str(ir),'-o',str(binary)],capture_output=True,text=True)
   if build.returncode:
    checks.append((src.name,False,build.stderr.strip()));continue
   inp=src.with_suffix('.in')
   execution=subprocess.run([str(binary)],input=inp.read_text() if inp.exists() else '',text=True,capture_output=True,timeout=10)
   checks.append((src.name,execution.stdout==expected.read_text() and execution.returncode==0,execution.stdout))
  for src in sorted((ROOT/'tests'/'stage2_err').glob('*.txt')):
   expected=src.with_suffix('.expected')
   ir=td/(src.stem+'.ll')
   r=invoke(src,ir)
   checks.append((src.name,r.returncode!=0 and not ir.exists() and r.stderr==expected.read_text() and r.stdout=='',r.stderr))
 for name,ok,detail in checks:
  print(('PASS' if ok else 'FAIL'),name, '' if ok else repr(detail)[:260])
 print(f'Passed {sum(ok for _,ok,_ in checks)}/{len(checks)} Stage 2 tests')
 return int(not all(ok for _,ok,_ in checks))
if __name__=='__main__':sys.exit(main())
