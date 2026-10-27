"""Measure isolated PDF/API/DB scenarios against an explicitly selected endpoint."""
import argparse,hashlib,json,math,statistics,time
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import httpx
from pypdf import PdfReader,PdfWriter

def main():
 p=argparse.ArgumentParser(); p.add_argument('--url',required=True); p.add_argument('--pdf',type=Path,required=True); p.add_argument('--output',type=Path,required=True); p.add_argument('--runs',type=int,default=3); a=p.parse_args()
 raw=a.pdf.read_bytes(); report={'started_at':datetime.now(timezone.utc).isoformat(),'scope':'HTTP PDF upload through extraction, generation and persistence; review HTTP through persistence. No Telegram/browser rendering.','source_pdf_name':a.pdf.name,'source_pdf_sha256':hashlib.sha256(raw).hexdigest(),'execution_sha':None,'identity_scope':'Fresh isolated smoke accounts; excluded from usefulness and North Star','runs':[]}
 def save():
  a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 def timed(client,method,path,**kw):
  t=time.perf_counter(); r=client.request(method,a.url.rstrip('/')+path,**kw); elapsed=round((time.perf_counter()-t)*1000,2)
  try: data=r.json()
  except ValueError: data={'response_excerpt':r.text[:400]}
  if r.status_code>=400: raise RuntimeError(json.dumps({'path':path,'status':r.status_code,'elapsed_ms':elapsed,'response':data},ensure_ascii=False))
  return data,elapsed
 with httpx.Client(timeout=httpx.Timeout(75,connect=12),follow_redirects=True) as c:
  try: report['health_before'],_=timed(c,'GET','/health')
  except Exception as e: report['preflight_error']=str(e); save(); return 1
  save()
  for index in range(a.runs):
   uid='quality-lab5-'+uuid4().hex[:20]; row={'index':index+1,'user_id':uid,'started_at':datetime.now(timezone.utc).isoformat(),'reviews':[]}; report['runs'].append(row)
   try:
    writer=PdfWriter(); writer.clone_document_from_reader(PdfReader(BytesIO(raw))); writer.add_metadata({'/QualityMeasurementNonce':uuid4().hex}); stream=BytesIO(); writer.write(stream); payload=stream.getvalue(); row['uploaded_pdf_sha256']=hashlib.sha256(payload).hexdigest(); row['cache_control']='Distinct PDF metadata per run; text unchanged, no reuse of idempotency result.'
    h={'X-User-ID':uid}
    cardset,elapsed=timed(c,'POST','/v1/ai/card-sets/from-pdf',headers=h,files={'file':('quality-source.pdf',payload,'application/pdf')},data={'requested_card_count':'5','language':'ru'})
    row['pdf_to_saved_cards_ms']=elapsed; row['card_set']=cardset; save(); print('run',index+1,'generation',elapsed,'ms',cardset.get('model'),flush=True)
    session,_=timed(c,'POST','/v1/ai/sessions',headers=h,json={'card_set_id':cardset['card_set_id'],'user_id':uid}); row['session_id']=session['session_id']
    for position,card in enumerate(cardset['cards'],start=1):
     review,elapsed=timed(c,'POST','/v1/ai/answer-reviews',headers=h,json={'session_id':session['session_id'],'card':card,'student_answer':card['reference_answer']})
     row['reviews'].append({'position':position,'student_answer':card['reference_answer'],'answer_to_saved_review_ms':elapsed,'response':review})
     timed(c,'PATCH','/v1/ai/sessions/'+session['session_id']+'/progress',headers=h,json={'current_position':position}); save(); print('run',index+1,'review',position,elapsed,'ms',review.get('model'),flush=True)
    persisted,_=timed(c,'GET','/v1/ai/sessions/'+session['session_id'],headers=h); row['persistence_verified']=persisted['card_set_id']==cardset['card_set_id'] and persisted['current_position']==len(cardset['cards']); row['completed']=True
   except Exception as e: row['error']=type(e).__name__+': '+str(e); print('run',index+1,'error',row['error'],flush=True)
   save()
 report['ended_at']=datetime.now(timezone.utc).isoformat()
 for field,values in [('pdf_to_cards',[r['pdf_to_saved_cards_ms'] for r in report['runs'] if 'pdf_to_saved_cards_ms' in r]),('answer_to_review',[v['answer_to_saved_review_ms'] for r in report['runs'] for v in r['reviews']])]:
  values.sort(); report[field]={'n':len(values),'raw_ms':values,'p50_ms':statistics.median(values) if values else None,'p95_ms':values[math.ceil(.95*len(values))-1] if values else None,'method':'median / nearest-rank p95'}
 report['completed_scenarios']=sum(r.get('completed',False) for r in report['runs']); save(); return 0 if report['completed_scenarios']==a.runs else 1
if __name__=='__main__': raise SystemExit(main())
