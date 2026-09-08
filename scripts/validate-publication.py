#!/usr/bin/env python3
"""Check the Git index for private files, credential patterns and broken local docs links."""
from pathlib import Path
import os
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
tracked = subprocess.check_output(
    ['git', 'ls-files', '-z'], cwd=ROOT
).decode().split('\0')
tracked = {name for name in tracked if name}
errors = []
forbidden_prefixes = ('environments/', 'evidence/', 'config/local/', 'config/cliente/', '.venv/')
forbidden_files = {'AGENTS.md', 'docs/REFERENCIA.md', 'docs/VALIDACAO.md', 'docs/IMPLEMENTACAO.pt-BR.md'}
credential_patterns = [
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(r'\bgithub_pat_[A-Za-z0-9_]{30,}\b'),
    re.compile(r'\beyJ[A-Za-z0-9_-]{12,}\.eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]+'),
]
# Optional local-only pattern: avoid embedding customer identifiers in this script.
private_pattern = os.environ.get('PUBLICATION_PRIVATE_PATTERN')
private_environment = re.compile(private_pattern) if private_pattern else None

def headings(text):
    """GitHub-style anchors for the plain English headings used in this project."""
    values = set()
    seen = {}
    for heading in re.findall(r'^#{1,6}\s+(.+)$', text, re.M):
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        values.add(slug if count == 0 else f'{slug}-{count}')
    return values

for name in sorted(tracked):
    path = ROOT / name
    if (name.startswith(forbidden_prefixes) or name in forbidden_files
            or path.suffix.lower() in {'.docx', '.pem', '.key', '.token', '.kubeconfig'}
            or path.name == '.env' or path.name.startswith('.env.')):
        errors.append(f'Private/local file is tracked: {name}')
    # Inspect the exact staged content, not an unstaged working copy.
    data = subprocess.check_output(['git', 'show', f':{name}'], cwd=ROOT)
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        errors.append(f'Unexpected binary in source publication: {name}')
        continue
    if any(pattern.search(text) for pattern in credential_patterns):
        errors.append(f'Credential-like content in {name} (value withheld)')
    if private_environment and private_environment.search(text):
        errors.append(f'Private environment identifier in {name}')
    if path.suffix != '.md':
        continue
    prose = re.sub(r'```.*?```|~~~.*?~~~', '', text, flags=re.S)
    for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)', prose):
        parts = urlsplit(target)
        if parts.scheme or target.startswith('//'):
            continue
        destination = (path.parent / unquote(parts.path)).resolve() if parts.path else path
        try:
            relative = destination.relative_to(ROOT).as_posix()
        except ValueError:
            errors.append(f'Link escapes repository in {name}: {target}')
            continue
        if relative not in tracked:
            errors.append(f'Link target is not published in {name}: {target}')
        elif parts.fragment and destination.suffix == '.md':
            linked = subprocess.check_output(['git', 'show', f':{relative}'], cwd=ROOT).decode()
            if unquote(parts.fragment) not in headings(linked):
                errors.append(f'Missing heading anchor in {name}: {target}')

for error in errors:
    print(error, file=sys.stderr)
print(f'Publication check: {len(tracked)} tracked files, {len(errors)} problems')
sys.exit(bool(errors))
