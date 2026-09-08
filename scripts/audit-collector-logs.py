#!/usr/bin/env python3
"""Read-only audit of every container in this chart's pods; no credentials exported."""
import argparse
import concurrent.futures
import datetime
import json
import re
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--kubeconfig', required=True)
p.add_argument('--context', required=True)
p.add_argument('--namespace', required=True)
p.add_argument('--since', default='10m')
p.add_argument('--output', required=True)
a = p.parse_args()
def kubectl(verb, *args):
    return subprocess.check_output(['kubectl', verb, '--kubeconfig', a.kubeconfig,
        '--context', a.context, '-n', a.namespace, '--request-timeout=30s', *args], text=True, timeout=40)
pods = json.loads(kubectl('get', 'pods', '-l',
    'app.kubernetes.io/name=sre-platform-telemetry', '-o', 'json'))['items']
def inspect(pair):
    pod, container = pair
    name = pod['metadata']['name']
    statuses = {c['name']: c for c in pod['status'].get('containerStatuses', [])}
    status = statuses.get(container['name'], {})
    row = dict(pod=name, node=pod['spec']['nodeName'], container=container['name'],
        phase=pod['status']['phase'], ready=status.get('ready', False),
        restarts=status.get('restartCount', 0), state=status.get('state'),
        readiness_probe=container.get('readinessProbe'))
    try:
        lines = kubectl('logs', name, '-c', container['name'], '--since='+a.since,
            '--timestamps=true').splitlines()
        errors = [line for line in lines if re.search(
            r'level=(?:ERROR|WARN)|\b(?:error|warn)\b|broken pipe|connection reset', line, re.I)]
        row.update(log_lines=len(lines), error_warning_lines=len(errors),
            connection_closed_lines=sum('broken pipe' in x or 'connection reset by peer' in x for x in errors),
            first_error=errors[0][:700] if errors else None,
            last_error=errors[-1][:700] if errors else None)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        row['audit_error'] = str(e)
    return row
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    rows = list(pool.map(inspect, [(pod, c) for pod in pods for c in pod['spec']['containers']]))
result = dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    context=a.context, namespace=a.namespace, window=a.since, pods=len(pods), containers=rows)
with open(a.output, 'w') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(json.dumps(dict(context=a.context, pods=len(pods), containers=len(rows),
    not_ready=sum(not x['ready'] for x in rows),
    error_warning_lines=sum(x.get('error_warning_lines', 0) for x in rows),
    audit_errors=sum('audit_error' in x for x in rows))))
raise SystemExit(not rows or any('audit_error' in x or not x['ready'] or x.get('error_warning_lines', 0) for x in rows))
