#!/usr/bin/env python3
"""Read-only VM Import Controller inventory. No source credentials or messages exported."""
import datetime
import http.server
import json
import math
import os
from pathlib import Path
import ssl
import threading
import time
import urllib.parse
import urllib.request

API = 'https://kubernetes.default.svc/apis/migration.harvesterhci.io/v1beta1/virtualmachineimports'
SA = Path('/var/run/secrets/kubernetes.io/serviceaccount')
PHASES = {'sourceReady', 'disksExported', 'diskImageSubmitted', 'diskImagesReady', 'diskImageFailed', 'virtualMachineCreated', 'virtualMachineRunning', 'virtualMachineImportValid', 'virtualMachineImportInvalid', 'VMMigrationFailed'}
FAILURES = {'diskImageFailed', 'virtualMachineImportInvalid', 'VMMigrationFailed'}
FAILURE_CONDITIONS = {'VMExportFailed', 'VirtualMachineImageFailed'}
ALLOWED_CONDITIONS = {'VMShutdownGuest', 'VMPoweringOff', 'VMPoweredOff', 'VMExported', 'VirtualMachineImageSubmitted', 'VirtualMachineImageReady', 'VirtualMachineImageFailed', 'VMExportFailed'}
SOURCE_KINDS = {'VmwareSource', 'OpenstackSource', 'OvaSource'}


def timestamp(value):
    try:
        return datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, AttributeError, TypeError):
        return None


def numeric(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number >= 0 else None
    except (ValueError, TypeError):
        return None


def sample(name, labels, value):
    # JSON string escaping is compatible with Prometheus label quoting for these fields.
    encoded = ','.join(f'{key}={json.dumps(str(value), ensure_ascii=False)}' for key, value in sorted(labels.items()))
    return f'{name}{{{encoded}}} {value:.17g}\n'


def true_condition(conditions, name):
    return next((c for c in conditions if c.get('type') == name and c.get('status') == 'True'), None)


def build_metrics(objects, now):
    lines = []
    for obj in objects:
        metadata, status = obj.get('metadata', {}), obj.get('status') or {}
        phase = status.get('importStatus', '')
        phase = phase if phase in PHASES else ('pending' if not phase else 'unknown')
        disks = status.get('diskImportStatus') or []
        conditions = status.get('importConditions') or []
        all_conditions = conditions + [c for d in disks for c in (d.get('diskConditions') or [])]
        if phase == 'virtualMachineRunning':
            outcome = 'succeeded'
        elif phase in FAILURES or any(c.get('type') in FAILURE_CONDITIONS and c.get('status') == 'True' for c in all_conditions):
            outcome = 'failed'
        elif phase == 'unknown':
            outcome = 'unknown'
        else:
            outcome = 'active'
        source = (obj.get('spec', {}).get('sourceCluster') or {}).get('kind', 'unknown')
        source = next((kind for kind in SOURCE_KINDS if kind.lower() == source.lower()), 'unknown')
        labels = {'namespace': metadata.get('namespace', ''), 'import_name': metadata.get('name', ''), 'target_vm': status.get('importedVirtualMachineName', ''), 'source_kind': source}
        lines.append(sample('harvester_import_info', dict(labels, phase=phase, outcome=outcome), 1))
        created = timestamp(metadata.get('creationTimestamp'))
        if created is not None:
            lines.append(sample('harvester_import_created_timestamp_seconds', labels, created))
            if outcome == 'active':
                lines.append(sample('harvester_import_active_age_seconds', labels, max(0, now-created)))
        condition_times = [timestamp(c.get('lastTransitionTime') or c.get('lastUpdateTime')) for c in all_conditions]
        condition_times = [value for value in condition_times if value is not None]
        if condition_times:
            lines.append(sample('harvester_import_last_condition_timestamp_seconds', labels, max(condition_times)))
        ready = [d for d in disks if true_condition(d.get('diskConditions') or [], 'VirtualMachineImageReady')]
        failed = [d for d in disks if not true_condition(d.get('diskConditions') or [], 'VirtualMachineImageReady') and true_condition(d.get('diskConditions') or [], 'VirtualMachineImageFailed')]
        for state, subset in [('total', disks), ('ready', ready), ('failed', failed)]:
            lines.append(sample('harvester_import_disks', dict(labels, state=state), len(subset)))
            sizes = [numeric(d.get('diskSize')) for d in subset]
            # Unknown size must never be silently coerced to zero.
            if all(value is not None for value in sizes):
                lines.append(sample('harvester_import_disk_capacity_bytes', dict(labels, state=state), sum(sizes)))
        exported = true_condition(conditions, 'VMExported')
        powered_off = true_condition(conditions, 'VMPoweredOff')
        if exported and powered_off:
            start = timestamp(powered_off.get('lastTransitionTime'))
            end = timestamp(exported.get('lastTransitionTime'))
            if start is not None and end is not None and end >= start:
                lines.append(sample('harvester_import_stage_duration_seconds', dict(labels, stage='poweroff_to_export'), end-start))
        starts, ends = [], []
        for disk in disks:
            cs = disk.get('diskConditions') or []
            for condition, target in [('VirtualMachineImageSubmitted', starts), ('VirtualMachineImageReady', ends)]:
                c = true_condition(cs, condition)
                value = timestamp(c.get('lastTransitionTime')) if c else None
                if value is not None:
                    target.append(value)
        if disks and len(starts) == len(disks) and len(ends) == len(disks) and max(ends) >= min(starts):
            lines.append(sample('harvester_import_stage_duration_seconds', dict(labels, stage='images_submitted_to_ready'), max(ends)-min(starts)))
    return ''.join(lines)


def list_imports(fetch=None):
    context = ssl.create_default_context(cafile=str(SA/'ca.crt')) if fetch is None else None
    def request(params):
        url = API + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + (SA/'token').read_text().strip()})
        with urllib.request.urlopen(req, context=context, timeout=15) as response:
            return json.load(response)
    fetch = fetch or request
    objects, continuation = [], ''
    while True:
        params = {'limit': 500}
        if continuation:
            params['continue'] = continuation
        page = fetch(params)
        objects.extend(page['items'])
        continuation = page.get('metadata', {}).get('continue', '')
        if not continuation:
            return objects


