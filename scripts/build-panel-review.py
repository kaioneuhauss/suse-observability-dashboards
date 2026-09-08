#!/usr/bin/env python3
"""Summarize audit-queries.py results per panel; no additional network queries."""
import argparse
import csv
import json
from pathlib import Path
import yaml


def absence_hint(filename, key):
    if key == 'restarts':
        return 'No positive restart increase in the hour can leave this list empty. Confirm fresh inventory and collection first.'
    if key == 'etcdPeer':
        return 'A single-member etcd cluster has no peers. In a multi-member cluster, check peer histogram collection.'
    if key in ('ioPressure', 'memoryPressure'):
        return 'PSI requires kernel support and the optional collector. Unsupported kernels do not report this metric.'
    if key.startswith('pvc'):
        return 'Check namespace and volume mode. Block volumes and unmounted filesystems may have no kubelet filesystem statistics.'
    if key in ('cpuUseGauge', 'memUseGauge', 'memoryRisk', 'throttling', 'cpuReservation', 'cpuLimitTop', 'memLimitTop'):
        return 'A running pod and the relevant positive request or complete limit are required. Missing limits are listed separately.'
    if 'application' in filename or 'traefik' in filename:
        if key in ('tlsExpiry', 'openConnections'):
            return 'This panel covers the whole selected cluster. Check Traefik metric support and collection.'
        return 'Check selected application and traffic in the stated window. A response time is undefined without completed requests; verify fresh collection.'
    if 'harvester' in filename:
        return 'Guest use requires a running VM and fresh Guest Agent statistics. Host panels cover the whole selected Harvester cluster.'
    return 'Check selection, applicability, target health and sample age. An empty result is not proof of health or zero consumption.'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--audit-dir', type=Path, required=True)
    a = ap.parse_args()
    instant = json.loads((a.audit_dir / 'queries-instant.json').read_text())
    historical = json.loads((a.audit_dir / 'queries-range.json').read_text())
    chart = Path(__file__).resolve().parents[1] / 'charts/suse-observability-dashboards/dashboards'
    panels = []
    for path in sorted(chart.glob('*.yaml')):
        definition = yaml.safe_load(path.read_text())
        for key, panel in definition['dashboard']['spec']['panels'].items():
            spec = panel['spec']
            current = [r for r in instant['results'] if r['dashboard'] == path.name and r['panel'] == key]
            ranges = [r for r in historical['results'] if r['dashboard'] == path.name and r['panel'] == key]
            all_items = [r for r in current if all(v == '.*' for v in r['variables'].values())]
            errors = sum(r['status'] != 'success' or r.get('nonfinite_values', 0) > 0 for r in current + ranges)
            kind = spec['plugin']['kind']
            classification = 'explanation' if kind == 'Markdown' else 'error' if errors else 'data' if any(r.get('series', 0) for r in all_items) else 'empty: reviewed applicability'
            panels.append(dict(dashboard=definition['name'], key=key,
                title=spec['display']['name'], kind=kind, classification=classification,
                everything_series=';'.join(str(r.get('series', 0)) for r in all_items),
                instant_cases=len(current), instant_empty=sum(r.get('series') == 0 for r in current),
                range_cases=len(ranges), range_empty=sum(r.get('series') == 0 for r in ranges),
                errors=errors, description=spec['display']['description'],
                absence_interpretation='Explanatory text; no metric query.' if kind == 'Markdown' else absence_hint(path.name, key)))
    (a.audit_dir / 'panel-review.json').write_text(json.dumps(dict(
        checked_at=instant['checked_at'], filter='Everything plus discovered filter cases',
        limits='Query evidence and applicability review; graphical checks are recorded separately.', panels=panels), ensure_ascii=False, indent=2))
    with (a.audit_dir / 'panel-validation.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(panels[0])); writer.writeheader(); writer.writerows(panels)
    print(json.dumps({'panels': len(panels), 'errors': sum(p['errors'] for p in panels),
        'empty_in_everything': [p['key'] for p in panels if p['classification'].startswith('empty')]}))


if __name__ == '__main__':
    main()
