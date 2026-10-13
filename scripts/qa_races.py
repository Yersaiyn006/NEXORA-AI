from pathlib import Path
import tempfile
import atexit
PROJECT_ROOT = Path(__file__).resolve().parent.parent
QA_DIRECTORY = tempfile.TemporaryDirectory(prefix="nexora-synthetic-qa-")
atexit.register(QA_DIRECTORY.cleanup)
import os,sys,uuid,json,concurrent.futures,threading
from datetime import timedelta
os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['DJANGO_SECRET_KEY']='isolated-audit-test-key';os.environ['NEXORA_AI_ENABLED']='false';os.environ['NEXORA_DATABASE_PATH']=str(Path(QA_DIRECTORY.name) / 'audit.sqlite3');sys.path.insert(0, str(PROJECT_ROOT))
import django;django.setup()
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.test import Client,override_settings
from django.db import close_old_connections
from django.utils import timezone
from core.models import Business,Membership,BusinessInvitation
from core.launch_views import digest
from assistant_ai.models import Conversation,Lead
from assistant_ai.turns import process_turn,TurnError
from assistant_ai.universal_engine import Result
call_command('migrate',verbosity=0)
b=Business.objects.create(name='Parallel invitation')
token='synthetic-invitation-'+uuid.uuid4().hex
inv=BusinessInvitation.objects.create(business=b,email='synthetic@example.com',token_hash=digest(token),expires_at=timezone.now()+timedelta(days=1))

def accept(i):
 close_old_connections()
 try:return Client().post('/launch/invite/'+token+'/',{'username':f'parallel_owner_{i}','password':'RarePass991Audit!','password_repeat':'RarePass991Audit!'}).status_code
 finally:close_old_connections()
with override_settings(ALLOWED_HOSTS=['testserver']):
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:statuses=list(pool.map(accept,range(4)))
owner=get_user_model().objects.filter(memberships__business=b).get()
chat=Conversation.objects.create(business=b)
when=timezone.now()+timedelta(days=1)
leads=[Lead.objects.create(business=b,conversation=chat,status='new',requested_at=when) for _ in range(4)]

def confirm(lead):
 close_old_connections()
 try:
  client=Client();client.force_login(owner)
  return client.post(f'/studio/booking/{lead.pk}/',{'business':b.pk,'action':'confirmed'}).status_code
 finally:close_old_connections()
with override_settings(ALLOWED_HOSTS=['testserver']):
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:confirmstatuses=list(pool.map(confirm,leads))
entered=threading.Event();release=threading.Event();firstid=uuid.uuid4()

def model(*args):
 entered.set()
 assert release.wait(timeout=5)
 return Result('synthetic answer','gemini')
def first():
 close_old_connections()
 try:return process_turn(chat,'first turn',firstid,model).content
 finally:close_old_connections()
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
 future=pool.submit(first)
 assert entered.wait(timeout=5)
 try:process_turn(chat,'parallel turn',uuid.uuid4(),lambda *args:Result('unexpected','gemini'));busy=False
 except TurnError as e:busy=e.status==409
 release.set();first_answer=future.result(timeout=5)
report={'invitation_requests':4,'invitation_statuses':statuses,'owner_memberships':Membership.objects.filter(business=b,role='owner').count(),'invitation_used':BusinessInvitation.objects.get(pk=inv.pk).used_at is not None,'confirmation_requests':4,'confirmation_statuses':confirmstatuses,'confirmed_conflicting_leads':Lead.objects.filter(business=b,status='confirmed').count(),'parallel_chat_rejected':busy,'chat_messages':chat.messages.count(),'first_answer':first_answer,'real_provider_calls':0}
assert report['owner_memberships']==1 and statuses.count(302)==1
assert report['confirmed_conflicting_leads']==1
assert busy and chat.messages.count()==2
print(json.dumps(report,indent=2))
