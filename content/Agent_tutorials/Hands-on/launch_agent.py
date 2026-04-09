#!/usr/bin/env python3
"""Unified launcher for ADK examples under Hands-on.

Usage:
  uv run python launch_agent.py list
  uv run python launch_agent.py run <example>
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Example:
    key: str
    root: Path
    entry_hint: str


def _find_adk_roots() -> list[Path]:
    roots = sorted((p.parent for p in BASE_DIR.rglob(".adk")), key=lambda p: len(p.parts))
    selected: list[Path] = []
    for root in roots:
        if any(parent in selected for parent in root.parents):
            continue
        selected.append(root)
    return selected


def _infer_entry_hint(root: Path) -> str:
    direct = root / "agent.py"
    if direct.exists():
        return "."

    candidates = sorted(root.glob("*/agent.py"))
    if candidates:
        return str(candidates[0].parent.relative_to(root))

    candidates = sorted(root.glob("*/*/agent.py"))
    if candidates:
        return str(candidates[0].parent.relative_to(root))

    return "(no agent.py found)"


def discover_examples() -> dict[str, Example]:
    examples: dict[str, Example] = {}
    for root in _find_adk_roots():
        key = root.name
        entry_hint = _infer_entry_hint(root)
        if entry_hint == "app" and root.name != "app":
            key = root.name
        elif entry_hint not in {".", "(no agent.py found)"}:
            key = Path(entry_hint).name

        # Keep keys deterministic if two examples share a name.
        final_key = key
        suffix = 2
        while final_key in examples:
            final_key = f"{key}-{suffix}"
            suffix += 1

        examples[final_key] = Example(key=final_key, root=root, entry_hint=entry_hint)

    return dict(sorted(examples.items(), key=lambda kv: kv[0]))


def list_examples(examples: dict[str, Example]) -> None:
    if not examples:
        print("No ADK examples found under Hands-on.")
        return

    print("Available examples:")
    for key, ex in examples.items():
        rel_root = ex.root.relative_to(BASE_DIR)
        print(f"- {key:16} root={rel_root} entry={ex.entry_hint}")


def run_example(example: Example, dry_run: bool = False) -> int:
    cmd = ["adk", "web", str(example.root)]
    print(f"Launching {example.key} from {example.root.relative_to(BASE_DIR)}")
    print("$ " + " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, cwd=BASE_DIR, check=False).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch Hands-on ADK examples consistently.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List discovered ADK examples")

    run_p = sub.add_parser("run", help="Run an example with adk web")
    run_p.add_argument("example", help="Example key from the list command")
    run_p.add_argument("--dry-run", action="store_true", help="Show command without launching")

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Shorthand: `launch_agent.py <example>` -> `launch_agent.py run <example>`.
    if argv and argv[0] not in {"list", "run", "-h", "--help"}:
        argv.insert(0, "run")

    parser = build_parser()
    args = parser.parse_args(argv)
    examples = discover_examples()

    if args.command == "list":
        list_examples(examples)
        return 0

    if args.command == "run":
        example = examples.get(args.example)
        if not example:
            print(f"Unknown example: {args.example}", file=sys.stderr)
            list_examples(examples)
            return 2
        return run_example(example, dry_run=args.dry_run)

    list_examples(examples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())