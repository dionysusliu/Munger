import subprocess
import sys


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True)


def print_section(title: str, result: subprocess.CompletedProcess[str]) -> None:
    print(f"== {title} ==")
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)


def main() -> int:
    deterministic = run(["pytest", "-q"])
    print_section("Deterministic Suite", deterministic)
    if deterministic.returncode != 0:
        return deterministic.returncode

    integration = run(["pytest", "-q", "-m", "integration", "-rs"])
    print_section("Integration Suite", integration)
    if integration.returncode != 0:
        return integration.returncode

    if "blocked external dependency" in integration.stdout.lower():
        print("Integration status: BLOCKED EXTERNAL DEPENDENCY")
    else:
        print("Integration status: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
