import json, os, time, urllib.parse, urllib.request
from datetime import date, timedelta
from pathlib import Path
from quran_workflow.content_extract import extract
from quran_workflow.airtable_db import create_item, list_items, update_status
from quran_workflow.buffer_db import publish_media_item, upload_public
from render_card import render_card
TOKEN=os.environ['TELEGRAM_BOT_TOKEN']; ADMIN_CHAT_ID=2021636669; BASE=f'https://api.telegram.org/bot{TOKEN}/'
ROOT=Path(__file__).resolve().parent; STATE=ROOT/'bot_state.json'; QUEUE=ROOT/'manual_queue.json'; CONFIG=ROOT/'schedule_config.json'
def api(method,**data):
 req=urllib.request.Request(BASE+method,data=urllib.parse.urlencode(data).encode(),method='POST')
 with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())
def send(text,markup=None):
 d={'chat_id':ADMIN_CHAT_ID,'text':text}
 if markup:d['reply_markup']=json.dumps(markup,ensure_ascii=False)
 return api('sendMessage',**d)
def home():return {'keyboard':[[{'text':'⬆️ تحميل محتوى'},{'text':'📤 نشر محتوى'}],[{'text':'⏰ المواعيد'},{'text':'🗓 محتوى اليوم'}],[{'text':'📚 القاعدة'},{'text':'⏳ للمراجعة'}]],'resize_keyboard':True,'is_persistent':True}
def cancel():return {'inline_keyboard':[[{'text':'❌ إلغاء','callback_data':'cancel'}]]}
def sections(action):return {'inline_keyboard':[[{'text':'📖 قرآن','callback_data':f'{action}|quran'},{'text':'📜 حديث','callback_data':f'{action}|hadith'}],[{'text':'❓ سؤال وجواب','callback_data':f'{action}|qa'}],[{'text':'❌ إلغاء','callback_data':'cancel'}]]}
def state():return json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
def save_state(s):STATE.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
def kind_name(k):return {'quran':'قرآن','hadith':'حديث','qa':'سؤال وجواب'}.get(k,k)
def next_slot(kind,items):
 slots=[]
 if CONFIG.exists():
  try:slots=json.loads(CONFIG.read_text()).get('slots',[])
  except:pass
 slots=slots or [{'time':'09:00','kind':kind}]; start=date.today()+timedelta(days=1)
 for n in range(366):
  d=(start+timedelta(days=n)).isoformat()
  for s in slots:
   if s.get('kind') in (kind,'all') and not any(x.get('scheduled_date')==d and x.get('publish_time')==s.get('time') for x in items):return d,s.get('time','09:00')
 return start.isoformat(),slots[0].get('time','09:00')
def save_item(item):
 items=list_items(); kind=item.get('kind','qa'); d,t=next_slot(kind,items); item=dict(item); item.update({'kind':kind,'scheduled_date':item.get('scheduled_date') or d,'publish_time':item.get('publish_time') or t,'airtable_status':'معتمد','id':item.get('id') or f'content-{int(time.time())}'})
 rid,_=create_item(item); item['record_id']=rid
 local=json.loads(QUEUE.read_text()) if QUEUE.exists() else []; local.append(item); QUEUE.write_text(json.dumps(local,ensure_ascii=False,indent=2)); return item
def summary(x):return f"القسم: {kind_name(x.get('kind'))}\n\n{x.get('main_text','')}\n\nالشرح: {x.get('explanation') or 'غير موجود'}\n\nالمصدر: {x.get('source') or 'غير محدد'}\n\nالموعد التالي: {x.get('scheduled_date') or 'غير محدد'} — {x.get('publish_time') or ''}"

def send_preview(x):
 output=ROOT/f'preview_{int(time.time())}.png'
 render_card(x.get('kind','qa'),x.get('main_text',''),x.get('explanation',''),x.get('source',''),output)
 url=upload_public(output);x['preview_url']=url
 markup={'inline_keyboard':[[{'text':'✅ اعتماد وحفظ','callback_data':'upload_save'},{'text':'✏️ تعديل','callback_data':'upload_edit'}],[{'text':'❌ رفض','callback_data':'cancel'}]]}
 api('sendPhoto',chat_id=ADMIN_CHAT_ID,photo=url,caption='معاينة الكادر الذي سيُنشر. راجع النص كاملًا قبل الحفظ.',reply_markup=json.dumps(markup,ensure_ascii=False))

def send_contents(filter_status=None):
 items=list_items(); items=[x for x in items if not filter_status or x.get('airtable_status')==filter_status]
 if not items:send('لا يوجد محتوى بهذا التصنيف.',home());return
 groups={'quran':[],'hadith':[],'qa':[]}
 for x in items:groups.setdefault(x.get('kind','qa'),[]).append(x)
 chunks=[]
 for k in ('quran','hadith','qa'):
  if groups[k]:chunks.append('【'+kind_name(k)+'】\n'+'\n'.join(f'{i+1}. {(x.get("main_text") or "")[:120]} — {x.get("airtable_status") or "بدون حالة"}' for i,x in enumerate(groups[k])))
 send('📚 محتوى القاعدة\n\n'+'\n\n'.join(chunks),home())

