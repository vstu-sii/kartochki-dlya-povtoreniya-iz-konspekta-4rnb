import urllib.request,urllib.error,json,time,uuid
from pathlib import Path
from datetime import datetime,timezone
BASE='https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com'
uid='quality-demo-'+uuid.uuid4().hex[:16]
def call(path,data=None):
 raw=None if data is None else json.dumps(data,ensure_ascii=False).encode()
 req=urllib.request.Request(BASE+path,data=raw,headers={'Content-Type':'application/json','X-User-ID':uid})
 start=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=100) as r: status=r.status; body=r.read().decode()
 except urllib.error.HTTPError as e: status=e.code;body=e.read().decode()
 return {'status':status,'body':json.loads(body),'seconds':round(time.monotonic()-start,3)}
report={'run_at':datetime.now(timezone.utc).isoformat(),'scope':'Public HTTP API; real service/model transport, no mocks; extracted PDF text and student answer, not Telegram UI or binary PDF','user_id':uid,'health_before':call('/health'),'cases':[]}
try:
 setup=call('/v1/ai/card-sets',{'document_id':'quality_'+uuid.uuid4().hex,'pages':[{'page':1,'text':'Кэш хранит часто используемые данные. Кэш уменьшает число обращений к медленной памяти. Индекс ускоряет поиск записей в базе данных.'}]})
 report['setup']=setup
 assert setup['status']==201,setup
 cards=setup['body']; sess=call('/v1/ai/sessions',{'card_set_id':cards['card_set_id'],'user_id':uid});report['session']=sess
 assert sess['status'] in (200,201),sess
 for case in [json.loads(x) for x in Path('tests/security/attacks.jsonl').read_text(encoding='utf-8').splitlines()]:
  if case['point']=='student answer':
   result=call('/v1/ai/answer-reviews',{'session_id':sess['body']['session_id'],'card':cards['cards'][0],'student_answer':case['text']})
  else: result=call('/v1/ai/card-sets',{'document_id':'quality_'+uuid.uuid4().hex,'pages':[{'page':1,'text':case['text']}]})
  block=result['status']==422 and 'PROMPT_INJECTION_BLOCKED' in json.dumps(result['body'])
  passed=block if case['expected_after']=='block' else result['status'] in (200,201)
  report['cases'].append({'id':case['id'],'input':case['text'],'expected':case['expected_after'],'passed':passed,'response':result})
  print(case['id'],passed,flush=True)
except Exception as e: report['error']=str(e)
finally:
 report['health_after']=call('/health');report['passed']=not report.get('error') and len(report['cases'])==16 and all(x['passed'] for x in report['cases'])
 out=Path('docs/demo/public-redteam-2026-10-30.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('report',out,'passed',report['passed'],report.get('error',''))
