from pathlib import Path
import tempfile
import atexit
PROJECT_ROOT = Path(__file__).resolve().parent.parent
QA_DIRECTORY = tempfile.TemporaryDirectory(prefix="nexora-synthetic-qa-")
atexit.register(QA_DIRECTORY.cleanup)
"""Synthetic file-SQLite concurrent requests; Gemini is disabled."""
import os,sys,json,uuid,time,statistics,collections,concurrent.futures
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
os.environ['DJANGO_SECRET_KEY']='isolated-audit-test-key'
os.environ['NEXORA_AI_ENABLED']='false'
os.environ['NEXORA_DATABASE_PATH']=str(Path(QA_DIRECTORY.name) / 'audit.sqlite3')
sys.path.insert(0, str(PROJECT_ROOT))
import django
django.setup()
from django.core.management import call_command
from django.test import Client,override_settings
from django.db import close_old_connections
from core.models import Business
from assistant_ai.models import Conversation,Message
call_command('migrate',verbosity=0)
b=Business.objects.create(name='Concurrency QA',slug='concurrency-qa',public_chat_enabled=True)

def send(i):
 close_old_connections();client=Client();start=time.monotonic()
 try:
  response=client.post('/chat/concurrency-qa/send/',{'message':f'Вопрос {i}','turn_id':str(uuid.uuid4())},REMOTE_ADDR=f'198.51.100.{i%200+1}')
  return response.status_code,round((time.monotonic()-start)*1000,2)
 except Exception as exc:return type(exc).__name__,round((time.monotonic()-start)*1000,2)
 finally:close_old_connections()

with override_settings(ALLOWED_HOSTS=['testserver'],NEXORA_PUBLIC_BUSINESS_PER_DAY=10000):
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(send,range(80)))
counts=collections.Counter(str(status) for status,_ in results);latencies=sorted(ms for _,ms in results)
chats=list(Conversation.objects.filter(business=b));pairs=[list(c.messages.values_list('role',flat=True)) for c in chats]
report={'database':'SQLite file','workers':8,'requests':80,'statuses':dict(counts),'latency_ms':{'median':round(statistics.median(latencies),2),'p95':latencies[int(len(latencies)*.95)-1]},'conversations':len(chats),'messages':Message.objects.filter(conversation__business=b).count(),'complete_pairs':sum(p.count('customer')==1 and p.count('assistant')==1 for p in pairs),'provider_calls':0}
assert counts == {'200': 80} and report['complete_pairs'] == 80
print(json.dumps(report,indent=2))
