#!/usr/bin/env python3
"""Verify that display-label projection preserves each series and its values."""
import argparse, concurrent.futures, importlib.util, json, math, re, time
import urllib.parse, urllib.request
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--url',default='http://127.0.0.1:18428');ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('generator',root/'charts/suse-observability-dashboards/tools/generate_dashboards.py')
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    g.stable_display_query=g.query
    jobs=[];now=int(time.time())-300  # Avoid comparing a still-ingesting final sample.
    for make in [g.application_dashboard,g.resource_dashboard,g.platform_dashboard,g.traefik_dashboard,g.harvester_dashboard]:
        d=make();variables=[v['perseslistvariable']['spec']['name'] for v in d['dashboard']['spec']['variables']]
        for panel,p in d['dashboard']['spec']['panels'].items():
            for q in p['spec'].get('queries',[]):
                q=q['spec']['plugin']['spec'];alias=q['alias'];expr=q['query']
                if '${' not in alias:continue
                for v in variables:expr=expr.replace('${'+v+'}','.*')
                for key,value in {'__rate_interval':'5m','__interval':'1m','__range':'1h'}.items():expr=expr.replace('${'+key+'}',value)
                jobs.append((d['name'],panel,alias,expr))
    # Reload to restore the production projection after preparing raw queries.
    spec.loader.exec_module(g)
    def fetch(expr):
        params={'query':expr,'start':now-3600,'end':now,'step':300}
        with urllib.request.urlopen(a.url+'/api/v1/query_range?'+urllib.parse.urlencode(params),timeout=90) as r: data=json.load(r)
        assert data['status']=='success',data
        return data['data']['result']
    def check(job):
        dashboard,panel,alias,expr=job
        result={'dashboard':dashboard,'panel':panel}
        try:
            rows=fetch(expr);expected={}
            for row in rows:
                name=re.sub(r'\$\{([^}]+)\}',lambda m:row['metric'].get(m[1],''),alias)
                assert name not in expected, 'Duplicate display identity: '+name
                expected[name]=row['values']
            projected=g.stable_display_query(alias,expr)['spec']['plugin']['spec']['query']
            actual={r['metric']['sre_series']:r['values'] for r in fetch(projected)}
            assert expected.keys()==actual.keys(),'Series identities differ'
            for name,values in expected.items():
                assert len(values)==len(actual[name]),'Sample counts differ'
                for (ta,va),(tb,vb) in zip(values,actual[name]):
                    x,y=float(va),float(vb)
                    assert ta==tb and (math.isclose(x,y,rel_tol=1e-12,abs_tol=1e-12) or (math.isnan(x) and math.isnan(y))), 'Value changed: '+name
            result.update(status='success',series=len(rows),samples=sum(map(len,expected.values())))
        except Exception as e:result.update(status='error',error=str(e))
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results=list(ex.map(check,jobs))
    errors=[r for r in results if r['status']!='success']
    Path(a.output).write_text(json.dumps({'checked_at':now,'results':results},indent=2))
    print(json.dumps({'queries':len(results),'errors':errors,'series':sum(r.get('series',0) for r in results),'samples':sum(r.get('samples',0) for r in results)}))
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
