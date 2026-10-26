"""Mirror only the public KubeVirt CA, atomically; never log credentials or bodies."""
import os,ssl,json,urllib.request,time,pathlib,sys
SA=pathlib.Path('/var/run/secrets/kubernetes.io/serviceaccount')
def sync():
 ctx=ssl.create_default_context(cafile=str(SA/'ca.crt'))
 url='https://kubernetes.default.svc/api/v1/namespaces/'+os.environ['SOURCE_NAMESPACE']+'/configmaps/'+os.environ['SOURCE_CONFIGMAP']
 request=urllib.request.Request(url,headers={'Authorization':'Bearer '+(SA/'token').read_text().strip()})
 with urllib.request.urlopen(request,context=ctx,timeout=15) as response:obj=json.load(response)
 bundle=obj['data']['ca-bundle']
 # Parse before replacing the trusted bundle; an invalid response preserves it.
 ssl.create_default_context(cadata=bundle)
 target=pathlib.Path('/kubevirt-ca/ca-bundle')
 if not target.exists() or target.read_text()!=bundle:
  tmp=target.with_suffix('.tmp');tmp.write_text(bundle);tmp.chmod(0o644);tmp.replace(target)
  print('Public KubeVirt CA updated',flush=True)
if __name__=='__main__':
 while True:
  try:sync()
  except Exception as error:
   print('CA sync failed: '+type(error).__name__,flush=True)
   if '--once' in sys.argv:raise SystemExit(1)
  if '--once' in sys.argv:break
  time.sleep(60)
