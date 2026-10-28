"""Write source hashes needed to audit a release."""
import hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; names=["requirements.lock","Dockerfile","compose.yml","backend/requirements.txt","ml/requirements.txt"]
report={"created_at":datetime.now(timezone.utc).isoformat(),"git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "files":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}}
out=ROOT/"artifacts/release/lab5-manifest.json"; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(out)
