#!/usr/bin/env python3
"""Native SUSE dashboards. Formula contracts are documented in docs/metric-contracts.md.

Topics inspired by doccaz/harvester-extra-dashboards; no Grafana JSON is imported.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'components/suse-observability-content'
BASE = json.loads((ROOT / 'dashboards/harvester.json').read_text())
KEY = 'k8s_cluster_name,namespace,name'
VM = 'k8s_cluster_name=~"${vm_cluster}",namespace=~"${vm_namespace}",name=~"${vm_name}"'
CLUSTER = 'k8s_cluster_name=~"${vm_cluster}"'
ALIAS = '${k8s_cluster_name} · ${namespace} · ${name}'


def metric(name, selector=VM, extra=''):
    return f'{name}{{{selector}{"," + extra if extra else ""}}}'


def dedup(expression, keys=KEY):
    return f'max by ({keys}) ({expression})'


def vm_rate(name):
    return dedup(f'rate({metric(name)}[5m])')


RUNNING = dedup(metric('kubevirt_vmi_info', extra='phase="running"'))
VCPUS = ' * '.join(dedup(metric('kubevirt_vm_resource_requests', extra=f'resource="cpu",source="domain",unit="{unit}"')) for unit in ('cores', 'sockets', 'threads'))
CPU = f'100 * ({vm_rate("kubevirt_vmi_cpu_usage_seconds_total")}) / (({VCPUS}) > 0)'
MEM_USED = f'({dedup(metric("kubevirt_vmi_memory_available_bytes"))} - {dedup(metric("kubevirt_vmi_memory_usable_bytes"))})'
MEM = f'100 * {MEM_USED} / ({dedup(metric("kubevirt_vmi_memory_available_bytes"))} > 0)'
READY = f'100 * avg by ({KEY}) (max by ({KEY},id) (rate({metric("kubevirt_vmi_vcpu_delay_seconds_total")}[5m])))'
WAIT = f'100 * avg by ({KEY}) (max by ({KEY},id) (rate({metric("kubevirt_vmi_vcpu_wait_seconds_total")}[5m])))'


class Dashboard:
    def __init__(self, name, description, guide, variables=None):
        self.data = copy.deepcopy(BASE)
        self.data.update(name=name, description=description)
        self.spec = self.data['dashboard']['spec']
        self.spec['panels'] = {'guide': copy.deepcopy(BASE['dashboard']['spec']['panels']['guide'])}
        self.spec['panels']['guide']['spec']['display']['name'] = 'Read this dashboard'
        self.spec['panels']['guide']['spec']['plugin']['spec']['text'] = guide
        if variables is not None:
            self.spec['variables'] = variables
        self.items = [{'x': 0, 'y': 0, 'width': 24, 'height': 1, 'content': {'$ref': '#/spec/panels/guide'}}]
        self.x, self.y, self.row_height = 0, 1, 0

    def add(self, key, title, description, queries, unit='decimal', stat=False, width=12):
        panel = copy.deepcopy(BASE['dashboard']['spec']['panels']['runningCount' if stat else 'vmSampleAge'])
        panel['spec']['display'] = {'name': title, 'description': description + '\n\nWhen to investigate / alert coverage: Context for investigation; not a paging rule. Verify source health and sample coverage before acting.'}
        panel['spec'].pop('links', None)
        plugin = panel['spec']['plugin']['spec']
        if 'yAxis' in plugin: plugin['yAxis'].pop('label', None)
        if stat:
            plugin['format'] = {'decimalPlaces': 2, 'unit': unit}
        else:
            plugin['yAxis']['format'] = {'decimalPlaces': 2, 'unit': unit}
        panel['spec']['queries'] = [{'kind': 'TimeSeriesQuery', 'spec': {'plugin': {'kind': 'PrometheusTimeSeriesQuery', 'spec': {'query': q, 'alias': a}}}} for a, q in queries]
        self.spec['panels'][key] = panel
        height = 2 if stat else 3
        if self.x + width > 24:
            self.y += self.row_height
            self.x, self.row_height = 0, 0
        self.items.append({'x': self.x, 'y': self.y, 'width': width, 'height': height, 'content': {'$ref': '#/spec/panels/' + key}})
        self.x += width
        self.row_height = max(self.row_height, height)

    def save(self, slug):
        self.spec['layouts'][0]['spec']['items'] = self.items
        (ROOT / 'dashboards' / (slug + '.json')).write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + '\n')


def variable(name, title, label, matcher):
    result = copy.deepcopy(BASE['dashboard']['spec']['variables'][0])
    spec = result['perseslistvariable']['spec']
    spec['name'] = name
    spec['display']['name'] = title
    spec['plugin']['spec'] = {'labelName': label, 'matchers': [matcher]}
    return result


d = Dashboard('Virtualization · VM Contention', 'CPU scheduling, guest memory pressure and VM disk response.',
              '**Follow the bottleneck.** Compare CPU usage with scheduler wait, guest memory with swap/page faults, and VM disk latency with Longhorn latency. Windows are 5 minutes. Empty is not zero. VM statistics require a running VMI; guest memory statistics depend on the guest balloon driver and platform support. These panels do not change VM resources.')
d.add('cpuReady', 'Worst CPU scheduler wait · %', 'Mean run-queue delay across vCPUs, then worst selected VM. A scheduling-pressure analogue to CPU Ready; not VMware-identical accounting. No factor of 1000: KubeVirt exports seconds.', [('Worst VM', f'max({READY})')], 'percent', True, 8)
d.add('cpuUsage', 'Highest VM CPU use · %', 'Domain CPU seconds per second divided by configured cores × sockets × threads. Includes hypervisor/domain CPU accounting; inspect the time series before resizing.', [('Highest VM', f'max({CPU})')], 'percent', True, 8)
d.add('memoryUse', 'Highest guest memory use · %', '100 × (available - usable) / available. Usable corresponds to guest MemAvailable; reclaimable cache is not counted as used. Missing statistics remain empty.', [('Highest VM', f'max({MEM})')], 'percent', True, 8)
for key, title, query, desc in [('ready', 'CPU scheduler wait by VM · %', READY, 'Average per-vCPU scheduling delay over 5 minutes, deduplicated by VM and vCPU ID.'), ('cpu', 'CPU use by VM · %', CPU, 'CPU demand relative to configured VM topology, not Kubernetes CPU request.'), ('ioWait', 'vCPU I/O wait by VM · %', WAIT, 'Time blocked on I/O, distinct from runnable CPU scheduler delay.'), ('memory', 'Guest memory use by VM · %', MEM, 'Guest MemAvailable-based use; different from QEMU RSS and host RAM.')]:
    d.add(key, title, desc, [(ALIAS, query)], 'percent')
d.add('faults', 'Guest major page faults/s', 'Rate of major page faults; investigate together with swap activity and guest memory headroom.', [(ALIAS, vm_rate('kubevirt_vmi_memory_pgmajfault_total'))])
d.add('swap', 'Guest swap activity · estimated bytes/s', 'KubeVirt exposes cumulative swap traffic as gauges. Positive 5-minute delta / 300 estimates traffic; a guest reset may invalidate this window. Not a counter rate.', [(ALIAS + ' · ' + direction, dedup(f'clamp_min(delta({metric("kubevirt_vmi_memory_swap_" + direction + "_traffic_bytes")}[5m]),0) / 300')) for direction in ('in', 'out')], 'bytes/sec')
for direction in ('read', 'write'):
    latency = f'1000 * {dedup(f"rate({metric('kubevirt_vmi_storage_' + direction + '_times_seconds_total')}[5m])", KEY + ",drive")} / ({dedup(f"rate({metric('kubevirt_vmi_storage_iops_' + direction + '_total')}[5m])", KEY + ",drive")} > 0)'
    d.add(direction + 'Latency', f'VM disk {direction} latency · ms', 'Mean seconds spent on I/O divided by completed I/Os, converted to milliseconds. One series per VM disk. Idle disks have no mean latency and remain empty.', [(ALIAS + ' · ${drive}', latency)], 'milliseconds')
d.save('virtualization-contention')

d = Dashboard('Virtualization · Capacity & Sizing', 'Running allocation, host headroom and 24-hour VM demand.',
              '**Capacity is constrained by more than one resource.** The overview uses all running VMs in the selected cluster. CPU capacity means host logical CPUs, not physical cores. Memory headroom includes all host activity. The N-1 estimate only subtracts guest allocations from host total RAM; system overhead, storage placement and HA eligibility still need review. A single host has zero surviving capacity. 24-hour demand is advisory; newly collected data does not cover a complete day.', BASE['dashboard']['spec']['variables'][:1])
all_vm = VM.replace(',namespace=~"${vm_namespace}",name=~"${vm_name}"', '')
running = RUNNING.replace(VM, all_vm)
cpus = VCPUS.replace(VM, all_vm)
guest = dedup(metric('kubevirt_vm_resource_requests', all_vm, 'resource="memory",source="guest",unit="bytes"'))
allocated = f'sum by (k8s_cluster_name) (({guest}) and on ({KEY}) ({running}))'
host_total = 'label_replace(sum by (cluster_name) (max by (cluster_name,node) (node_memory_MemTotal_bytes{cluster_name=~"${vm_cluster}",job="sre-node"})),"k8s_cluster_name","$1","cluster_name","(.+)")'
host_largest = host_total.replace('sum by (cluster_name)', 'max by (cluster_name)', 1)
logical = 'label_replace(count by (cluster_name) (max by (cluster_name,node,cpu) (node_cpu_seconds_total{cluster_name=~"${vm_cluster}",job="sre-node",mode="idle"})),"k8s_cluster_name","$1","cluster_name","(.+)")'
d.add('allocatedCpu', 'Running VMs · configured vCPUs', 'Sum cores × sockets × threads for VMs with a currently running VMI. Stopped definitions are excluded.', [('${k8s_cluster_name}', f'sum by (k8s_cluster_name) (({cpus}) and on ({KEY}) ({running}))')], stat=True, width=8)
d.add('allocatedMemory', 'Running VMs · configured guest RAM', 'Configured guest RAM of running VMs, not used RAM, QEMU overhead or Kubernetes requests.', [('${k8s_cluster_name}', allocated)], 'bytes(IEC)', True, 8)
d.add('hostAvailable', 'Host memory available', 'MemAvailable from Linux includes reclaimable cache and reflects all host workloads. Use this before starting additional VMs.', [('${cluster_name}', 'sum by (cluster_name) (max by (cluster_name,node) (node_memory_MemAvailable_bytes{cluster_name=~"${vm_cluster}",job="sre-node"})) and on (cluster_name) (max by (cluster_name) (label_replace(up{k8s_cluster_name=~"${vm_cluster}",service_name="kubevirt-metrics"},"cluster_name","$1","k8s_cluster_name","(.+)")))')], 'bytes(IEC)', True, 8)
d.add('cpuRatio', 'Running vCPU / host logical CPU ratio', 'Configuration ratio, not utilization or an admission recommendation. Hyperthreading, CPU pinning and workload behavior affect usable capacity.', [('${k8s_cluster_name}', f'sum by (k8s_cluster_name) (({cpus}) and on ({KEY}) ({running})) / on (k8s_cluster_name) ({logical} > 0)')])
d.add('nMinusOne', 'N-1 guest-memory budget · upper bound', 'Total host RAM minus largest host RAM minus configured RAM of running VMs. Negative means guest allocation exceeds this upper bound. System overhead and usable allocatable memory are not deducted; positive does not certify HA or successful evacuation.', [('${k8s_cluster_name}', f'({host_total}) - on (k8s_cluster_name) ({host_largest}) - on (k8s_cluster_name) ({allocated})')], 'bytes(IEC)')
for key, title, expression, unit in [('cpuP95', 'VM CPU demand · p95 over 24h · cores', vm_rate('kubevirt_vmi_cpu_usage_seconds_total'), 'decimal'), ('memoryP95', 'Guest memory used · p95 over 24h', MEM_USED, 'bytes(IEC)')]:
    expression = expression.replace(VM, all_vm)
    d.add(key, title, '95th percentile of 5-minute sampled demand over the available part of 24 hours. No automatic size recommendation. Inspect peak demand, business cycles, telemetry gaps and resize events first. Only currently running VMs are shown.', [(ALIAS, f'quantile_over_time(0.95,({expression})[24h:5m]) and on ({KEY}) ({running})')], unit)
d.add('cpuPeak', 'VM CPU demand · max over 24h · cores', 'Maximum of 5-minute mean CPU demand in the available 24-hour history; shorter bursts can be hidden. Compare against p95.', [(ALIAS, f'max_over_time(({vm_rate("kubevirt_vmi_cpu_usage_seconds_total").replace(VM,all_vm)})[24h:5m]) and on ({KEY}) ({running})')])
d.add('coverage', 'CPU telemetry samples · trailing 24h', 'Count of raw CPU samples per current VM. At 30 seconds, a full uninterrupted day is approximately 2880 samples; verify cadence and restarts before treating p95 as a full-day estimate. This is coverage, not availability.', [(ALIAS, f'max by ({KEY}) (count_over_time({metric("kubevirt_vmi_cpu_usage_seconds_total",all_vm)}[24h])) and on ({KEY}) ({running})')])
d.save('virtualization-capacity')

variables = [variable('storage_cluster', 'Cluster', 'k8s_cluster_name', 'longhorn_volume_capacity_bytes'), variable('storage_volume', 'Volume', 'volume', 'longhorn_volume_capacity_bytes{k8s_cluster_name=~"${storage_cluster}"}')]
storage = 'k8s_cluster_name=~"${storage_cluster}",volume=~"${storage_volume}"'
storage_cluster = 'k8s_cluster_name=~"${storage_cluster}"'
volkeys = 'k8s_cluster_name,volume'
def volume(name, extra=''):
    return dedup(metric('longhorn_' + name, storage, extra), volkeys)
health = volume('volume_robustness', 'state=~"degraded|faulted"')
backup = volume('volume_last_backup_at')
present = volume('volume_capacity_bytes')
zero = f'0 * count({health})'
backup_zero = f'0 * count({backup})'
d = Dashboard('Virtualization · Storage & Protection', 'Longhorn capacity, volume health, I/O and backup metadata.',
              '**Volume scope, not VM backup assurance.** These are Longhorn volumes, including non-VM PVCs and detached volumes. State metrics use labeled 0/1 series. A last-backup timestamp records metadata, not a tested restore or application-consistent backup. Snapshot space stays in the storage cluster. Host capacity panels follow only the cluster filter. No deletion or cleanup is performed.', variables)
d.add('unhealthy', 'Degraded or faulted volumes', 'Count of unique volumes with an active degraded/faulted state. Detached unknown is not counted as healthy or unhealthy here. Zero is shown only when robustness telemetry exists.', [('Volumes', f'count({health} == 1) or ({zero})')], stat=True, width=8)
d.add('neverBackup', 'Volumes without a recorded backup', 'Last successful backup timestamp equals zero. Includes all selected volumes, not just VM disks. Check which volumes require protection before scheduling backups.', [('Volumes', f'count({backup} == 0) or ({backup_zero})')], stat=True, width=8)
d.add('staleBackup', 'Last backup older than 7 days', 'Counts only non-zero last-backup timestamps older than 7 days. Never-backed-up volumes are shown separately. The 7-day review window is not your agreed RPO.', [('Volumes', f'count(((time() - ({backup})) > 604800) and ({backup} > 0)) or ({backup_zero})')], stat=True, width=8)
for key, title, desc, queries, unit in [
    ('volumeHealth', 'Volume robustness · active states', 'Only states whose value is 1 are shown. Unknown on detached volumes is expected; verify attachment before declaring an incident.', [('${k8s_cluster_name} · ${volume} · ${state}', f'max by ({volkeys},state) ({metric("longhorn_volume_robustness",storage)}) == 1')], 'decimal'),
    ('attachment', 'Volume attachment · active states', 'Attachment state uses one labeled 0/1 series per state. Detached volumes can be legitimate stopped VM disks; not a deletion list.', [('${k8s_cluster_name} · ${volume} · ${state}', f'max by ({volkeys},state) ({metric("longhorn_volume_state",storage)}) == 1')], 'decimal'),
    ('latency', 'Longhorn volume I/O latency · ms', 'Longhorn exposes current latency gauges in nanoseconds. Divide by 1,000,000; do not apply rate(). Filter zero-IOPS volumes out because idle latency has no operational meaning.', [('${volume} · ' + direction, f'({volume("volume_" + direction + "_latency")} / 1000000) and ({volume("volume_" + direction + "_iops")} > 0)') for direction in ('read','write')], 'milliseconds'),
    ('iops', 'Longhorn volume IOPS', 'Read/write operations per second are already gauges computed by Longhorn. Do not take a second rate.', [('${volume} · ' + direction, volume('volume_' + direction + '_iops')) for direction in ('read','write')], 'decimal'),
    ('backupAge', 'Last successful backup age · days', 'time() minus the non-zero Unix timestamp, divided by 86400. Empty may mean no backup; see the never-backed-up tile. Does not verify target accessibility or restore.', [('${volume}', f'(time() - ({backup} > 0)) / 86400')], 'decimal'),
    ('backupState', 'Backup state code', 'Longhorn 1.11.2: 0 New, 1 Pending, 2 InProgress, 3 Completed, 4 Error, 5 Unknown. Empty means no matching backup objects or missing telemetry. Metadata only.', [('${volume} · ${backup}', f'max by ({volkeys},backup) ({metric("longhorn_backup_state",storage)})')], 'decimal'),
    ('snapshotSpace', 'Snapshot logical data · one copy per snapshot', 'Sum reported snapshot sizes, deduplicated by volume/snapshot. This is not physical replicated disk usage or guaranteed reclaimable space; sharing, rebuilds and purge behavior matter.', [('${volume}', f'sum by ({volkeys}) (max by ({volkeys},snapshot) ({metric("longhorn_snapshot_actual_size_bytes",storage)}))')], 'bytes(IEC)'),
    ('logicalCapacity', 'Volume provisioned capacity', 'Logical provisioned size, independent of physical bytes used and replica count.', [('${volume}', present)], 'bytes(IEC)'),
]:
    d.add(key,title,desc,queries,unit)
d.add('physicalStorage','Node physical storage · cluster scope','Longhorn-managed node capacity, used bytes and reserved bytes for other applications/system. Cluster scope: volume filter does not apply. Scheduled bytes are a different measure.', [('${node} · '+kind, dedup(metric('longhorn_node_storage_' + kind + '_bytes',storage_cluster),'k8s_cluster_name,node')) for kind in ('capacity','usage','reservation')], 'bytes(IEC)')
d.add('scheduledStorage','Node scheduled replica capacity · cluster scope','Logical bytes scheduled as replicas. Can exceed physical capacity with thin provisioning; do not subtract this from physical usage to calculate free disk.', [('${node}', dedup(metric('longhorn_node_storage_scheduled_bytes',storage_cluster),'k8s_cluster_name,node'))], 'bytes(IEC)')
d.save('virtualization-storage')

variables = [variable('import_cluster','Cluster','cluster_name','harvester_import_inventory_up'), variable('import_namespace','Namespace','namespace','harvester_import_info{cluster_name=~"${import_cluster}"}'), variable('import_name','Import','import_name','harvester_import_info{cluster_name=~"${import_cluster}",namespace=~"${import_namespace}"}')]
imports = 'cluster_name=~"${import_cluster}",namespace=~"${import_namespace}",import_name=~"${import_name}"'
import_keys = 'cluster_name,namespace,import_name,target_vm,source_kind'
inventory = 'max by (cluster_name) (harvester_import_inventory_up{cluster_name=~"${import_cluster}"})'
info = f'max by ({import_keys},phase,outcome) (harvester_import_info{{{imports}}}) and on (cluster_name) ({inventory} == 1)'
zero = f'0 * sum({inventory} == 1)'
import_alias = '${cluster_name} · ${namespace} · ${import_name}'
def imported(name, extra=''):
    return f'max by ({import_keys}) ({name}{{{imports}{","+extra if extra else ""}}}) and on (cluster_name) ({inventory} == 1)'
d = Dashboard('Virtualization · VMware Imports (VMIC)', 'VM Import Controller phases, failures, disk readiness and recorded stage durations.',
              '**VM Import Controller imports, not live migration.** Retained import objects are the inventory; deleting them removes this live inventory, while metric retention controls history. Success means the controller recorded virtualMachineRunning, not application acceptance. Disk readiness is completed disk objects, not transfer bytes or an overall progress percentage. Stage durations come only from explicit recorded timestamps; no exact total migration duration or ETA is inferred. No import, shutdown or retry action is executed.', variables)
for key,title,outcome in [('registered','Retained import records',None),('succeeded','Controller completed','succeeded'),('failed','Failed / invalid records','failed'),('active','Active / pending records','active')]:
    expression=info if outcome is None else info.replace('harvester_import_info{'+imports+'}', 'harvester_import_info{'+imports+',outcome="'+outcome+'"}')
    d.add(key,title,'Count of retained import objects in the selected scope. Unknown/new phases are not silently classified as succeeded. A zero is produced only while inventory collection is healthy.',[(title,f'count({expression}) or ({zero})')],stat=True,width=6)
d.add('phases','Recorded phase per import','Each visible series has value 1 and names the controller phase. virtualMachineRunning is the terminal controller status; it is not a current guest-health check.',[(import_alias+' · ${phase} · ${outcome}',info)])
d.add('collection','Import inventory collection · 1 healthy / 0 failed','API read success and exporter freshness. HTTP scrape success alone is insufficient: this signal becomes 0 on API errors or stale polling.', [('${cluster_name}',inventory)])
d.add('diskReadiness','Disk objects ready · %','Number of disk records with VirtualMachineImageReady=True divided by recorded disks. A 100% value covers the disk-image stage only; VM creation and boot can still be pending. No disks means undefined, not 100%.',[(import_alias,f'100 * ({imported("harvester_import_disks", "state=\"ready\"")}) / (({imported("harvester_import_disks", "state=\"total\"")}) > 0)')],'percent')
d.add('disks','Disk records by import','Counts recorded total, ready and failed disks. Ready takes precedence over an old failed condition after recovery. These are disk objects, not bytes transferred.',[(import_alias+' · '+state,imported('harvester_import_disks','state="'+state+'"')) for state in ('total','ready','failed')])
d.add('activeAge','Active import age · seconds','Elapsed time from object creation for active imports only. Includes queueing and all stages; no promised completion time is inferred.',[(import_alias,imported('harvester_import_active_age_seconds'))],'seconds')
d.add('lastCondition','Time since last recorded condition · active imports','Age of the newest condition timestamp for active imports. Long copy operations may legitimately have no condition updates; this is an investigation signal, not proof that transfer stalled.',[(import_alias,f'(time() - ({imported("harvester_import_last_condition_timestamp_seconds")})) and on (cluster_name,namespace,import_name) (harvester_import_info{{{imports},outcome="active"}})')],'seconds')
d.add('logicalDisks','Recorded disk capacity · bytes','Sum diskSize from the controller API. Logical source disk capacity, not bytes copied, allocated storage or measured throughput. Missing sizes remain absent.',[(import_alias,imported('harvester_import_disk_capacity_bytes','state="total"'))],'bytes(IEC)')
d.add('stageTimes','Recorded stage duration · seconds','poweroff_to_export: VMPoweredOff → VMExported. images_submitted_to_ready: earliest submitted → latest ready across all disks, only when every disk has timestamps. These intervals do not include full boot/application acceptance and are not end-to-end migration duration.',[(import_alias+' · ${stage}',f'max by ({import_keys},stage) (harvester_import_stage_duration_seconds{{{imports}}}) and on (cluster_name) ({inventory} == 1)')],'seconds')
d.save('imports')

# Coverage is kept in the same catalog as the existing dashboards.
path = ROOT / 'files/panel-monitor-coverage.json'
coverage = json.loads(path.read_text())
slugs = {'virtualization-contention','virtualization-capacity','virtualization-storage','imports'}
coverage = [row for row in coverage if row['dashboard'] not in slugs]
for slug in sorted(slugs):
    panels = json.loads((ROOT/'dashboards'/(slug+'.json')).read_text())['dashboard']['spec']['panels']
    coverage += [{'dashboard':slug,'panel':key,'title':panel['spec']['display']['name'],'monitors':[],'guidance':'Decision support; inspect source health, coverage and the metric contract.'} for key,panel in panels.items() if panel['spec'].get('queries')]
path.write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
