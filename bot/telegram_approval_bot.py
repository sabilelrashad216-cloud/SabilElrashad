import json, os, time, urllib.parse, urllib.request, urllib.error
from datetime import date, timedelta
from pathlib import Path
from quran_workflow.content_extract import extract
from quran_workflow.airtable_db import create_item, list_items, update_status
from quran_workflow.buffer_db import publish_media_item, upload_public
from render_card import render_card

TOKEN=os.environ['TELEGRAM_BOT_TOKEN']; ADMIN_CHAT_ID=int(os.environ.get('TELEGRAM_ADMIN_CHAT_ID','2021636669')); BASE=f'https://api.telegram.org/bot{TOKEN}/'
ROOT=Path(__file__).resolve().parent; STATE=ROOT/'bot_state.json'; QUEUE=ROOT/'manual_queue.json'; CONFIG=ROOT/'schedule_config.json'; PAGE_SIZE=10

def cleanup_file(file_path):
    try:
        if file_path:
            Path(file_path).unlink(missing_ok=True)
    except Exception as exc: print('cleanup error:',repr(exc),flush=True)

def read_json(path,default):
    try:
        if not path.exists(): return default
        with path.open(encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError, TypeError) as exc:
        print('json read error:',path,repr(exc),flush=True); return default

