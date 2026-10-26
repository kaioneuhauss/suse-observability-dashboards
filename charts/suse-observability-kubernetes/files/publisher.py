#!/usr/bin/env python3
"""Runs ONLY inside Helm publisher Jobs; no pip or local Python is required.

The ConfigMap is the complete set of permitted names. Never grants RBAC, never
reads Kubernetes Secrets via its API, never falls back to a local sts context.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request

ROOT = Path(os.environ.get('DEFINITIONS_DIR', '/definitions'))
WORK = Path(os.environ.get('WORK_DIR', '/work'))

class PublishError(RuntimeError):
    pass

def redact(text: str) -> str:
    for key in ('STS_CLI_SERVICE_TOKEN', 'STS_CLI_API_TOKEN'):
        value = os.environ.get(key, '')
        if value:
            text = text.replace(value, '[REDACTED]')
    return re.sub(r'svctok-[A-Za-z0-9._-]+', '[REDACTED]', text)

def log(message: str) -> None:
    print(redact(message), flush=True)

def prepare_cli() -> str:
    path = os.environ.get('CLI_PATH', '')
    if path:
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            raise PublishError('CLI_PATH nao e um binario executavel na imagem: ' + path)
        return path
    url = os.environ['CLI_DOWNLOAD_URL']
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise PublishError('O download da CLI exige HTTPS.')
    ca_path = os.environ.get('CA_PATH', '')
    context = ssl.create_default_context()
    if ca_path:
        context.load_verify_locations(cafile=ca_path)
    dest = WORK / 'sts.tgz'
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(url, context=context, timeout=60) as response, dest.open('wb') as stream:
        if urllib.parse.urlsplit(response.url).scheme != 'https':
            raise PublishError('Redirecionamento para download sem HTTPS recusado.')
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > 128 * 1024 * 1024:
                raise PublishError('Download da CLI excedeu 128 MiB.')
            digest.update(chunk)
            stream.write(chunk)
    expected = os.environ.get('CLI_SHA256', '')
    if expected and digest.hexdigest().lower() != expected.lower():
        raise PublishError('SHA256 da CLI nao confere. Nenhuma operacao na API executada.')
    if not expected:
        log('[AVISO] Download TLS validado, mas CLI_SHA256 nao definido. Em producao prefira imagem preconstruida fixada por digest.')
    with tarfile.open(dest, 'r:gz') as archive:
        candidates = [m for m in archive.getmembers() if m.isfile() and Path(m.name).name == 'sts']
        if len(candidates) != 1 or candidates[0].size > 192 * 1024 * 1024:
            raise PublishError('Arquivo da CLI sem exatamente um binario sts valido.')
        member = archive.extractfile(candidates[0])
        if member is None:
            raise PublishError('Nao foi possivel ler o binario sts.')
        binary = WORK / 'sts'
        with binary.open('wb') as target:
            while chunk := member.read(1024 * 1024):
                target.write(chunk)
    binary.chmod(0o755)
    dest.unlink()
    return str(binary)

class CLI:
    def __init__(self, binary: str):
        self.binary = binary
    def run(self, *args: str, json_output: bool = True):
        command = [self.binary, '--config', str(WORK / 'isolated-cli-config.yaml')]
        ca = os.environ.get('CA_PATH', '')
        if ca:
            command += ['--ca-cert-path', ca]
        command += list(args)
        if json_output:
            command += ['--output', 'json', '--no-color']
        # Auth isolation: an explicit empty config plus the supplied token and URL.
        env = os.environ.copy()
        for key in ('STS_CLI_API_TOKEN', 'STS_API_TOKEN', 'STS_API_KEY', 'STS_CLI_CONTEXT'):
            env.pop(key, None)
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    check=False, timeout=90, env=env)
        except subprocess.TimeoutExpired as exc:
            raise PublishError('Timeout da CLI; confira estado da API antes de repetir a operacao.') from exc
        if result.returncode:
            details = redact((result.stderr or result.stdout).strip())[-3000:]
            note = ''
            if '403' in details or 'Forbidden' in details:
                note = ('\n403: confira URL, permissoes e o Service Token do Secret. '
                        'Para dashboards use a MESMA credencial proprietaria; '
                        'mesma role ou nome semelhante de token nao comprovam propriedade. '
                        'Nenhuma tentativa de elevar privilegios sera feita.')
            raise PublishError('sts ' + ' '.join(args[:2]) + ' falhou: ' + details + note)
        if not json_output:
            return result.stdout
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise PublishError('A CLI nao retornou JSON valido; interrompido sem tentar interpretar tabela.') from exc

def listed(cli: CLI, kind: str) -> list[dict]:
    obj = cli.run(kind, 'list')
    field = 'dashboards' if kind == 'dashboard' else 'monitors'
    if not isinstance(obj, dict) or not isinstance(obj.get(field), list):
        raise PublishError('Formato inesperado em sts ' + kind + ' list: esperado ' + field)
    if not all(isinstance(item, dict) for item in obj[field]):
        raise PublishError('Lista retornada pela CLI possui objeto invalido.')
    return obj[field]

def exact_match(objects: list[dict], name: str):
    matches = [o for o in objects if o.get('name') == name]
    if len(matches) > 1:
        raise PublishError('Nome duplicado; resolva manualmente antes de continuar: ' + name)
    return matches[0] if matches else None

def numeric_id(obj: dict) -> str:
    val = str(obj.get('id', ''))
    if not re.fullmatch('[0-9]+', val) or int(val) <= 0:
        raise PublishError('Objeto sem ID numerico valido.')
    return val

def check_dashboard_identity(obj: dict) -> None:
    if not str(obj.get('identifier', '')).startswith('urn:custom:dashboard:'):
        raise PublishError('Recusado dashboard nao-customizado com o mesmo nome: ' + str(obj.get('name')))

def dashboard_payload(obj: dict) -> dict:
    """Select only the writable schema; IDs and server metadata aren't reapplied."""
    if not isinstance(obj, dict) or not isinstance(obj.get('dashboard'), dict):
        raise PublishError('Resposta sem definicao completa do dashboard.')
    result = {key: obj[key] for key in ('name', 'description', 'scope', 'dashboard') if key in obj}
    if not result.get('name'):
        raise PublishError('Dashboard sem nome.')
    return result

