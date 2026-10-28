"""Real Gemini PDF/API/DB acceptance in isolated SQLite (not production)."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from unittest.mock import patch
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--pdf",type=Path,required=True)
    parser.add_argument("--scenarios",type=int,default=2)
    parser.add_argument("--delay-seconds",type=float,default=6,help="Inter-call quota pause, excluded from request latency")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if not os.getenv("GEMINI_API_KEY") or os.getenv("MODEL_PROVIDER")!="gemini":
        raise SystemExit("GEMINI_API_KEY and MODEL_PROVIDER=gemini required; no fallback substitute")
    if args.delay_seconds<0:
        raise SystemExit("delay-seconds must be nonnegative")
    if not 1<=args.scenarios<=10:
        raise SystemExit("scenarios must be 1..10")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from backend.database import Base, session_scope
    from backend.models import CardSet, AnswerReview
    from backend.routers.ai import router
    raw=args.pdf.read_bytes()
    report={"run_at":datetime.now(timezone.utc).isoformat(),"code_sha":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"source_sha256":hashlib.sha256(raw).hexdigest(),"scope":"local real Gemini -> TestClient API -> isolated SQLite; not production","answer_mode":"reference_copy_not_paraphrase","inter_call_delay_seconds":args.delay_seconds,"scenarios":[],"status":"in_progress"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine);sessions=sessionmaker(bind=engine,expire_on_commit=False)
    def db_session():
        with sessions() as db:yield db
    app=FastAPI();app.include_router(router);app.dependency_overrides[session_scope]=db_session
    passed=True
    try:
        with patch("backend.routers.ai.AI_SERVICE_URL","inprocess"),TestClient(app) as client:
            for index in range(args.scenarios):
                owner="quality-local-live-"+uuid4().hex
                row={"number":index+1,"reviews":[]};report["scenarios"].append(row)
                if args.delay_seconds:time.sleep(args.delay_seconds)
                started=time.perf_counter()
                r=client.post("/v1/ai/card-sets/from-pdf",headers={"X-User-ID":owner},files={"file":(args.pdf.name,raw,"application/pdf")},data={"requested_card_count":"5","language":"ru"})
                body=r.json();row["generation"]={"status":r.status_code,"wall_ms":round((time.perf_counter()-started)*1000),"response":body};save()
                if r.status_code!=201 or body.get("fallback_used") is not False or not str(body.get("model","")).startswith("gemini-"):
                    row["passed"]=False;passed=False;continue
                with sessions() as db:
                    row["persisted_cards"]=len(db.get(CardSet,body["card_set_id"]).cards)
                r=client.post("/v1/ai/sessions",json={"card_set_id":body["card_set_id"],"user_id":owner})
                row["session_status"]=r.status_code
                if r.status_code!=201:
                    row["passed"]=False;passed=False;save();continue
                sid=r.json()["session_id"]
                for card in body["cards"][:5]:
                    if args.delay_seconds:time.sleep(args.delay_seconds)
                    started=time.perf_counter()
                    response=client.post("/v1/ai/answer-reviews",headers={"X-User-ID":owner},json={"session_id":sid,"card":card,"student_answer":card["reference_answer"]})
                    answer=response.json();item={"status":response.status_code,"wall_ms":round((time.perf_counter()-started)*1000),"response":answer}
                    with sessions() as db:item["persisted_review"]=bool(answer.get("review_id") and db.get(AnswerReview,answer["review_id"]))
                    row["reviews"].append(item);save()
                reopened=client.get("/v1/ai/sessions/"+sid,headers={"X-User-ID":owner})
                row["reopen_status"]=reopened.status_code
                row["reopened_cards"]=len(reopened.json().get("cards",[]))
                calls=[row["generation"]]+row["reviews"]
                row["passed"]=(row["persisted_cards"]==5 and row["reopened_cards"]==5 and len(row["reviews"])==5 and all(c["status"] in (200,201) and c["response"].get("fallback_used") is False for c in calls) and all(c["persisted_review"] for c in row["reviews"]))
                usage=[c["response"].get("usage",{}) for c in calls]
                row["input_tokens"]=sum(u.get("input_tokens",0) for u in usage)
                row["output_tokens_including_thinking"]=sum(u.get("output_tokens",0) for u in usage)
                row["cost_usd"]=row["input_tokens"]*.30/1e6+row["output_tokens_including_thinking"]*2.50/1e6
                passed &= row["passed"];save()
        lat=[c["wall_ms"] for s in report["scenarios"] for c in s["reviews"]]
        report.update(status="completed",passed=passed,review_sample_size=len(lat),review_p50_ms=statistics.median(lat) if lat else None,review_p95_ms=sorted(lat)[math.ceil(.95*len(lat))-1] if lat else None,p95_method="nearest rank",sample_scope="small local sample, not stable production p95")
    except Exception as exc:
        # Never persist request URLs, headers or credentials in error text.
        report.update(status="failed",passed=False,error_type=type(exc).__name__)
        passed=False
    finally:
        engine.dispose();save()
    print(json.dumps({k:report.get(k) for k in ("status","passed","review_sample_size","review_p95_ms")}))
    return 0 if passed else 1

if __name__=="__main__":
    raise SystemExit(main())
