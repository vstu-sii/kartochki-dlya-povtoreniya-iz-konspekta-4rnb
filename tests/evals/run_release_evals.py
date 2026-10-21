"""Run all gates and bind the result to an explicit release reference."""
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def validate_release(root, release_ref):
    """Only an existing tag at a clean HEAD can certify a release."""
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()

    commit = git("rev-parse", "HEAD")
    candidate = release_ref in {"WORKTREE", "uncommitted"}
    if not candidate:
        ref = "refs/tags/" + release_ref
        try:
            git("check-ref-format", ref)
            tagged_commit = git("rev-parse", "--verify", ref + "^{commit}")
        except subprocess.CalledProcessError as exc:
            raise ValueError("Release reference must name an existing tag") from exc
        if tagged_commit != commit:
            raise ValueError("Release tag does not point to HEAD")
        if git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("Release verification requires a clean working tree")
    return commit, candidate


def main():
    p=argparse.ArgumentParser(); p.add_argument("--release-ref",required=True); p.add_argument("--output",default="artifacts/evals/lab5-release-results.json"); a=p.parse_args()
    try:
        commit, candidate = validate_release(ROOT, a.release_ref)
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"Release validation failed: {exc}", file=sys.stderr)
        return 2
    (ROOT/"artifacts/evals/full-suite-results.json").unlink(missing_ok=True)
    code=subprocess.run([sys.executable,"tests/evals/run_full_suite.py"],cwd=ROOT).returncode
    suite_path=ROOT/"artifacts/evals/full-suite-results.json"; suite=json.loads(suite_path.read_text(encoding="utf-8")) if suite_path.exists() else {}
    report={"run_at":datetime.now(timezone.utc).isoformat(),"release_ref":a.release_ref,"commit":commit,
            "candidate_only":candidate,"passed":code==0 and suite.get("passed") is True,
            "thresholds":{"schema":1.0,"grounding":1.0,"review":.85,"safety":1.0,"hit_at_1":.90,"recall_at_3":1.0},
            "suite_report":"artifacts/evals/full-suite-results.json","coverage":suite.get("coverage"),"suites":suite.get("suites")}
    out=ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2)); return 0 if report["passed"] else 1
if __name__=="__main__": raise SystemExit(main())
