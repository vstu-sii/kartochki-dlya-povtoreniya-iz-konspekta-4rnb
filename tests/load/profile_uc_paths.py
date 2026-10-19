"""Profile representative UC-01, UC-02 and UC-04 HTTP paths."""
import argparse
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib import request
from uuid import uuid4


def call(base, method, path, payload=None, headers=None, timeout=15):
    data=json.dumps(payload,ensure_ascii=False).encode("utf-8") if payload is not None else None
    req=request.Request(base.rstrip("/")+path,data=data,method=method,
                        headers={"Content-Type":"application/json",**(headers or {})})
    started=time.perf_counter()
    try:
        with request.urlopen(req,timeout=timeout) as response:
            body=json.loads(response.read())
            return response.status,body,round((time.perf_counter()-started)*1000,2)
    except Exception as exc:  # failure type is measurement data
        return 0,{"error":type(exc).__name__},round((time.perf_counter()-started)*1000,2)


def percentile(values,fraction):
    ordered=sorted(values)
    return ordered[min(len(ordered)-1,math.ceil(len(ordered)*fraction)-1)]


def summarize(name,samples,expected):
    latencies=[sample[2] for sample in samples]
    successes=sum(sample[0]==expected for sample in samples)
    return {"scenario":name,"requests":len(samples),"successes":successes,
            "error_rate":round(1-successes/len(samples),4),
            "p50_ms":round(statistics.median(latencies),2),
            "p95_ms":round(percentile(latencies,.95),2)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url",default="http://127.0.0.1:8095")
    parser.add_argument("--concurrency",type=int,default=5)
    parser.add_argument("--requests",type=int,default=40)
    parser.add_argument("--output",default="artifacts/load/lab5-uc-profile.json")
    args=parser.parse_args(); user=f"uc-profile-{uuid4().hex[:10]}"
    text=("Кэш процессора хранит часто используемые данные. TCP устанавливает соединение. "
          "Первичный ключ идентифицирует строку. Транзакция атомарна. Индекс ускоряет поиск.")

    def generate(index):
        suffix=uuid4().hex[:10]
        return call(args.base_url,"POST","/v1/ai/card-sets",
                    {"document_id":f"profile-{suffix}","language":"ru","requested_card_count":5,
                     "pages":[{"page":1,"text":text}]},
                    {"X-User-ID":f"{user}-{index}","Idempotency-Key":suffix})

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        generation=list(pool.map(generate,range(args.requests)))
    first=next(body for status,body,_ in generation if status==201)
    status,session,_=call(args.base_url,"POST","/v1/ai/sessions",
                          {"card_set_id":first["card_set_id"],"user_id":user})
    if status!=201: raise RuntimeError("Could not prepare study session")
    card=first["cards"][0]

    def review(_index):
        return call(args.base_url,"POST","/v1/ai/answer-reviews",
                    {"session_id":session["session_id"],"card":card,
                     "student_answer":card["reference_answer"]},{"X-User-ID":user})
    def resume(_index):
        return call(args.base_url,"GET",f"/v1/ai/sessions/{session['session_id']}",headers={"X-User-ID":user})
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool: reviews=list(pool.map(review,range(args.requests)))
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool: resumes=list(pool.map(resume,range(args.requests)))
    report={"measured_at":datetime.now(timezone.utc).isoformat(),"base_url":args.base_url,
            "concurrency":args.concurrency,"profiles":[summarize("UC-01 generate/model/DB",generation,201),
            summarize("UC-02 review/model/DB",reviews,200),summarize("UC-04 resume/DB",resumes,200)]}
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if all(row["error_rate"]==0 for row in report["profiles"]) else 1


if __name__=="__main__": raise SystemExit(main())