def normalized_dashboard(obj: dict) -> dict:
    p = json.loads(json.dumps(dashboard_payload(obj)))
    p.setdefault('description', '')
    dash = p['dashboard']
    # Server-assigned Perses name/version/timestamps aren't desired configuration.
    meta = dash.get('metadata', {})
    dash['metadata'] = {'project': meta['project']} if 'project' in meta else {}
    project = dash['metadata'].get('project')
    if isinstance(project, str):
        try: dash['metadata']['project'] = json.loads(project)
        except json.JSONDecodeError: pass
    # v2.10.2 omits empty queries of Markdown panels. Do not drop other fields.
    for panel in dash.get('spec', {}).get('panels', {}).values():
        spec = panel.get('spec', {})
        if spec.get('queries') == []:
            spec.pop('queries')
    # CLI input unions and the API output use equivalent, different wrappers.
    def canonical(value):
        if isinstance(value, list):
            return [canonical(v) for v in value]
        if isinstance(value, dict):
            wrappers = {'perseslistvariable', 'persestextvariable',
                        'perseslistvariabledefaultsinglevalue', 'perseslistvariabledefaultslicevalues'}
            populated = {k:v for k,v in value.items() if not (k in wrappers and v is None)}
            if len(populated) == 1 and next(iter(populated)) in wrappers:
                return canonical(next(iter(populated.values())))
            return {k: canonical(v) for k, v in value.items()}
        return value
    return canonical(p)

