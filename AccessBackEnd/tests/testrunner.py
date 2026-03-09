from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    backend_dir = script_dir.parent
    project_root = backend_dir.parent
    report_file = script_dir / "test_results.txt"

    test_files = sorted(script_dir.glob("test_*.py"))

    with report_file.open("w", encoding="utf-8") as report:
        report.write("Accessibility AI backend test run\n")
        report.write(f"Started: {datetime.now().isoformat()}\n")
        report.write(f"Tests directory: {script_dir}\n")
        report.write(f"Project root: {project_root}\n\n")

        exit_code = 0

        for test_file in test_files:
            relative_test_file = test_file.relative_to(project_root)

            header = "=" * 50
            print(header)
            print(f"Running: {relative_test_file}")
            print(header)

            report.write(f"{header}\n")
            report.write(f"Running: {relative_test_file}\n")
            report.write(f"{header}\n")

            process = subprocess.Popen(
                [sys.executable, "-m", "pytest", str(relative_test_file), "-v"],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="")
                report.write(line)

            process.wait()
            if process.returncode != 0:
                exit_code = 1

            print()
            report.write("\n")

        report.write(f"Finished: {datetime.now().isoformat()}\n")
        if exit_code == 0:
            report.write("Overall result: PASS\n")
            print("Overall result: PASS")
        else:
            report.write("Overall result: FAIL\n")
            print("Overall result: FAIL")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())