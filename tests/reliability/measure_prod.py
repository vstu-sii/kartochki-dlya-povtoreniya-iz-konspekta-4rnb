"""Sample public health and save each observation plus aggregate metrics."""
import argparse, json, statistics, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument("--url", required=True); p.add_argument("--samples", type=int, default=30)
    p.add_argument("--interval", type=float, default=1); p.add_argument("--output", default="artifacts/reliability/prod-window.json"); a=p.parse_args(); samples=[]
    for index in range(a.samples):
        started=time.perf_counter(); status=0
        try:
            with urllib.request.urlopen(a.url, timeout=10) as response: response.read(); status=response.status
        except Exception: pass
        samples.append({"at":datetime.now(timezone.utc).isoformat(),"status":status,"latency_ms":round((time.perf_counter()-started)*1000,2)})
        if index+1<a.samples: time.sleep(a.interval)
    values=sorted(x["latency_ms"] for x in samples); good=sum(200<=x["status"]<400 for x in samples)
    report={"target":a.url,"sample_count":len(samples),"period_start":samples[0]["at"],"period_end":samples[-1]["at"],
            "uptime_percent":round(good/len(samples)*100,2),"latency_p50_ms":round(statistics.median(values),2),
            "latency_p95_ms":values[min(len(values)-1,int(len(values)*.95))],"method":"active HTTP health sampling","samples":samples}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="samples"})); return 0 if good==len(samples) else 1

if __name__ == "__main__": raise SystemExit(main())
