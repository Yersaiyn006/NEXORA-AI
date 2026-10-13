from pathlib import Path
import tempfile
import atexit
PROJECT_ROOT = Path(__file__).resolve().parent.parent
QA_DIRECTORY = tempfile.TemporaryDirectory(prefix="nexora-synthetic-qa-")
atexit.register(QA_DIRECTORY.cleanup)
"""Official SDK against local synthetic HTTP transport, not a real Gemini model."""
import os,sys,json,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['DJANGO_SECRET_KEY']='isolated-audit-test-key';os.environ['NEXORA_AI_ENABLED']='true';os.environ['GEMINI_API_KEY']='synthetic-key';os.environ['NEXORA_DATABASE_PATH']=str(Path(QA_DIRECTORY.name) / 'audit.sqlite3');sys.path.insert(0, str(PROJECT_ROOT))
import django;django.setup()
from django.core.management import call_command
from django.test import override_settings
from core.models import Business
from assistant_ai.models import Conversation
from assistant_ai.universal_engine import respond
from google import genai
from google.genai import types
call_command('migrate',verbosity=0)
b=Business.objects.create(name='Synthetic SDK QA');chat=Conversation.objects.create(business=b)
mode='ok';requests=[];payloads=[]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  requests.append(mode);payloads.append(body)
  if mode=='timeout':
   time.sleep(.2);return
  if mode=='429':code=429;body={'error':{'code':429,'message':'synthetic quota error','status':'RESOURCE_EXHAUSTED'}}
  elif mode=='malformed':code=200;body={'candidates':[]}
  else:code=200;body={'candidates':[{'content':{'role':'model','parts':[{'text':'Синтетический транспортный ответ'}]},'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':11,'candidatesTokenCount':7,'totalTokenCount':18}}
  self.send_response(code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(body).encode())
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();original=genai.Client

def local_client(*,api_key,http_options):
 return original(api_key=api_key,http_options=types.HttpOptions(base_url=f'http://127.0.0.1:{server.server_port}',timeout=http_options.timeout,retry_options=http_options.retry_options, client_args={'trust_env': False}, async_client_args={'trust_env': False}))
report=[]
try:
 for case in ('ok','429','malformed','timeout'):
  mode=case;before=len(requests)
  with override_settings(NEXORA_AI_TIMEOUT_MS=50 if case=='timeout' else 1000), patch('google.genai.Client',side_effect=local_client):
   result=respond(chat,'Расскажи о компании')
  report.append({'case':case,'source':result.source,'tokens':result.tokens_used,'http_attempts':len(requests)-before})
 assert report[0]['source']=='gemini' and report[0]['tokens']==18
 assert all(row['http_attempts']==1 for row in report)
 assert all(row['source']=='fallback' for row in report[1:])
 assert 'systemInstruction' in payloads[0]
 print(json.dumps({'transport':'local synthetic HTTP','actual_gemini_calls':0,'cases':report},indent=2))
finally:server.shutdown();server.server_close()
