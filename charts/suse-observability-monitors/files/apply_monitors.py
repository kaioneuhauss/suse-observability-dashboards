#!/usr/bin/env python3
"""Apply only the packaged monitors and verify their persisted definitions."""
import json
from pathlib import Path
import re
import subprocess

def run(*args):
    command = ['/work/sts']
    if Path('/ca/ca.crt').exists():
        command += ['--ca-cert-path', '/ca/ca.crt']
    result = subprocess.run(command + list(args), capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

def index(monitors):
    result = {}
    for monitor in monitors:
        result.setdefault(monitor['name'], []).append(monitor)
    return result

def main():
    catalog = json.loads(Path('/definitions/catalog.json').read_text())
    current = index(json.loads(run('monitor', 'list', '-o', 'json'))['monitors'])
    planned = []
    for rule in catalog:
        matches = current.get(rule['name'], [])
        if len(matches) > 1:
            raise RuntimeError('Duplicate monitor name; resolve before applying: ' + rule['name'])
        identifier = matches[0]['identifier'] if matches else 'urn:custom:monitor:sre-dashboards:' + rule['slug']
        if not identifier:
            raise RuntimeError('Existing monitor has no identifier: ' + rule['name'])
        source = Path('/definitions', rule['slug'] + '.sty').read_text()
        source, count = re.subn(r'^  identifier: .*$', '  identifier: ' + identifier, source, flags=re.M)
        if count != 1:
            raise RuntimeError('Expected exactly one packaged monitor identifier')
        planned.append((rule, identifier, source))
    # Preflight every identity before the first write. Never delete a monitor.
    for rule, identifier, source in planned:
        Path('/work/monitor.sty').write_text(source)
        run('monitor', 'apply', '--file', '/work/monitor.sty')
        print('Applied: ' + rule['name'], flush=True)
    persisted = index(json.loads(run('monitor', 'list', '-o', 'json'))['monitors'])
    report = []
    for rule, identifier, source in planned:
        matches = persisted.get(rule['name'], [])
        if len(matches) != 1:
            raise RuntimeError('Expected one persisted monitor: ' + rule['name'])
        actual = matches[0]
        arguments = {a['_type']: a['value'] for a in actual['arguments']}
        # urnTemplate and titleTemplate are distinct parameters of the same type.
        strings = [a['value'] for a in actual['arguments'] if a['_type'] == 'ArgumentStringVal']
        metric = arguments['ArgumentPromQLMetricVal']
        checks = {
            'identifier': actual['identifier'] == identifier,
            'query': metric['query'] == rule['query'],
            'unit': metric['unit'] == 'none',
            'alias': metric['aliasTemplate'] == rule['alias'],
            'threshold': arguments['ArgumentDoubleVal'] == rule['threshold'],
            'comparator': arguments['ArgumentComparatorWithoutEqualityVal'] == rule['comparator'],
            'severity': arguments['ArgumentFailingHealthStateVal'] == rule['severity'],
            'mapping': rule['urnTemplate'] in strings,
            'title': rule['titleTemplate'] in strings,
            'tags': set(actual['tags']) == {'sre-dashboards', 'platform'},
            'description': actual['description'] == rule['description'],
            'remediation': actual['remediationHint'] == rule['remediation'],
            'enabled': actual['status'] == ('ENABLED' if rule['enabled'] else 'DISABLED'),
            'interval': actual['intervalSeconds'] == 60,
        }
        if not all(checks.values()):
            raise RuntimeError('Persisted definition mismatch: ' + rule['name'] + ' ' + json.dumps(checks))
        report.append({'name': rule['name'], 'identifier': identifier, 'definition_match': True})
    print(json.dumps({'persisted_monitors': len(report), 'monitors': report}, ensure_ascii=False))

if __name__ == '__main__':
    main()