class Snapshot:
    def __init__(self, interval):
        self.interval = interval
        self.lock = threading.Lock()
        self.body, self.last_success, self.ok = '', 0, False

    def update(self, objects, now):
        body = build_metrics(objects, now)
        with self.lock:
            self.body, self.last_success, self.ok = body, now, True

    def fail(self):
        with self.lock:
            self.ok = False

    def metrics(self, now):
        with self.lock:
            fresh = self.ok and now-self.last_success <= max(90, 3*self.interval)
            header = sample('harvester_import_inventory_up', {}, int(fresh))
            header += sample('harvester_import_inventory_last_success_timestamp_seconds', {}, self.last_success)
            return header + (self.body if fresh else ''), fresh


def main():
    interval = max(30, int(os.getenv('POLL_INTERVAL_SECONDS', '30')))
    state = Snapshot(interval)
    def poll():
        while True:
            try:
                state.update(list_imports(), time.time())
            except Exception as error:
                state.fail()
                # Never print API responses, source specs, credentials or error messages.
                print('Import inventory poll failed: ' + type(error).__name__, flush=True)
            time.sleep(interval)
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body, ready = state.metrics(time.time())
            if self.path == '/health':
                self.send_response(200 if ready else 503)
                self.end_headers()
                return
            if self.path != '/metrics':
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
            self.end_headers()
            self.wfile.write(body.encode())
        def log_message(self, *_args):
            pass
    threading.Thread(target=poll, daemon=True).start()
    http.server.ThreadingHTTPServer(('127.0.0.1', 9103), Handler).serve_forever()


if __name__ == '__main__':
    main()
