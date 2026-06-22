"""Self-contained AST mutation-testing harness.

Why not mutmut here: mutmut 3.x copies the project into a ``mutants/`` tree and
re-runs pytest there; with this repo's src-layout + editable install that needs
environment tuning the sandbox can't persist. This harness mutates the target
module in place (the editable install points at the same file, so the mutation
takes effect), runs the test suite, records whether the mutation was caught
(killed) or not (survived), and always restores the original source.

Mutation operators: comparison-op swaps (boundary/negation), arithmetic-op
swaps, boolean and/or swap, boolean-constant flip, and integer-literal +/-1.
One mutation per run. Supports slicing ([--start,--end)) so a large module can
be swept across several short invocations; results append to --out as JSONL.

A mutation is a true SURVIVOR only if the FULL suite fails to kill it, so the
fast targeted suite is used first and each survivor is re-checked against the
full suite (--verify-tests) before being reported.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

_CMP_SWAP = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is,
    ast.In: ast.NotIn, ast.NotIn: ast.In,
}
_BIN_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv}
_BOOL_SWAP = {ast.And: ast.Or, ast.Or: ast.And}


def _collect_sites(tree: ast.AST) -> list[tuple[int, str]]:
    """Return mutation sites as (node-counter, description). The counter is the
    index in a fixed ast.walk order; the transformer below replays it."""
    sites = []
    for i, node in enumerate(ast.walk(tree)):
        if isinstance(node, ast.Compare) and type(node.ops[0]) in _CMP_SWAP:
            sites.append((i, f"cmp {type(node.ops[0]).__name__}->"
                             f"{_CMP_SWAP[type(node.ops[0])].__name__} L{node.lineno}"))
        elif isinstance(node, ast.BinOp) and type(node.op) in _BIN_SWAP:
            sites.append((i, f"bin {type(node.op).__name__}->"
                             f"{_BIN_SWAP[type(node.op)].__name__} L{node.lineno}"))
        elif isinstance(node, ast.BoolOp):
            sites.append((i, f"bool {type(node.op).__name__}->"
                             f"{_BOOL_SWAP[type(node.op)].__name__} L{node.lineno}"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            sites.append((i, f"const {node.value}->{not node.value} L{node.lineno}"))
        elif (isinstance(node, ast.Constant) and isinstance(node.value, int)
              and not isinstance(node.value, bool)):
            sites.append((i, f"int {node.value}->{node.value + 1} L{node.lineno}"))
    return sites


def _mutate(src: str, target_counter: int) -> str:
    tree = ast.parse(src)
    for i, node in enumerate(ast.walk(tree)):
        if i != target_counter:
            continue
        if isinstance(node, ast.Compare):
            node.ops[0] = _CMP_SWAP[type(node.ops[0])]()
        elif isinstance(node, ast.BinOp):
            node.op = _BIN_SWAP[type(node.op)]()
        elif isinstance(node, ast.BoolOp):
            node.op = _BOOL_SWAP[type(node.op)]()
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            node.value = not node.value
        elif isinstance(node, ast.Constant) and isinstance(node.value, int):
            node.value = node.value + 1
        break
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def _run_tests(tests: list[str], timeout: int) -> bool:
    """True if the suite PASSES (mutation survived); False if it fails (killed)."""
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x",
                            "-p", "no:cacheprovider", "--no-header", *tests],
                           cwd=str(Path.cwd()), capture_output=True, timeout=timeout)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False        # a hang (e.g. mutated loop bound) counts as killed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--tests", nargs="+", required=True, help="fast targeted suite")
    ap.add_argument("--verify-tests", nargs="+", default=None,
                    help="broader suite to confirm survivors (default: --tests)")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=10**9)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    path = Path(args.target)
    original = path.read_text()
    sites = _collect_sites(ast.parse(original))
    verify = args.verify_tests or args.tests
    end = min(args.end, len(sites))
    killed = survived = errored = 0
    survivors = []
    try:
        for k, desc in [(c, d) for c, d in sites][args.start:end]:
            try:
                mutated = _mutate(original, k)
            except Exception:             # unparse/parse hiccup -> skip site
                errored += 1
                continue
            path.write_text(mutated)
            passed = _run_tests(args.tests, args.timeout)
            if passed:                    # survived targeted -> confirm vs broader suite
                if verify != args.tests:
                    passed = _run_tests(verify, args.timeout)
                if passed:
                    survived += 1
                    survivors.append({"site": k, "desc": desc})
                else:
                    killed += 1
            else:
                killed += 1
            if args.out:
                with open(args.out, "a") as fh:
                    fh.write(json.dumps({"site": k, "desc": desc,
                                         "result": "survived" if passed else "killed"}) + "\n")
    finally:
        path.write_text(original)         # ALWAYS restore

    total = killed + survived
    score = (killed / total * 100) if total else 0.0
    print(f"target={args.target} sites={len(sites)} ran={total} "
          f"killed={killed} survived={survived} skipped_errors={errored}")
    print(f"mutation score (killed/ran) = {score:.1f}%")
    for s in survivors:
        print(f"  SURVIVED: site {s['site']}: {s['desc']}")


if __name__ == "__main__":
    main()
