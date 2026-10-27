"""Reproduce formula extraction and per-formula generation coverage."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.pdf_extractor import extract_pdf_pages
from backend.quality_guards import validate_model_card
from ml.models.baseline import BaselineModel

class QuietTrace:
    def record(self,*args,**kwargs):
        pass


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artifacts/ai/formula-fix-2026-10-27/formula-results.json")
    args=parser.parse_args()
    os.environ["MODEL_PROVIDER"]="deterministic"
    fixture=ROOT/"tests/fixtures/lab5-formulas-source.pdf"
    reference=json.loads((ROOT/"tests/fixtures/lab5-formulas-expected.json").read_text(encoding="utf-8"))
    pages=extract_pdf_pages(fixture.read_bytes())
    model=BaselineModel(QuietTrace())
    rows=[]
    batches=[]
    for page in pages:
        formulas=[row for row in reference if row["page"]==page.page]
        for start in range(0,len(formulas),10):
            batch=formulas[start:start+10]
            # Only actually extracted formulas enter generation. Never inject
            # the expected transcription as source text to obtain a green run.
            extracted=[row["expected_latex"] for row in batch if row["expected_latex"] in page.text]
            source="\n".join(extracted)
            output=model.generate({"document_id":"formula-quality-batch","pages":[{"page":page.page,"text":source}],"requested_card_count":10,"language":"ru","user_id":"formula-quality-owner","resource_owner_id":"formula-quality-owner"}) if extracted else {"cards":[]}
            batches.append({"page":page.page,"start":start,"source":source,"output":output})
            for row in batch:
                matches=[card for card in output["cards"] if card["reference_answer"]==row["expected_latex"]]
                grounded=bool(matches) and validate_model_card(matches[0],{page.page:source}) is None
                rows.append({**row,"extracted_intact":row["expected_latex"] in page.text,"preserved_in_generated_thesis":grounded})
    preserved=sum(row["preserved_in_generated_thesis"] for row in rows)
    report={"source_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),"base_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"working_tree_changes_included":bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).strip()),"provider":"deterministic","review_kind":"automated_against_agent_visual_transcription","human_review":None,"total":len(rows),"preserved":preserved,"lost_or_degraded":len(rows)-preserved,"loss_rate":(len(rows)-preserved)/len(rows),"target":.10,"passed":(len(rows)-preserved)/len(rows)<.10,"scope":"Exhaustive per-formula generation in batches <=10, on one vector PDF. Not whole-document set coverage, OCR, production or Gemini.","pages":[vars(page) for page in pages],"rows":rows,"batches":batches}
    dest=ROOT/args.output;dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("total","preserved","lost_or_degraded","loss_rate","passed")}))
    return 0 if report["passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