def schedule_text():
 try:return json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else {'slots':[{'time':'09:00','kind':'quran'},{'time':'20:00','kind':'hadith'}]}
 except:return {'slots':[]}
def download_photo(m):
 photos=m.get('photo') or []
 if not photos:return None
 p=api('getFile',file_id=photos[-1]['file_id'])['result']['file_path']
 with urllib.request.urlopen(f'https://api.telegram.org/file/bot{TOKEN}/{p}') as r:return r.read()
def handle_upload(x):
 if not x.get('main_text'):send('لم أستطع استخراج نص واضح. أرسل النص أو صورة أوضح.',cancel());return
 if not x.get('explanation'):
  save_state({'step':'upload_optional_explanation','pending':x});send('هل يوجد تفسير أو شرح؟ أرسله الآن، أو اضغط «بدون شرح» للانتقال إلى معاينة الصورة.',{'inline_keyboard':[[{'text':'✅ بدون شرح — معاينة','callback_data':'upload_no_explanation'}],[{'text':'❌ إلغاء','callback_data':'cancel'}]]});return
 save_state({'step':'upload_confirm','pending':x});send_preview(x);save_state({'step':'upload_confirm','pending':x})
def send_publish_items(kind):
 items=[x for x in list_items(kind) if x.get('airtable_status') not in ('تم النشر','published')]
 if not items:send(f'لا يوجد محتوى في قسم {kind_name(kind)}.',home());return
 rows=[]
 for i,x in enumerate(items):rows.append([{'text':f'{i+1}. {(x.get("main_text") or "")[:45]}','callback_data':f'pick|{kind}|{x.get("record_id")}'}])
 rows.append([{'text':'❌ إلغاء','callback_data':'cancel'}]);send(f'اختر محتوى {kind_name(kind)} للنشر:',{'inline_keyboard':rows})
def process_message(m):
 if (m.get('chat') or {}).get('id')!=ADMIN_CHAT_ID:return
 text=(m.get('text') or '').strip(); s=state()
 if text in ('/start','/menu','القائمة'):save_state({});send('اختر العملية:',home());return
 if text=='⬆️ تحميل محتوى':save_state({'step':'upload_kind'});send('اختر القسم الذي سيُحفظ فيه المحتوى:',sections('upload'));return
 if text=='📤 نشر محتوى':save_state({'step':'publish_kind'});send('اختر القسم الذي تريد النشر منه:',sections('publish'));return
 if text=='📚 القاعدة':send_contents();return
 if text=='⏳ للمراجعة':send_contents('بانتظار المراجعة');return
 if text=='🗓 محتوى اليوم':
  today=date.today().isoformat(); items=[x for x in list_items() if x.get('scheduled_date')==today]
  send('🗓 محتوى اليوم:\n\n'+('\n'.join(f'{i+1}. {kind_name(x.get("kind"))} — {(x.get("main_text") or "")[:120]}' for i,x in enumerate(items)) if items else 'لا يوجد محتوى مجدول اليوم.'),home());return
 if text=='⏰ المواعيد':
  slots=schedule_text().get('slots',[]); save_state({'step':'schedule_count'})
  send('⏰ المواعيد الحالية:\n'+('\n'.join(f'{s.get("time")} — {kind_name(s.get("kind"))}' for s in slots) if slots else 'لا توجد')+'\n\nأرسل عدد المواعيد الجديد (مثال: 2) أو اضغط إلغاء.',cancel());return
 if text=='❌ إلغاء':save_state({});send('تم الإلغاء.',home());return
 if s.get('step')=='schedule_count':
  try:n=int(text)
  except:n=0
  if not 1<=n<=4:send('اكتب رقمًا من 1 إلى 4.',cancel());return
  save_state({'step':'schedule_times','count':n});send(f'أرسل {n} وقتًا مفصولًا بفاصلة، مثال: 09:00, 20:00',cancel());return
 if s.get('step')=='schedule_times':
  times=[v.strip() for v in text.replace('،',',').split(',') if v.strip()]
  if len(times)!=s.get('count') or any(len(v)!=5 or v[2]!=':' for v in times):send('صيغة الوقت يجب أن تكون HH:MM وبنفس العدد.',cancel());return
  save_state({'step':'schedule_kinds','times':times,'count':s['count']});send('أرسل الأقسام بنفس الترتيب: قرآن, حديث, سؤال وجواب',cancel());return
 if s.get('step')=='schedule_kinds':
  vals=[]
  for v in text.replace('،',',').split(','):
   vals.append('quran' if 'قر' in v else 'hadith' if 'حد' in v else 'qa' if 'سؤال' in v or 'جواب' in v else '')
  if len(vals)!=s.get('count') or any(not v for v in vals):send('اكتب قرآن أو حديث أو سؤال وجواب لكل موعد.',cancel());return
  CONFIG.write_text(json.dumps({'slots':[{'time':t,'kind':k} for t,k in zip(s['times'],vals)]},ensure_ascii=False,indent=2),encoding='utf-8');save_state({});send('✅ تم حفظ المواعيد:\n'+'\n'.join(f'{t} — {kind_name(k)}' for t,k in zip(s['times'],vals)),home());return
 if s.get('step')=='upload_explanation':
  x=s.get('pending') or {};x['explanation']=text;save_state({'step':'upload_confirm','pending':x});send('راجع المحتوى قبل الحفظ في Airtable:\n\n'+summary(x),{'inline_keyboard':[[{'text':'✅ حفظ في القاعدة','callback_data':'upload_save'},{'text':'❌ إلغاء','callback_data':'cancel'}]]});return
 if s.get('step')=='upload_optional_explanation':
  x=s.get('pending') or {};x['explanation']=text;save_state({'step':'upload_confirm','pending':x});send_preview(x);save_state({'step':'upload_confirm','pending':x});return
 if s.get('step')=='upload_content':
  try:handle_upload(extract(text=text,expected_kind=s.get('kind')))
  except Exception as e:print('extract error',repr(e),flush=True);send('حدث خطأ في قراءة المحتوى. أرسله مرة أخرى.',cancel())
  return
 if m.get('photo') and s.get('step')=='upload_content':
  try:handle_upload(extract(text=m.get('caption'),image_bytes=download_photo(m),expected_kind=s.get('kind')))
  except Exception as e:print('photo error',repr(e),flush=True);send('تعذر قراءة الصورة.',cancel())
  return
