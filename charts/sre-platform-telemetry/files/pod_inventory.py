#!/usr/bin/env python3
"""Bounded, read-only Pod spec inventory; exposes no annotations, env or credentials."""
import json,math,os,re,ssl,time,threading,urllib.parse,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
SA=Path('/var/run/secrets/kubernetes.io/serviceaccount')
API='https://'+os.environ.get('KUBERNETES_SERVICE_HOST','kubernetes.default.svc')+':'+os.environ.get('KUBERNETES_SERVICE_PORT','443')

state={'text':'','success':False,'last':0};lock=threading.Lock()
def quantity(value):
 m=re.fullmatch(r'([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)([A-Za-z]*)',str(value))
 if not m:raise ValueError('Invalid Kubernetes quantity')
 v,u=m.groups();powers={'':1,'n':1e-9,'u':1e-6,'m':1e-3,'k':1e3,'K':1e3,'M':1e6,'G':1e9,'T':1e12,'P':1e15,'E':1e18,'Ki':1024,'Mi':1024**2,'Gi':1024**3,'Ti':1024**4,'Pi':1024**5,'Ei':1024**6}
 n=float(v)*powers[u]
 if not math.isfinite(n) or n<0:raise ValueError('Invalid quantity')
 return n
def refresh():
 lines=[];token='';count=0;seen=0
 context=ssl.create_default_context(cafile=str(SA/'ca.crt'))
 while True:
  query=urllib.parse.urlencode({'limit':500,'continue':token})
  req=urllib.request.Request(API+'/api/v1/pods?'+query,headers={'Authorization':'Bearer '+(SA/'token').read_text().strip()})
  with urllib.request.urlopen(req,context=context,timeout=10) as r:page=json.load(r)
  seen+=len(page['items'])
  if seen>100000:raise ValueError('Pod inventory safety cap exceeded')
  for pod in page['items']:
   if pod.get('status',{}).get('phase') not in ['Running','Pending']:continue
   count+=1
   statuses={s['name']:s for s in pod.get('status',{}).get('containerStatuses',[])}
   for c in pod['spec']['containers']:
    labels={'namespace':pod['metadata']['namespace'],'pod_name':pod['metadata']['name'],'container':c['name']}
    lab=','.join(k+'='+json.dumps(v) for k,v in labels.items())
    running=int('running' in statuses.get(c['name'],{}).get('state',{}))
    lines.append('sre_pod_container_running{'+lab+'} '+str(running))
    for section,suffix in [('requests','requested'),('limits','limit')]:
     for resource,value in c.get('resources',{}).get(section,{}).items():
      if resource in ['cpu','memory']:lines.append('sre_pod_container_'+resource+'_'+suffix+'{'+lab+'} '+str(quantity(value)))
  token=page.get('metadata',{}).get('continue','')
  if not token:break
 return '\n'.join(lines)+'\nsre_pod_inventory_pods '+str(count)+'\n'
def loop():
 while True:
  try:
   text=refresh()
   with lock:state.update(text=text,success=True,last=time.time())
  except Exception as e:
   with lock:state.update(text='',success=False)
   print('Pod inventory failed: '+type(e).__name__,flush=True)
  time.sleep(30)
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  with lock:s=dict(state)
  fresh=s['success'] and time.time()-s['last']<90
  if self.path=='/health':body=b'ok\n' if fresh else b'inventory unavailable\n';code=200 if fresh else 503
  elif self.path=='/metrics':body=((s['text'] if fresh else '')+'sre_pod_inventory_success '+str(int(fresh))+'\nsre_pod_inventory_last_success_timestamp_seconds '+str(s['last'])+'\n').encode();code=200
  else:body=b'not found\n';code=404
  self.send_response(code);self.send_header('Content-Type','text/plain; version=0.0.4');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
if __name__=='__main__':
 threading.Thread(target=loop,daemon=True).start();ThreadingHTTPServer(('127.0.0.1',9102),Handler).serve_forever()
