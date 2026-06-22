"""Coverage-guided mutation testing.

For each mutant, the ONLY tests that can possibly kill it are those that execute
the mutated line (a test that never runs the line can't observe the mutation).
We record per-test line coverage once (pytest --cov-context=test), then for each
mutant run just the covering tests. A mutated line with NO covering test is an
immediate, real survivor -- a coverage gap.

This is both sound and fast, and reuses the same coverage data as coverage-guided
gap hunting. Mutation operators and in-place mutate/restore come from
mutation_probe. Budget-aware (--max-seconds) and resumable (--resume via --out).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coverage  # noqa: E402
import mutation_probe as mp  # noqa: E402


def _atomic_write(path: Path, text: str) -> None:
    """Write via a temp file + os.replace so a kill mid-write leaves the file
    either fully old or fully new -- never truncated."""
    tmp = path.with_suffix(path.suffix + ".muttmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _pristine(path: Path) -> str:
    """The committed (HEAD) source, so a leftover mutant from a killed prior run
    is repaired before we start. Falls back to disk if not tracked."""
    try:
        rel = path.resolve().relative_to(Path.cwd().resolve())
        r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=str(Path.cwd()),
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout
    except Exception:
        pass
    return path.read_text()


def _sites_with_lineno(src: str):
    tree = ast.parse(src)
    flat = list(ast.walk(tree))
    out = []
    for i, node in enumerate(flat):
        if isinstance(node, ast.Compare) and type(node.ops[0]) in mp._CMP_SWAP:
            d = f"cmp {type(node.ops[0]).__name__}->{mp._CMP_SWAP[type(node.ops[0])].__name__}"
        elif isinstance(node, ast.BinOp) and type(node.op) in mp._BIN_SWAP:
            d = f"bin {type(node.op).__name__}->{mp._BIN_SWAP[type(node.op)].__name__}"
        elif isinstance(node, ast.BoolOp):
            d = f"bool {type(node.op).__name__}->{mp._BOOL_SWAP[type(node.op)].__name__}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            d = f"const {node.value}->{not node.value}"
        elif (isinstance(node, ast.Constant) and isinstance(node.value, int)
              and not isinstance(node.value, bool)):
            d = f"int {node.value}->{node.value + 1}"
        else:
            continue
        out.append((i, f"{d} L{node.lineno}", node.lineno))
    return out


def _covering_tests(covdata, abspath, lineno, cap, stem=""):
    """Covering test node-ids, ordered so tests whose file name relates to the
    module under test come FIRST -- under pytest -x the real killer fires early.
    Returns (first `cap`, the remainder, total) so a mutant that survives the
    fast capped set can be confirmed against every remaining covering test
    (sound) without re-running the capped ones."""
    cbl = covdata.contexts_by_lineno(abspath)
    ctxs = cbl.get(lineno, [])
    tests = {c.split("|")[0] for c in ctxs if c and "::" in c}
    ordered = sorted(tests, key=lambda nid: (0 if stem and stem in nid else 1, nid))
    return ordered[:cap], ordered[cap:], len(tests)


def _run(node_ids, timeout):
    try:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x",
                            "-p", "no:cacheprovider", "--no-header", *node_ids],
                           cwd=str(Path.cwd()), capture_output=True, timeout=timeout, env=env)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--cov-file", default=".coverage")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=10**9)
    ap.add_argument("--node-cap", type=int, default=400)
    ap.add_argument("--fallback-tests", nargs="+", default=[],
                    help="run these for lines with no per-line coverage "
                         "(import-time literals/defaults), before calling a survivor")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-seconds", type=float, default=1e9)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    path = Path(args.target)
    original = _pristine(path)
    if path.read_text() != original:
        _atomic_write(path, original)   # repair leftover mutant from a killed run
    abspath = str(path.resolve())
    sites = _sites_with_lineno(original)

    covdata = coverage.CoverageData(basename=args.cov_file)
    covdata.read()
    if abspath not in set(covdata.measured_files()):
        cands = [f for f in covdata.measured_files() if f.endswith(path.name)]
        abspath = cands[0] if cands else abspath

    done = set()
    if args.resume and args.out and Path(args.out).exists():
        for line in Path(args.out).read_text().splitlines():
            try:
                done.add(json.loads(line)["site"])
            except Exception:
                pass

    killed = survived = uncovered = 0
    survivors = []
    t0 = time.time()
    stopped = None
    end = min(args.end, len(sites))
    try:
        for k, desc, lineno in sites[args.start:end]:
            if k in done:
                continue
            if time.time() - t0 > args.max_seconds:
                stopped = k
                break
            tests, remainder, ntests = _covering_tests(covdata, abspath, lineno,
                                                       args.node_cap, stem=path.stem)
            try:
                mutated = mp._mutate(original, k)
            except Exception:
                continue
            run_tests = tests if tests else args.fallback_tests
            if not run_tests:
                uncovered += 1
                survived += 1
                res = "uncovered"
                survivors.append((k, desc, "uncovered (no test, no fallback)"))
            else:
                _atomic_write(path, mutated)
                passed = _run(run_tests, args.timeout)
                _atomic_write(path, original)
                if not tests:                       # import-time line, checked via fallback
                    res = "survived" if passed else "killed"
                    if passed:
                        uncovered += 1
                        survived += 1
                        survivors.append((k, desc, "uncovered (fallback passed)"))
                    else:
                        killed += 1
                else:
                    if passed and remainder:        # confirm vs every remaining covering test
                        _atomic_write(path, mutated)
                        passed = _run(remainder, args.timeout)
                        _atomic_write(path, original)
                    res = "survived" if passed else "killed"
                    if passed:
                        survived += 1
                        survivors.append((k, desc, f"{ntests} tests"))
                    else:
                        killed += 1
            if args.out:
                with open(args.out, "a") as fh:
                    fh.write(json.dumps({"site": k, "line": lineno, "desc": desc,
                                         "result": res, "ntests": ntests}) + "\n")
    finally:
        _atomic_write(path, original)

    if stopped is not None:
        print(f"BUDGET_REACHED next_site={stopped}")
    total = killed + survived
    score = (killed / total * 100) if total else 0.0
    print(f"target={args.target} sites={len(sites)} ran={total} killed={killed} "
          f"survived={survived} (uncovered={uncovered}) score={score:.1f}%")
    for k, d, n in survivors[:40]:
        print(f"  SURVIVED site {k}: {d}  [{n}]")


if __name__ == "__main__":
    main()