def write_json(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    try:
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(tmp,path)
    except OSError as exc:
        cleanup_file(tmp); print('json write error:',path,repr(exc),flush=True); raise

def api(method,**data):
    try:
        req=urllib.request.Request(BASE+method,data=urllib.parse.urlencode(data).encode(),method='POST')
        with urllib.request.urlopen(req,timeout=60) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as exc:
        body=exc.read().decode(errors='replace'); print('telegram HTTP error:',method,exc.code,body[-800:],flush=True); return {'ok':False,'description':body}
    except urllib.error.URLError as exc:
        print('telegram network error:',method,repr(exc),flush=True); return {'ok':False,'description':str(exc)}
    except Exception as exc:
        print('telegram api error:',method,repr(exc),flush=True); return {'ok':False,'description':str(exc)}

def send(text,markup=None):
    data={'chat_id':ADMIN_CHAT_ID,'text':text}
    if markup:data['reply_markup']=json.dumps(markup,ensure_ascii=False)
    return api('sendMessage',**data)

def home():return {'keyboard':[[{'text':'⬆️ تحميل محتوى'},{'text':'📤 نشر محتوى'}],[{'text':'⏰ المواعيد'},{'text':'🗓 محتوى اليوم'}],[{'text':'📚 القاعدة'},{'text':'⏳ للمراجعة'}]],'resize_keyboard':True,'is_persistent':True}
def inline_footer(back='home'):return [[{'text':'🔙 رجوع','callback_data':f'back|{back}'},{'text':'❌ إلغاء','callback_data':'cancel'}]]
def cancel(back='home'):return {'inline_keyboard':inline_footer(back)}
def sections(action):return {'inline_keyboard':[[{'text':'📖 قرآن','callback_data':f'{action}|quran'},{'text':'📜 حديث','callback_data':f'{action}|hadith'}],[{'text':'❓ سؤال وجواب','callback_data':f'{action}|qa'}]]+inline_footer('home')}
def state():return read_json(STATE,{})
def save_state(s):write_json(STATE,s)
def kind_name(k):return {'quran':'قرآن','hadith':'حديث','qa':'سؤال وجواب'}.get(k,k)

def next_slot(kind,items):
    cfg=read_json(CONFIG,{'slots':[]}); slots=cfg.get('slots') or [{'time':'09:00','kind':kind}]; start=date.today()+timedelta(days=1)
    for n in range(366):
        d=(start+timedelta(days=n)).isoformat()
        for slot in slots:
            if slot.get('kind') in (kind,'all') and not any(x.get('scheduled_date')==d and x.get('publish_time')==slot.get('time') for x in items): return d,slot.get('time','09:00')
    return start.isoformat(),slots[0].get('time','09:00')

def save_item(item):
    items=list_items(); kind=item.get('kind','qa'); d,t=next_slot(kind,items); item=dict(item); item.update({'kind':kind,'scheduled_date':item.get('scheduled_date') or d,'publish_time':item.get('publish_time') or t,'airtable_status':'معتمد','id':item.get('id') or f'content-{int(time.time())}'})
    rid,_=create_item(item); item['record_id']=rid; local=read_json(QUEUE,[]); local.append(item); write_json(QUEUE,local); return item

def summary(x):return f"القسم: {kind_name(x.get('kind'))}\n\n{x.get('main_text','')}\n\nالشرح: {x.get('explanation') or 'غير موجود'}\n\nالمصدر: {x.get('source') or 'غير محدد'}\n\nالموعد التالي: {x.get('scheduled_date') or 'غير محدد'} — {x.get('publish_time') or ''}"

def send_preview(x):
    output=ROOT/f'preview_{int(time.time())}.png'
    try:
        render_card(x.get('kind','qa'),x.get('main_text',''),x.get('explanation',''),x.get('source',''),output); url=upload_public(output); x['preview_url']=url
        markup={'inline_keyboard':[[{'text':'✅ اعتماد وحفظ','callback_data':'upload_save'},{'text':'✏️ تعديل','callback_data':'upload_edit'}]]+inline_footer('upload')}
        api('sendPhoto',chat_id=ADMIN_CHAT_ID,photo=url,caption='معاينة الكادر الذي سيُنشر. راجع النص كاملًا قبل الحفظ.',reply_markup=json.dumps(markup,ensure_ascii=False))
    finally: cleanup_file(output)

def database_menu():return {'inline_keyboard':[[{'text':'📖 القرآن الكريم','callback_data':'db|quran|all|0'}],[{'text':'📜 الأحاديث','callback_data':'db|hadith|all|0'}],[{'text':'❓ سؤال وجواب','callback_data':'db|qa|all|0'}],[{'text':'⏳ بانتظار المراجعة','callback_data':'db|all|بانتظار المراجعة|0'},{'text':'✅ المعتمد','callback_data':'db|all|معتمد|0'}],[{'text':'🗓 المجدول','callback_data':'db|all|مجدول|0'},{'text':'🚀 تم النشر','callback_data':'db|all|تم النشر|0'}]]+inline_footer('home')}

def send_contents(kind=None,status=None,page=0):
    items=list_items(kind if kind in ('quran','hadith','qa') else None); items=[x for x in items if not status or x.get('airtable_status')==status]; total=len(items); start=page*PAGE_SIZE; shown=items[start:start+PAGE_SIZE]
    if not shown:send('لا يوجد محتوى بهذا التصنيف.',database_menu());return
    text='📚 '+(kind_name(kind) if kind in ('quran','hadith','qa') else 'قاعدة المحتوى')+f' — صفحة {page+1}/{max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)}\n\n'+'\n'.join(f'{start+i+1}. {kind_name(x.get("kind"))} — {(x.get("main_text") or "")[:180]}\nالحالة: {x.get("airtable_status") or "غير محددة"}' for i,x in enumerate(shown))
    rows=[]
    if page>0: rows.append([{'text':'◀️ السابق','callback_data':f'db|{kind or "all"}|{status or "all"}|{page-1}'}])
    if start+PAGE_SIZE<total: rows.append([{'text':'▶️ التالي','callback_data':f'db|{kind or "all"}|{status or "all"}|{page+1}'}])
    rows+=inline_footer('database');send(text,{'inline_keyboard':rows})

def send_publish_items(kind,page=0):
    items=[x for x in list_items(kind) if x.get('airtable_status') not in ('تم النشر','published')]; total=len(items); start=page*PAGE_SIZE; shown=items[start:start+PAGE_SIZE]
    if not shown:send(f'لا يوجد محتوى معتمد في قسم {kind_name(kind)}.',home());return
    rows=[[{'text':f'{start+i+1}. {(x.get("main_text") or "")[:45]}','callback_data':f'pick|{kind}|{x.get("record_id")}'}] for i,x in enumerate(shown)]
    if page>0:rows.append([{'text':'◀️ السابق','callback_data':f'pubpage|{kind}|{page-1}'}])
    if start+PAGE_SIZE<total:rows.append([{'text':'▶️ التالي','callback_data':f'pubpage|{kind}|{page+1}'}])
    rows+=inline_footer('publish');send(f'اختر محتوى {kind_name(kind)} للنشر — صفحة {page+1}/{max(1,(total+PAGE_SIZE-1)//PAGE_SIZE)}:',{'inline_keyboard':rows})

def download_photo(m):
    photos=m.get('photo') or []
    if not photos:return None
    p=api('getFile',file_id=photos[-1]['file_id']).get('result',{}).get('file_path')
    if not p:raise RuntimeError('Telegram لم يعط مسار الصورة')
    with urllib.request.urlopen(f'https://api.telegram.org/file/bot{TOKEN}/{p}',timeout=60) as r:return r.read()

def handle_upload(x):
    if not x.get('main_text'):send('لم أستطع استخراج نص واضح. أرسل النص أو صورة أوضح.',cancel('upload'));return
    if not x.get('explanation'):
        save_state({'step':'upload_optional_explanation','pending':x});send('هل يوجد تفسير أو شرح؟ أرسله الآن، أو اضغط «بدون شرح» للانتقال إلى معاينة الصورة.',{'inline_keyboard':[[{'text':'✅ بدون شرح — معاينة','callback_data':'upload_no_explanation'}]]+inline_footer('upload')});return
    save_state({'step':'upload_confirm','pending':x});send_preview(x);save_state({'step':'upload_confirm','pending':x})

def process_message(m):
    incoming_chat=(m.get('chat') or {}).get('id')
    if incoming_chat!=ADMIN_CHAT_ID:
        print(f'ignored Telegram message from chat_id={incoming_chat}; expected configured admin chat',flush=True)
        return
    text=(m.get('text') or '').strip(); s=state()
    if text in ('/start','/menu','القائمة'):save_state({});send('اختر العملية:',home());return
    if text=='⬆️ تحميل محتوى':save_state({'step':'upload_kind'});send('اختر القسم الذي سيُحفظ فيه المحتوى:',sections('upload'));return
    if text=='📤 نشر محتوى':save_state({'step':'publish_kind'});send('اختر القسم الذي تريد النشر منه:',sections('publish'));return
    if text=='📚 القاعدة':send('اختر القسم أو حالة المحتوى:',database_menu());return
    if text=='⏳ للمراجعة':send_contents(status='بانتظار المراجعة');return
    if text=='🗓 محتوى اليوم':
        today=date.today().isoformat(); items=[x for x in list_items() if x.get('scheduled_date')==today];send('🗓 محتوى اليوم:\n\n'+('\n'.join(f'{i+1}. {kind_name(x.get("kind"))} — {(x.get("main_text") or "")[:120]}' for i,x in enumerate(items)) if items else 'لا يوجد محتوى مجدول اليوم.'),home());return
    if text=='⏰ المواعيد':
        cfg=read_json(CONFIG,{'slots':[{'time':'09:00','kind':'quran'},{'time':'20:00','kind':'hadith'}]});save_state({'step':'schedule_count'});send('⏰ المواعيد الحالية:\n'+'\n'.join(f'{x.get("time")} — {kind_name(x.get("kind"))}' for x in cfg.get('slots',[]))+'\n\nأرسل عدد المواعيد الجديد.',cancel('home'));return
    if text=='❌ إلغاء':save_state({});send('تم الإلغاء.',home());return
    if s.get('step')=='upload_optional_explanation':
        x=s.get('pending') or {};x['explanation']=text;save_state({'step':'upload_confirm','pending':x});send_preview(x);save_state({'step':'upload_confirm','pending':x});return
    if m.get('photo') and s.get('step')=='upload_content':
        try:handle_upload(extract(text=m.get('caption'),image_bytes=download_photo(m),expected_kind=s.get('kind')))
        except Exception as e:print('photo error',repr(e),flush=True);send('تعذر قراءة الصورة الآن. أرسل صورة أوضح أو النص كتابةً.',cancel('upload'))
        return
    if s.get('step')=='upload_content':
        try:handle_upload(extract(text=text,expected_kind=s.get('kind')))
        except Exception as e:print('extract error',repr(e),flush=True);send('حدث خطأ في قراءة المحتوى. أرسله مرة أخرى.',cancel('upload'))
        return
    if s.get('step')=='upload_explanation':
        x=s.get('pending') or {};x['explanation']=text;save_state({'step':'upload_confirm','pending':x});send_preview(x);return

def process_callback(u):
    c=u.get('callback_query');
    if not c or c.get('message',{}).get('chat',{}).get('id')!=ADMIN_CHAT_ID:return
    a=c.get('data','');api('answerCallbackQuery',callback_query_id=c['id'])
    if a=='cancel':save_state({});send('تم الإلغاء.',home());return
    if a.startswith('back|'):
        target=a.split('|',1)[1]
        if target=='upload':save_state({'step':'upload_kind'});send('اختر القسم:',sections('upload'))
        elif target=='publish':save_state({'step':'publish_kind'});send('اختر القسم:',sections('publish'))
        elif target=='database':send('اختر القسم أو الحالة:',database_menu())
        else:save_state({});send('القائمة الرئيسية:',home())
        return
    if a.startswith('upload|'):
        kind=a.split('|')[1];save_state({'step':'upload_content','kind':kind});send(f'أرسل محتوى {kind_name(kind)} الآن نصًا أو صورة:',cancel('upload'));return
    if a.startswith('publish|'):send_publish_items(a.split('|')[1],0);return
    if a.startswith('pubpage|'):
        _,kind,page=a.split('|');send_publish_items(kind,int(page));return
    if a.startswith('db|'):
        _,kind,status,page=a.split('|');send_contents(None if kind=='all' else kind,None if status=='all' else status,int(page));return
    if a=='upload_no_explanation':
        x=state().get('pending') or {};x['explanation']='';save_state({'step':'upload_confirm','pending':x});send_preview(x);save_state({'step':'upload_confirm','pending':x});return
    if a=='upload_save':
        x=state().get('pending') or {};save_item(x);save_state({});send('✅ تم اعتماد المحتوى وحفظه في Airtable. سيظهر الآن داخل «📤 نشر محتوى».',home());return
    if a=='upload_edit':save_state({'step':'upload_content','kind':(state().get('pending') or {}).get('kind','qa')});send('أرسل النسخة المعدلة:',cancel('upload'));return
    if a.startswith('pick|'):
        _,kind,rid=a.split('|',2);x=next((x for x in list_items(kind) if x.get('record_id')==rid),None)
        if not x:send('تعذر العثور على المحتوى.',home());return
        save_state({'step':'publish_confirm','pending':x});send('معاينة المحتوى:\n\n'+summary(x),{'inline_keyboard':[[{'text':'🚀 نشر الآن','callback_data':'publish_now'},{'text':'⏰ النشر في الموعد التالي','callback_data':'publish_next'}]]+inline_footer('publish')});return
    if a in ('publish_now','publish_next'):
        x=state().get('pending') or {};output=ROOT/f'card_{x.get("record_id",int(time.time()))}.png'
        try:
            render_card(x.get('kind','qa'),x.get('main_text',''),x.get('explanation',''),x.get('source',''),output)
            _,_,results=publish_media_item(x,output,mode='shareNow' if a=='publish_now' else 'addToQueue');ok=[r['service'] for r in results if r.get('post')]
            if ok:update_status(x,'تم النشر' if a=='publish_now' else 'مجدول')
            save_state({});send(('✅ تم النشر فعليًا: ' if a=='publish_now' else '⏰ تمت الجدولة: ')+', '.join(ok),home())
        except Exception as e:print('publish error',repr(e),flush=True);send('❌ لم يتم النشر؛ Buffer لم يؤكد العملية:\n'+str(e),home())
        finally:cleanup_file(output);cleanup_file(str(output).rsplit('.',1)[0]+'_short.mp4')
        return

def main():
    offset=None
    while True:
        try:
            params={'timeout':25,'limit':20,'allowed_updates':json.dumps(['message','callback_query'])}
            if offset is not None:params['offset']=offset
            for u in api('getUpdates',**params).get('result',[]):
                offset=u['update_id']+1
                if u.get('message'):process_message(u['message'])
                if u.get('callback_query'):process_callback(u)
        except Exception as exc:print('polling error:',repr(exc),flush=True);time.sleep(3)
if __name__=='__main__':main()
