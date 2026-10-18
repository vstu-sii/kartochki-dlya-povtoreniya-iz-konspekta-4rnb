"""Measure contribution of normalization/semantic rules on frozen review cases."""
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

from ml.models.baseline import BaselineModel

ROOT = Path(__file__).resolve().parents[2]

def cases():
    paths=[ROOT/"docs/quality/golden-dataset/dataset.jsonl",ROOT/"docs/quality/golden-dataset/dataset-v2-additions.jsonl"]
    return [json.loads(line) for path in paths if path.exists() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and '"operation":"review_answer"' in line]

def lexical(model, reference, answer):
    ref=set(reference.lower().split()); got=set(answer.lower().split()); coverage=len(ref & got)/max(1,len(ref))
    return "correct" if coverage>=.72 else "partially_correct" if coverage>=.18 else "incorrect"

def main():
    p=argparse.ArgumentParser(); p.add_argument("--output",default="artifacts/experiments/lab5-ablation-results.json"); a=p.parse_args()
    model=BaselineModel(); rows=[]
    for case in cases():
        inp=case["input"]; expected=case["expected_output"]["verdict"]
        card={"reference_answer":inp["reference_answer"],"source_quote":case["context"][0]["text"]}
        full=model._deterministic_review(card,inp["student_answer"])["verdict"]
        raw=lexical(model,inp["reference_answer"],inp["student_answer"])
        rows.append({"id":case["id"],"expected":expected,"full":full,"without_normalization":raw,
                     "full_correct":full==expected,"without_normalization_correct":raw==expected})
    total=len(rows); full=sum(r["full_correct"] for r in rows)/total; raw=sum(r["without_normalization_correct"] for r in rows)/total
    provider=json.loads((ROOT/"artifacts/experiments/lab4-provider-results.json").read_text(encoding="utf-8"))
    report={"run_at":datetime.now(timezone.utc).isoformat(),"dataset":"frozen Lab2+Lab3 review cases","review_case_count":total,
            "ablation":{"full_semantic_rules":round(full,4),"without_normalization":round(raw,4),"delta_pp":round((full-raw)*100,2)},
            "prompt_provider_evidence":{"provider":provider["provider"],"model":provider["requested_model"],
              "prompt_a":provider["variant_a"],"prompt_b":provider["variant_b"],"decision":provider["decision"]},"cases":rows}
    out=ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},ensure_ascii=False,indent=2)); return 0 if full>=.85 else 1

if __name__=="__main__": raise SystemExit(main())
