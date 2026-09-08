#!/usr/bin/env python3
"""Merge a reviewed HelmChartConfig overlay; preserve all existing settings and protect the backup."""
import argparse,json,os,subprocess,tempfile
from pathlib import Path
import yaml

def merge(a,b):
    for k,v in b.items():
        if isinstance(v,dict) and isinstance(a.get(k),dict):merge(a[k],v)
        else:a[k]=v
    return a

def main():
    a=argparse.ArgumentParser();a.add_argument('--kubeconfig',required=True);a.add_argument('--context',required=True);a.add_argument('--overlay',required=True);a.add_argument('--backup-dir',required=True);a.add_argument('--namespace',default='kube-system');a.add_argument('--name',default='rke2-traefik');a.add_argument('--apply',action='store_true',help='Patch live object only; its owning controller can revert it');a.add_argument('--output',help='Write merged HelmChartConfig for the persistent RKE2 manifest source');p=a.parse_args()
    base=['--kubeconfig',p.kubeconfig,'--context',p.context,'-n',p.namespace]
    raw=subprocess.check_output(['kubectl','get',*base,'helmchartconfig',p.name,'-o','json']);obj=json.loads(raw)
    overlay=yaml.safe_load(Path(p.overlay).read_text());old=yaml.safe_load(obj['spec'].get('valuesContent','')) or {}
    dest=Path(p.backup_dir);dest.mkdir(mode=0o700,parents=True,exist_ok=True);os.chmod(dest,0o700)
    backup=dest/f"{p.context}-{p.name}-{obj['metadata']['resourceVersion']}.json"
    if backup.exists():
        if backup.read_bytes()!=raw:raise RuntimeError('Backup exists with different contents')
    else:
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(raw)
    new=yaml.safe_dump(merge(old,overlay),sort_keys=False)
    if p.output:
        manifest={'apiVersion':obj['apiVersion'],'kind':obj['kind'],'metadata':{'name':p.name,'namespace':p.namespace},'spec':dict(obj['spec'],valuesContent=new)}
        out=Path(p.output);out.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:yaml.safe_dump(manifest,f,sort_keys=False)
    patch=[{'op':'test','path':'/metadata/resourceVersion','value':obj['metadata']['resourceVersion']},{'op':'add','path':'/spec/valuesContent','value':new}]
    with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
        json.dump(patch,f);f.flush()
        cmd=['kubectl','patch',*base,'helmchartconfig',p.name,'--type=json','--patch-file',f.name]
        if not p.apply:cmd+=['--dry-run=server']
        subprocess.run(cmd,check=True)
    print(('Applied' if p.apply else 'Validated only')+' overlay keys: '+', '.join(overlay)+'. Backup: '+str(backup))
if __name__=='__main__':main()
