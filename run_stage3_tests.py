"""Stage 3 feature, optimizer, real-program and Stage 2 compatibility tests."""
from pathlib import Path
import subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable

def cmd(*args, input_text=None):
    return subprocess.run([str(x) for x in args], input=input_text, text=True,
                          capture_output=True, timeout=12)

def compile_run(source, optimized, input_text, folder):
    ll = folder / 'test.ll'
    binary = folder / 'test'
    ll.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)
    flags = ['--optimize'] if optimized else []
    build_ir = cmd(PYTHON, ROOT/'compiler.py', *flags, source, ll)
    if build_ir.returncode:
        return None, build_ir.stderr
    build = cmd('clang', '-Wno-override-module', ll, '-o', binary)
    if build.returncode:
        return None, build.stderr
    executed = cmd(binary, input_text=input_text)
    if executed.returncode:
        return None, f'program exit status {executed.returncode}: {executed.stderr}'
    return executed.stdout, ''

def main():
    checks = []
    def check(name, condition, message=''):
        checks.append((name, condition, message))
        print(('PASS ' if condition else 'FAIL ') + name + ('' if condition else ': ' + message[:300]), flush=True)

    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        for section in ('stage2_ok', 'stage3_feature_ok', 'stage3_opt'):
            for src in sorted((ROOT/'tests'/section).glob('*.txt')):
                inp = src.with_suffix('.in')
                input_text = inp.read_text() if inp.exists() else ''
                expected = src.with_suffix('.expected').read_text()
                ordinary, err = compile_run(src, False, input_text, tmp)
                check(f'{section}/{src.name} baseline', ordinary == expected, err or repr(ordinary))
                optimized, err = compile_run(src, True, input_text, tmp)
                check(f'{section}/{src.name} optimized', optimized == expected, err or repr(optimized))
                if section == 'stage3_opt':
                    ast = cmd(PYTHON, ROOT/'compiler.py', '--optimize', '--ast', src)
                    check(f'{section}/{src.name} AST', ast.returncode == 0 and ast.stdout == src.with_suffix('.ast').read_text(), ast.stderr)
        for section in ('stage2_err', 'stage3_feature_err'):
            for src in sorted((ROOT/'tests'/section).glob('*.txt')):
                expected = src.with_suffix('.expected').read_text()
                for optimized in (False, True):
                    ll = tmp/'error.ll'
                    ll.unlink(missing_ok=True)
                    flags = ['--optimize'] if optimized else []
                    proc = cmd(PYTHON, ROOT/'compiler.py', *flags, src, ll)
                    check(f'{section}/{src.name} {"optimized" if optimized else "baseline"}',
                          proc.returncode != 0 and proc.stderr == expected and not ll.exists() and not proc.stdout,
                          proc.stderr)
        for session in ('savings_planner', 'savings_planner_zero'):
            inp = (ROOT/'programs'/f'{session}.in').read_text()
            expected = (ROOT/'programs'/f'{session}.expected').read_text()
            for optimized in (False, True):
                output, err = compile_run(ROOT/'programs'/'savings_planner.txt', optimized, inp, tmp)
                check(f'program/{session} {"optimized" if optimized else "baseline"}', output == expected, err or repr(output))
    passed = sum(ok for _, ok, _ in checks)
    print(f'Passed {passed}/{len(checks)} Stage 3 checks')
    return 0 if passed == len(checks) else 1

if __name__ == '__main__':
    sys.exit(main())