def validate_dashboard(obj):
    data = normalized_dashboard(obj)['dashboard']['spec']
    panels = data.get('panels', {})
    used = set()
    for layout in data.get('layouts', []):
        positions = []
        for item in layout['spec']['items']:
            if any(type(item.get(k)) is not int for k in ('x', 'y', 'width', 'height')):
                raise PublishError('Every panel must have integer x/y/width/height coordinates.')
            x, y, w, h = (item[k] for k in ('x', 'y', 'width', 'height'))
            if min(x, y) < 0 or min(w, h) <= 0 or x + w > 24:
                raise PublishError('Panel outside the 24-column grid.')
            ref = item['content']['$ref'].removeprefix('#/spec/panels/')
            if ref not in panels or ref in used:
                raise PublishError('Missing or repeated panel reference: ' + ref)
            used.add(ref)
            for a, b, c, d in positions:
                if x < a+c and a < x+w and y < b+d and b < y+h:
                    raise PublishError('Overlapping dashboard panels: ' + obj['name'])
            positions.append((x,y,w,h))
    if used != set(panels):
        raise PublishError('Dashboard has panels missing from its layout.')

def first_difference(left, right, path='dashboard'):
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                return path + '.' + key + ' (missing field)'
            diff = first_difference(left[key], right[key], path + '.' + key)
            if diff: return diff
    elif isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right): return path + ' (different list size)'
        for i, (a,b) in enumerate(zip(left,right)):
            diff = first_difference(a,b,path + '[' + str(i) + ']')
            if diff: return diff
    elif left != right:
        return path + ' (different value)'
    return ''

def sync_dashboards(cli, definitions, action, strategy):
    if not isinstance(definitions, list) or not definitions:
        raise PublishError('The dashboard selection cannot be empty.')
    names = set()
    existing = listed(cli, 'dashboard')
    for desired in definitions:
        validate_dashboard(desired)
        name = desired['name']
        if name in names: raise PublishError('Duplicate dashboard name: ' + name)
        names.add(name)
        old = exact_match(existing, name)
        if old:
            check_dashboard_identity(old)
            numeric_id(old)
    for desired in definitions:
        sync_dashboard(cli, desired, action, strategy)
    log(json.dumps({'action': action, 'verified_dashboards': len(definitions)}))

def describe_dashboard(cli: CLI, obj: dict) -> dict:
    data = cli.run('dashboard', 'describe', '--id', numeric_id(obj))
    if not isinstance(data, dict) or not isinstance(data.get('data'), dict):
        raise PublishError('Esperado {data: dashboard} em sts dashboard describe 3.3.6.')
    return dashboard_payload(data['data'])

def write_yaml_json(name: str, value: dict) -> Path:
    # JSON is valid YAML, but sts 3.3.6 requires the .yaml extension.
    p = WORK / name
    p.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    return p

