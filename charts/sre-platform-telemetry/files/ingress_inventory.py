"""Expose exact Ingress -> Traefik backend identities, including named ports.

Read-only Kubernetes Ingress inventory. The SUSE Agent 1.5.32 reports port=0
for named ports, so its metric alone cannot construct these identities.
"""
import json, os, ssl, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT='/var/run/secrets/kubernetes.io/serviceaccount'
CONTEXT=ssl.create_default_context(cafile=ROOT+'/ca.crt')
URL='https://kubernetes.default.svc/apis/networking.k8s.io/v1/ingresses'
LOCK=threading.Lock(); ROWS=[]; LAST=0; SUCCESS=0

def esc(value):return str(value).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')

def collect():
    global ROWS,LAST,SUCCESS
    while True:
        try:
            with open(ROOT+'/token') as f:token=f.read().strip()
            request=urllib.request.Request(URL,headers={'Authorization':'Bearer '+token})
            with urllib.request.urlopen(request,context=CONTEXT,timeout=10) as response:data=json.load(response)
            rows=set()
            for ingress in data['items']:
                ns=ingress['metadata']['namespace']
                for rule in ingress['spec'].get('rules',[]):
                    for path in rule.get('http',{}).get('paths',[]):
                        backend=path.get('backend',{}).get('service')
                        if not backend:continue
                        port=backend['port'].get('name',backend['port'].get('number'))
                        if port is None:continue
                        name=backend['name'];identity=f'{ns}-{name}-{port}@kubernetes'
                        rows.add(f'sre_ingress_backend_info{{ingress_namespace="{esc(ns)}",backend="{esc(name)}",service="{esc(identity)}"}} 1')
            with LOCK:ROWS=sorted(rows);LAST=time.time();SUCCESS=1
        except Exception as error:
            with LOCK:SUCCESS=0
            # Avoid printing authorization headers or entire response bodies.
            print('Ingress inventory collection failed: '+type(error).__name__,flush=True)
        time.sleep(30)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ['/metrics','/health']:
            self.send_error(404);return
        with LOCK:
            rows=ROWS.copy() if time.time()-LAST<120 else []
            body='\n'.join(['# TYPE sre_ingress_backend_info gauge',*rows,
                f'sre_ingress_inventory_success {SUCCESS}',
                f'sre_ingress_inventory_last_success_timestamp_seconds {LAST}'])+'\n'
        self.send_response(200);self.send_header('Content-Type','text/plain; version=0.0.4');self.end_headers();self.wfile.write(body.encode())
    def log_message(self,*args):pass

if __name__=='__main__':
    threading.Thread(target=collect,daemon=True).start()
    HTTPServer(('127.0.0.1',9102),Handler).serve_forever()
