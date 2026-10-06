import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent
COMPILER = ROOT / "compiler.py"
OK_DIR = ROOT / "tests" / "ok"
ERR_DIR = ROOT / "tests" / "err"


def run_command(test_file: Path):
    return subprocess.run(
        [
            sys.executable,
            str(COMPILER),
            "--ast",
            str(test_file),
        ],
        capture_output=True,
        text=True,
    )


def run_ok_tests():
    passed = 0
    failed = 0

    for test_file in sorted(OK_DIR.glob("*.txt")):
        expected_file = test_file.with_suffix(".expected")

        if not expected_file.exists():
            print(f"FAIL {test_file.name}: missing expected file")
            failed += 1
            continue

        result = run_command(test_file)
        expected = expected_file.read_text()

        if result.returncode != 0:
            print(f"FAIL {test_file.name}: compiler returned error")
            print(result.stderr.rstrip())
            failed += 1
            continue

        if result.stderr:
            print(f"FAIL {test_file.name}: unexpected stderr")
            print(result.stderr.rstrip())
            failed += 1
            continue

        if result.stdout != expected:
            print(f"FAIL {test_file.name}: output differs")
            failed += 1
            continue

        print(f"PASS {test_file.name}")
        passed += 1

    return passed, failed


def run_error_tests():
    passed = 0
    failed = 0

    for test_file in sorted(ERR_DIR.glob("*.txt")):
        expected_file = test_file.with_suffix(".expected")

        if not expected_file.exists():
            print(f"FAIL {test_file.name}: missing expected file")
            failed += 1
            continue

        result = run_command(test_file)
        expected = expected_file.read_text()

        if result.returncode == 0:
            print(f"FAIL {test_file.name}: expected compilation failure")
            failed += 1
            continue

        if result.stdout:
            print(f"FAIL {test_file.name}: unexpected stdout")
            failed += 1
            continue

        if result.stderr != expected:
            print(f"FAIL {test_file.name}: error output differs")
            failed += 1
            continue

        print(f"PASS {test_file.name}")
        passed += 1

    return passed, failed


def main():
    ok_passed, ok_failed = run_ok_tests()
    err_passed, err_failed = run_error_tests()

    total_passed = ok_passed + err_passed
    total_failed = ok_failed + err_failed
    total = total_passed + total_failed

    print()
    print(f"Passed: {total_passed}/{total}")
    print(f"Failed: {total_failed}/{total}")

    if total_failed != 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
