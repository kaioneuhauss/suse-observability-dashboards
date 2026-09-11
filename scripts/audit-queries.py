#!/usr/bin/env python3
"""Validate every panel using discovered live single-value filter paths.

Also checks parent+Everything paths, representative multiple selections and an
invalid cluster. Range mode covers Everything and each cluster, bounding load.
This is API evidence, not a GUI test or an exhaustive test of arbitrary subsets.
"""
import argparse,concurrent.futures,json,math,re,time,os,urllib.parse,urllib.request
from pathlib import Path
import yaml

def substitute(expr,values):
    for k,v in values.items():expr=expr.replace('${'+k+'}',json.dumps(v,ensure_ascii=False)[1:-1])
    if re.search(r'\$\{[^}]+\}',expr):raise ValueError('Unresolved variable: '+expr)
    return expr

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--url',default='http://127.0.0.1:18428');ap.add_argument('--output',required=True)
    ap.add_argument('--range',action='store_true');ap.add_argument('--hours',type=int,default=6);ap.add_argument('--workers',type=int,default=3)
    ap.add_argument('--api-prefix',default='/api/v1');ap.add_argument('--service-token-env',default='');a=ap.parse_args();now=int(time.time());jobs=[];coverage=[]
    def api(endpoint,params):
        url=a.url.rstrip('/')+a.api_prefix.rstrip('/')+'/'+endpoint+'?'+urllib.parse.urlencode(params,doseq=True)
        headers={'Authorization':'ApiKey '+os.environ[a.service_token_env]} if a.service_token_env else {}
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=90) as r:d=json.load(r)
        if d.get('status')!='success':raise RuntimeError(d)
        return d
    def values(spec,selected):
        matcher=substitute(spec['plugin']['spec']['matchers'][0],selected);label=spec['plugin']['spec']['labelName']
        data=api('query',{'query':matcher,'time':now})
        return sorted({r['metric'][label] for r in data['data']['result'] if r['metric'].get(label)})
    chart=Path(__file__).resolve().parents[1]/'charts/suse-observability-content/dashboards'
    for path in sorted(chart.glob('*.json')):
        doc=json.loads(path.read_text());specs=[v['perseslistvariable']['spec'] for v in doc['dashboard']['spec']['variables']]
        names=[s['name'] for s in specs];base=dict.fromkeys(names,'.*');scenarios={};choices=[]
        def keep(v):scenarios[json.dumps(v,sort_keys=True)]=v.copy()
        def walk(level,selected):
            keep(selected)
            if level==len(specs) or (a.range and level>0):return
            spec=specs[level];available=values(spec,selected)
            choices.append({'variable':spec['name'],'parents':selected.copy(),'options':available})
            if len(available)>1:
                multi=selected.copy();multi[spec['name']]='|'.join(re.escape(v) for v in available[:2]);keep(multi)
            for value in available:
                child=selected.copy();child[spec['name']]=re.escape(value);walk(level+1,child)
        walk(0,base)
        negative=base.copy();negative[names[0]]='__sre_nonexistent_cluster__';keep(negative)
        coverage.append({'dashboard':path.name,'scenarios':len(scenarios),'choices':choices})
        for selected in scenarios.values():
            replacements=dict(selected,__rate_interval='5m',__interval='5m',__range=f'{a.hours}h')
            for panelid,panel in doc['dashboard']['spec']['panels'].items():
                for qi,q in enumerate(panel['spec'].get('queries',[])):
                    expr=substitute(q['spec']['plugin']['spec']['query'],replacements)
                    jobs.append((path.name,panelid,qi,selected,expr))
    print('Discovered',len(jobs),'query/filter cases',flush=True)
    def execute(job):
        name,panel,qi,scenario,expr=job;params={'query':expr,'time':now};endpoint='query'
        if a.range or 'range_sum(' in expr:params={'query':expr,'start':now-a.hours*3600,'end':now,'step':60 if 'range_sum(' in expr else 300};endpoint='query_range'
        result={'dashboard':name,'panel':panel,'query_index':qi,'variables':scenario}
        try:
            d=api(endpoint,params);rows=d['data']['result']
            nums=[v[1] for row in rows for v in row.get('values',[row['value']] if 'value' in row else [])]
            result.update(status='success',series=len(rows),finite_values=sum(math.isfinite(float(v)) for v in nums))
            result['nonfinite_values']=len(nums)-result['finite_values']
            result['classification']='data' if rows else 'empty; applicability and collection must be reviewed'
        except Exception as e:result.update(status='error',error=str(e),query=expr)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:results=list(ex.map(execute,jobs))
    errors=[r for r in results if r['status']!='success']
    out={'checked_at':now,'mode':'range' if a.range else 'instant','hours':a.hours,'filter_coverage':coverage,'results':results,'limits':'API only; all live single-value paths, representative multi-selection, bounded time windows.'}
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps({'queries':len(results),'errors':len(errors),'empty':sum(r.get('series')==0 for r in results),'nonfinite_cases':sum(r.get('nonfinite_values',0)>0 for r in results)}))
    return bool(errors)
if __name__=='__main__':raise SystemExit(main())