def sync_dashboard(cli: CLI, desired: dict, action: str, strategy: str) -> None:
    desired = dashboard_payload(desired)
    name = desired['name']
    old = exact_match(listed(cli, 'dashboard'), name)
    if old:
        check_dashboard_identity(old)
        numeric_id(old)
    if action == 'plan':
        log('[PLAN] dashboard ' + name + (' existente ID=' + numeric_id(old) if old else ' ausente'))
        return
    if action == 'delete':
        if old:
            cli.run('dashboard', 'delete', '--id', numeric_id(old))
        if exact_match(listed(cli, 'dashboard'), name):
            raise PublishError('Dashboard permanece apos delete: ' + name)
        log('[OK] dashboard ausente: ' + name)
        return
    previous = describe_dashboard(cli, old) if old else None
    if previous and normalized_dashboard(previous) == normalized_dashboard(desired):
        log('[OK] dashboard sem mudancas: ' + name + ' ID=' + numeric_id(old))
        return
    if previous:
        write_yaml_json('backup-dashboard.yaml', previous)
        log('[INFO] Backup temporario /work/backup-dashboard.yaml; nao substitui exportacao externa.')
    desired_file = write_yaml_json('dashboard.yaml', desired)
    removed = False
    if old:
        if strategy == 'patch':
            write_yaml_json('dashboard.yaml', dict(desired, id=int(numeric_id(old))))
        elif strategy == 'replace':
            # A 403 exits BEFORE create; it never creates a duplicate as a workaround.
            cli.run('dashboard', 'delete', '--id', numeric_id(old))
            removed = True
        else:
            raise PublishError('updateStrategy deve ser patch ou replace.')
    try:
        cli.run('dashboard', 'apply', '--file', str(desired_file))
        new = exact_match(listed(cli, 'dashboard'), name)
        if not new:
            raise PublishError('Dashboard nao encontrado apos apply.')
        check_dashboard_identity(new)
        actual = describe_dashboard(cli, new)
        if normalized_dashboard(actual) != normalized_dashboard(desired):
            raise PublishError(first_difference(normalized_dashboard(desired), normalized_dashboard(actual)) + ': Dashboard persistido difere do arquivo. '
                               'Com CLI/base legada e strategy=patch, revise strategy=replace; '
                               'o Job nao apaga automaticamente como fallback.')
    except PublishError:
        # Best-effort restoration only if we explicitly deleted and no new object exists.
        # A malformed/new partial object is not silently deleted.
        if removed and previous:
            try:
                if not exact_match(listed(cli, 'dashboard'), name):
                    restore = write_yaml_json('restore-dashboard.yaml', previous)
                    cli.run('dashboard', 'apply', '--file', str(restore))
                    log('[AVISO] Definicao anterior recriada; ID pode ter mudado. Falha original sera preservada.')
            except PublishError as error:
                log('[FALHA] Restauracao automatica nao concluida: ' + str(error))
        raise
    log('[OK] dashboard persistido e conferido: ' + name + ' ID=' + numeric_id(new))

def verify_monitor(actual: dict, rule: dict, identifier: str) -> bool:
    arguments = {a['_type']: a['value'] for a in actual.get('arguments', [])}
    strings = [a['value'] for a in actual.get('arguments', []) if a['_type'] == 'ArgumentStringVal']
    metric = arguments.get('ArgumentPromQLMetricVal', {})
    checks = [actual.get('identifier') == identifier,
              metric.get('query') == rule['query'], metric.get('unit') == 'none',
              metric.get('aliasTemplate') == rule['alias'],
              arguments.get('ArgumentDoubleVal') == rule['threshold'],
              arguments.get('ArgumentComparatorWithoutEqualityVal') == rule['comparator'],
              arguments.get('ArgumentFailingHealthStateVal') == rule['severity'],
              rule['urnTemplate'] in strings, rule['titleTemplate'] in strings,
              set(actual.get('tags', [])) == set(rule['tags']),
              actual.get('description') == rule['description'],
              actual.get('remediationHint') == rule['remediation'],
              actual.get('status') == ('ENABLED' if rule['enabled'] else 'DISABLED'),
              actual.get('intervalSeconds') == 60]
    return all(checks)

def monitor_source(rule: dict) -> tuple[str, str]:
    slug = rule['slug']
    if not re.fullmatch(r'[a-z0-9-]+', slug):
        raise PublishError('Slug invalido no catalogo.')
    source = (ROOT / (slug + '.sty')).read_text(encoding='utf-8')
    matches = re.findall(r'^  identifier: (.*)$', source, flags=re.M)
    if len(matches) != 1:
        raise PublishError('Definicao deve ter exatamente um identifier: ' + slug)
    return source, matches[0].strip().strip('"\'')