def process_callback(u):
 c=u.get('callback_query');
 if not c or c.get('message',{}).get('chat',{}).get('id')!=ADMIN_CHAT_ID:return
 a=c.get('data','');api('answerCallbackQuery',callback_query_id=c['id'])
 if a=='cancel':save_state({});send('تم الإلغاء.',home());return
 if a.startswith('upload|'):
  kind=a.split('|')[1];save_state({'step':'upload_content','kind':kind});send(f'أرسل محتوى {kind_name(kind)} الآن نصًا أو صورة:',cancel());return
 if a.startswith('publish|'):
  send_publish_items(a.split('|')[1]);return
 if a=='upload_save':
  x=state().get('pending') or {};saved=save_item(x);save_state({});send('✅ تم اعتماد المحتوى وحفظه في Airtable.\n\nسيظهر الآن داخل «📤 نشر محتوى» لاختياره لاحقًا.',home());return
 if a=='upload_no_explanation':
  x=state().get('pending') or {};x['explanation']='';save_state({'step':'upload_confirm','pending':x});send_preview(x);save_state({'step':'upload_confirm','pending':x});return
 if a=='upload_edit':save_state({'step':'upload_content','kind':(state().get('pending') or {}).get('kind','qa')});send('أرسل النسخة المعدلة:',cancel());return
 if a.startswith('pick|'):
  _,kind,rid=a.split('|',2);x=next((x for x in list_items(kind) if x.get('record_id')==rid),None)
  if not x:send('تعذر العثور على المحتوى.',home());return
  save_state({'step':'publish_confirm','pending':x});send('معاينة المحتوى:\n\n'+summary(x),{'inline_keyboard':[[{'text':'🚀 نشر الآن','callback_data':'publish_now'},{'text':'⏰ النشر في الموعد التالي','callback_data':'publish_next'}],[{'text':'❌ إلغاء','callback_data':'cancel'}]]});return
 if a in ('publish_now','publish_next'):
  x=state().get('pending') or {}; output=ROOT/f'card_{x.get("record_id", int(time.time()))}.png'
  try:
   render_card(x.get('kind','qa'),x.get('main_text',''),x.get('explanation',''),x.get('source',''),output)
   image_url,video_url,results=publish_media_item(x,output,mode='shareNow' if a=='publish_now' else 'addToQueue')
   ok=[r['service'] for r in results if r.get('post')]
   skipped=[f"{r['service']}: {r['skipped']}" for r in results if r.get('skipped')]
   if ok:update_status(x,'تم النشر' if a=='publish_now' else 'مجدول')
   save_state({})
   msg=('✅ تم نشر الصورة والفيديو فعليًا الآن على: '+', '.join(ok) if a=='publish_now' else '⏰ تم جدولة الصورة والفيديو في Buffer على: '+', '.join(ok))
   if skipped:msg+='\n\nملاحظة: '+'؛ '.join(skipped)
   send(msg+'\n\nتم تجهيز نسخة الصورة ونسخة الفيديو العمودي 1080×1920.',home())
  except Exception as e:
   print('publish error',repr(e),flush=True);send('❌ لم يتم النشر. Buffer لم يؤكد العملية:\n'+str(e),home())
  return
def main():
 off=None
 while True:
  try:
   p={'timeout':25,'limit':20,'allowed_updates':json.dumps(['message','callback_query'])}
   if off is not None:p['offset']=off
   for u in api('getUpdates',**p).get('result',[]):
    off=u['update_id']+1
    if u.get('message'):process_message(u['message'])
    if u.get('callback_query'):process_callback(u)
  except Exception as e:print('polling error',e,flush=True);time.sleep(3)
if __name__=='__main__':main()
