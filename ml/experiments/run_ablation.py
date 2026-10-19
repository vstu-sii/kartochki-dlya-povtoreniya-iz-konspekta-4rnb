"""Measure every review improvement independently on frozen cases."""
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from ml.models import baseline
from ml.models.baseline import BaselineModel

ROOT = Path(__file__).resolve().parents[2]

def cases():
    paths=[ROOT/"docs/quality/golden-dataset/dataset.jsonl",ROOT/"docs/quality/golden-dataset/dataset-v2-additions.jsonl"]
    return [json.loads(line) for path in paths if path.exists() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and '"operation":"review_answer"' in line]

def lexical(model, reference, answer):
    ref=set(reference.lower().split()); got=set(answer.lower().split()); coverage=len(ref & got)/max(1,len(ref))
    return "correct" if coverage>=.72 else "partially_correct" if coverage>=.18 else "incorrect"

def no_stemming_keywords(text):
    """Keep aliases/normalization, but remove only Russian suffix stemming."""
    return {
        word for word in re.findall(r"[a-zа-яё0-9]+", BaselineModel._normalize(text))
        if len(word) > 2 and word not in baseline.STOP_WORDS
    }

def verdict(model, card, answer, variant):
    if variant == "full_semantic_rules":
        return model._deterministic_review(card, answer)["verdict"]
    if variant == "without_phrase_aliases":
        with patch.dict(baseline.PHRASE_ALIASES, {}, clear=True):
            return model._deterministic_review(card, answer)["verdict"]
    if variant == "without_stemming":
        with patch.object(BaselineModel, "_keywords", staticmethod(no_stemming_keywords)):
            return model._deterministic_review(card, answer)["verdict"]
    if variant == "without_source_precision":
        no_source = {**card, "source_quote": ""}
        return model._deterministic_review(no_source, answer)["verdict"]
    if variant == "without_contradiction_guard":
        with patch.object(BaselineModel, "_has_clear_contradiction", staticmethod(lambda _r, _a: False)):
            return model._deterministic_review(card, answer)["verdict"]
    if variant == "raw_lexical_overlap":
        return lexical(model, card["reference_answer"], answer)
    raise ValueError(f"Unknown ablation variant: {variant}")

def main():
    p=argparse.ArgumentParser(); p.add_argument("--output",default="artifacts/experiments/lab5-ablation-results.json"); a=p.parse_args()
    model=BaselineModel(); rows=[]
    variants=("full_semantic_rules", "without_phrase_aliases", "without_stemming",
              "without_source_precision", "without_contradiction_guard", "raw_lexical_overlap")
    for case in cases():
        inp=case["input"]; expected=case["expected_output"]["verdict"]
        card={"reference_answer":inp["reference_answer"],"source_quote":case["context"][0]["text"]}
        predictions={name:verdict(model,card,inp["student_answer"],name) for name in variants}
        rows.append({"id":case["id"],"expected":expected,"predictions":predictions,
                     "correct":{name:value==expected for name,value in predictions.items()}})
    total=len(rows)
    agreement={name:sum(row["correct"][name] for row in rows)/total for name in variants}
    full=agreement["full_semantic_rules"]
    ablation={name:{"agreement":round(score,4),"delta_vs_full_pp":round((score-full)*100,2)}
              for name,score in agreement.items()}
    provider=json.loads((ROOT/"artifacts/experiments/lab4-provider-results.json").read_text(encoding="utf-8"))
    report={"run_at":datetime.now(timezone.utc).isoformat(),"dataset":"frozen Lab2+Lab3 review cases","review_case_count":total,
            "ablation":ablation,
            "prompt_provider_evidence":{"provider":provider["provider"],"model":provider["requested_model"],
              "prompt_a":provider["variant_a"],"prompt_b":provider["variant_b"],"decision":provider["decision"]},"cases":rows}
    out=ROOT/a.output; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="cases"},ensure_ascii=False,indent=2)); return 0 if full>=.85 else 1

if __name__=="__main__": raise SystemExit(main())