def sync_monitors(cli: CLI, catalog: list[dict], action: str) -> None:
    objects = listed(cli, 'monitor')
    legacy_path = ROOT / 'legacy-identifiers.json'
    legacy = json.loads(legacy_path.read_text()) if legacy_path.exists() else {}
    planned = []
    seen = set()
    for rule in catalog:
        name = rule['name']
        if name in seen:
            raise PublishError('Catalogo com nome duplicado: ' + name)
        seen.add(name)
        source, packaged_identifier = monitor_source(rule)
        old = exact_match(objects, name)
        allowed = {packaged_identifier, *legacy.get(rule['slug'], [])}
        if old:
            numeric_id(old)
            # Accept the prior project tags for an in-place migration. Identity
            # must still match this catalog; a tag alone never grants ownership.
            old_tags = set(old.get('tags', []))
            project_tags = {'sre-dashboards', 'platform', 'dashboard-applications',
                            'dashboard-platform', 'dashboard-traefik',
                            'dashboard-resources', 'dashboard-harvester'}
            if old.get('identifier') not in allowed or 'sre-dashboards' not in old_tags or not old_tags <= project_tags:
                raise PublishError('Monitor com nome igual mas identifier/tags fora do catalogo: ' + name)
        ident = old['identifier'] if old else packaged_identifier
        planned.append((rule, old, ident, source))
    # All names/IDs checked BEFORE the first mutation.
    for rule, old, ident, source in planned:
        if action == 'plan':
            log('[PLAN] monitor ' + rule['name'] + (' ID=' + numeric_id(old) if old else ' ausente'))
        elif action == 'delete':
            if old:
                cli.run('monitor', 'delete', '--id', numeric_id(old))
                log('[OK] monitor removido: ' + rule['name'])
        elif old and verify_monitor(old, rule, ident):
            log('[OK] monitor sem mudancas: ' + rule['name'])
        else:
            source, count = re.subn(r'^  identifier: .*$', '  identifier: ' + ident, source, flags=re.M)
            if count != 1:
                raise PublishError('Identifier inesperado.')
            path = WORK / (rule['slug'] + '.sty')
            path.write_text(source, encoding='utf-8')
            cli.run('monitor', 'apply', '--file', str(path))
            log('[OK] monitor aplicado: ' + rule['name'])
    if action == 'plan':
        return
    current = listed(cli, 'monitor')
    for rule, old, ident, source in planned:
        found = exact_match(current, rule['name'])
        if action == 'delete':
            if found:
                raise PublishError('Monitor permanece apos delete: ' + rule['name'])
        elif not found or not verify_monitor(found, rule, ident):
            raise PublishError('Definicao persistida diferente do catalogo: ' + rule['name'])
    log(json.dumps({'action': action, 'verified_monitors': len(planned)}, ensure_ascii=False))

def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    action = os.environ.get('PUBLISH_ACTION', 'apply')
    if action not in ('apply', 'plan', 'delete'):
        raise PublishError('Acao desconhecida.')
    if action == 'delete' and os.environ.get('CONFIRM_DELETE') != 'DELETE_MANAGED_OBJECTS':
        raise PublishError('Delete exige confirmacao literal DELETE_MANAGED_OBJECTS.')
    if not os.environ.get('STS_CLI_SERVICE_TOKEN'):
        raise PublishError('Service Token ausente; revise auth.existingSecret e auth.serviceTokenKey.')
    url = os.environ.get('STS_CLI_URL', '')
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise PublishError('STS_CLI_URL deve ser HTTPS, sem credenciais na URL.')
    cli = CLI(prepare_cli())
    cli.run('version')
    kind = os.environ['PUBLISH_KIND']
    log('[INFO] Destino=' + url + ' tipo=' + kind + ' acao=' + action)
    if kind == 'dashboard':
        desired = json.loads((ROOT / 'dashboard.json').read_text(encoding='utf-8'))
        sync_dashboard(cli, desired, action, os.environ.get('UPDATE_STRATEGY', 'replace'))
    elif kind == 'dashboard-bundle':
        definitions = json.loads((ROOT / 'dashboards.json').read_text(encoding='utf-8'))['dashboards']
        sync_dashboards(cli, definitions, action, os.environ.get('UPDATE_STRATEGY', 'replace'))
    elif kind == 'monitor':
        catalog = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
        if not isinstance(catalog, list) or not catalog:
            raise PublishError('Catalogo vazio/invalido.')
        sync_monitors(cli, catalog, action)
    else:
        raise PublishError('Tipo de publicacao desconhecido.')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        log('[FALHA] ' + str(error))
        sys.exit(1)
