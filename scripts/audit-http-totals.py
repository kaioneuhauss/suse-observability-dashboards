#!/usr/bin/env python3
"""Read-only invariant check: period totals must not depend on chart resolution."""
import argparse
import concurrent.futures
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--url', default='http://127.0.0.1:18428')
p.add_argument('--output', required=True)
p.add_argument('--native', action='store_true', help='Validate using the native SUSE API and its interval expansion')
p.add_argument('--service-token-env', default='')
p.add_argument('--hours', type=int, default=6)
a = p.parse_args()
end = int(time.time()) // 900 * 900
start = end - a.hours * 3600
root = Path(__file__).resolve().parents[1] / 'components/suse-observability-content/dashboards'
jobs = []
for slug in ['applications', 'traefik']:
    doc = json.loads((root / (slug + '.json')).read_text())
    for key, panel in doc['dashboard']['spec']['panels'].items():
        for index, query in enumerate(panel['spec'].get('queries', [])):
            expr = query['spec']['plugin']['spec']['query']
            if 'range_sum(' in expr:
                expr = re.sub(r'\$\{(?!__interval\})[^}]+\}', '.*', expr)
                jobs.extend((slug, key, index, step, expr) for step in [60, 300, 900])

def run(job):
    slug, key, index, step, expr = job
    if not a.native: expr = expr.replace('${__interval}', f'{step}s')
    params = {'query': expr, 'start': start, 'end': end, 'step': step}
    prefix = '/api/metrics' if a.native else '/api/v1'
    headers = {'X-API-Key': os.environ[a.service_token_env]} if a.service_token_env else {}
    request = urllib.request.Request(a.url.rstrip('/') + prefix + '/query_range?' + urllib.parse.urlencode(params), headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response:
        data = json.load(response)
    if data.get('status') != 'success':
        raise RuntimeError(data)
    rows = data['data']['result']
    values = {json.dumps(row['metric'], sort_keys=True): float(row['values'][-1][1]) for row in rows}
    return {'dashboard': slug, 'panel': key, 'query': index, 'step': step, 'values': values}

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    rows = list(pool.map(run, jobs))
checks = []
for base in rows:
    if base['step'] != 60:
        continue
    others = [r for r in rows if (r['dashboard'], r['panel'], r['query']) == (base['dashboard'], base['panel'], base['query'])]
    # Small tolerance handles floating point accumulation, not skipped time windows.
    passed = all(r['values'].keys() == base['values'].keys() and all(math.isclose(v, r['values'][k], rel_tol=1e-6, abs_tol=1e-6) for k, v in base['values'].items()) for r in others)
    checks.append({'dashboard': base['dashboard'], 'panel': base['panel'], 'passed': passed, 'series': len(base['values'])})
for step in [60, 300, 900]:
    total = next(r for r in rows if r['dashboard'] == 'applications' and r['panel'] == 'requests1h' and r['step'] == step)
    routes = next(r for r in rows if r['dashboard'] == 'applications' and r['panel'] == 'routeTotals' and r['step'] == step)
    expected, observed = sum(total['values'].values()), sum(routes['values'].values())
    checks.append({'dashboard': 'applications', 'panel': 'route sum equals request total', 'step': step, 'passed': math.isclose(expected, observed, abs_tol=max(1, len(routes['values']))), 'expected': expected, 'observed': observed})
Path(a.output).write_text(json.dumps({'start': start, 'end': end, 'checks': checks, 'results': rows}, indent=2) + '\n')
print(json.dumps({'queries': len(rows), 'checks': len(checks), 'failed': sum(not c['passed'] for c in checks)}))
for check in checks:
    if not check['passed']:
        print(json.dumps(check))
raise SystemExit(any(not c['passed'] for c in checks))
