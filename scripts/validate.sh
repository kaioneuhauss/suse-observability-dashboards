#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
for pair in 'sre-platform-telemetry:cluster' 'suse-observability-dashboards:dashboards' 'suse-observability-monitors:monitors'; do
  chart="${pair%%:*}"
  values="${pair##*:}"
  helm lint "charts/$chart" -f "config/$values.values.yaml"
  helm template test "charts/$chart" -n suse-observability -f "config/$values.values.yaml" > /dev/null
done
python3 - <<'PY'
import ast,json,yaml,subprocess
from pathlib import Path
root=Path.cwd()
for p in list(root.glob('scripts/*.py'))+list(root.glob('charts/*/tools/*.py'))+list(root.glob('charts/*/files/*.py')):ast.parse(p.read_text(),filename=str(p))
for p in root.rglob('*.schema.json'):json.loads(p.read_text())
for p in root.glob('config/*.yaml'):yaml.safe_load(p.read_text())
rules=json.loads((root/'alerts/catalog.json').read_text());assert len(rules)==len({r['slug'] for r in rules})==24
assert json.loads((root/'charts/suse-observability-monitors/files/catalog.json').read_text())==rules
monitor_render=subprocess.check_output(['helm','template','test','charts/suse-observability-monitors','-f','config/monitors.values.yaml'],text=True)
monitor_cm=next(x for x in yaml.safe_load_all(monitor_render) if x and x['kind']=='ConfigMap')
assert {'apply_monitors.py','catalog.json'} <= set(monitor_cm['data'])
assert len(monitor_cm['data'])==len(rules)+2
for rule in rules:
 p=root/'charts/suse-observability-monitors/monitors'/(rule['slug']+'.sty')
 data=yaml.safe_load(p.read_text().replace('{{ get "urn:stackpack:common:monitor-function:threshold" }}','threshold'))
 assert data['nodes'][0]['arguments']['metric']['query']==rule['query']
for p in root.glob('charts/suse-observability-dashboards/dashboards/*.yaml'):
 d=yaml.safe_load(p.read_text())['dashboard']['spec'];seen=[]
 for grid in d['layouts']:
  for item in grid['spec']['items']:seen.append(item['content']['$ref'].split('/')[-1])
 assert set(seen)==set(d['panels']) and len(seen)==len(set(seen)),p
 for panel in d['panels'].values():assert panel['spec']['display']['description']
 for v in d['variables']:assert v['perseslistvariable']['spec']['customAllValue']=='.*'
small=subprocess.run(['helm','template','test','charts/sre-platform-telemetry','-f','config/cluster.values.yaml','--set','vmagent.queueMaxDiskMiB=256'],capture_output=True)
assert small.returncode!=0,'Invalid undersized queue unexpectedly accepted'
rendered=subprocess.check_output(['helm','template','test','charts/sre-platform-telemetry','-f','config/cluster.values.yaml'],text=True)
for obj in yaml.safe_load_all(rendered):
 if not obj or obj.get('kind') not in ('Deployment','DaemonSet'):continue
 for container in obj['spec']['template']['spec']['containers']:
  for probe in ('readinessProbe','livenessProbe','startupProbe'):
   assert container.get(probe,{}).get('httpGet',{}).get('path')!='/metrics', 'Metrics response must not be used as an HTTP health probe'
print('Syntax, 24 native monitors, panel references, filter defaults and invalid-queue rejection: OK')
PY
