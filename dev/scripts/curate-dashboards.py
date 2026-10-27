#!/usr/bin/env python3
"""Apply the English reading guide, native display formats and reviewed layouts.

Run after the two metric generators. Query changes below are deliberately small:
status summaries count active states instead of plotting hundreds of 0/1 lines.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'components/suse-observability-content'
META = {
 'harvester': ('Virtualization · VM & Host Overview', 'Are my virtual machines and their hosts running out of resources?', 'Start with the summary, then select a VM to see its memory and disks. VM means the operating system inside the virtual machine; host means the physical Harvester server. Host panels always cover the selected cluster.'),
 'virtualization-contention': ('Virtualization · VM Performance', 'Why is a virtual machine slow? Compare CPU waiting time, memory pressure and disk response.', 'Select a VM and look for changes at the same time as the slowdown. High CPU use alone does not prove a problem: also check waiting time and disk response. Most rates use the last 5 minutes.'),
 'virtualization-capacity': ('Virtualization · Capacity Planning', 'How much capacity is assigned to running VMs, and how much room is left?', 'Assigned resources are configuration, not actual use. Use available host memory before starting more VMs. The 24-hour charts help review sizing; they do not recommend an automatic resize or guarantee high availability.'),
 'virtualization-storage': ('Virtualization · Storage & Backups', 'Which volumes need attention, how busy is storage, and what backups are recorded?', 'Start with volume health, then check storage space and backups. A volume is a virtual disk; this view includes all selected Longhorn volumes, including non-VM volumes. A recorded backup does not prove that a restore will succeed.'),
 'imports': ('Virtualization · VMware Import Progress', 'Which VMware imports have finished, failed or are still being processed by VM Import Controller?', 'Select an import to see its current stage and disk preparation. Completed means the controller recorded the VM starting; check the application separately. Disk readiness is not the percentage of data transferred. This dashboard does not cover Coriolis.'),
 'applications': ('Applications · Traffic, Errors & Speed', 'How many requests reach the application, how often do they fail, and how long do they take?', 'Choose an application, then compare traffic, errors and response time. These measurements come from instrumentation inside the application. Health-check routes are excluded. No traffic cannot prove availability.'),
 'traefik': ('Traefik · Incoming Traffic & Errors', 'Are requests reaching applications through Traefik, and where are errors or delays occurring?', 'Traefik is the entry point that sends incoming requests to applications. Start with traffic, errors and response time, then select an application. Certificates and connections are cluster-wide measurements.'),
 'platform': ('Kubernetes · Cluster Health', 'Are servers and applications available, and is the cluster running out of resources?', 'Start with readiness and missing application copies. Then review server resources, storage and the cluster database. A pod is a running unit of an application; a node is a server. Empty charts need a collection or applicability check.'),
 'resources': ('Kubernetes · Application Resource Usage', 'Are applications using the CPU and memory reserved for them, or approaching their limits?', 'A request reserves resources for scheduling. A limit sets a maximum. Actual use is a separate measurement. Compare the same five busiest pods across used, reserved and limit charts. 1000 mCPU equals one CPU core.'),
}

# key | plain title | first paragraph: meaning and useful next step
READING = {
'harvester': '''
runningCount|Running VMs|Number of running VM instances currently reported by KubeVirt. Powered-off VM definitions are not included; compare this with the running list in Harvester.
guestCpuGauge|Busiest VM: CPU used|CPU use of the busiest selected VM compared with its configured virtual CPUs. If high, open VM Performance to check whether CPU is actually waiting.
guestMemoryGauge|Busiest VM: memory used|Highest memory-use percentage inside a selected VM. This counts memory the guest cannot readily reclaim; check the VM trend before adding RAM.
guestDiskGauge|Fullest VM filesystem|Highest measured filesystem use inside a VM. Review the named VM and mount point before it fills up. Requires QEMU Guest Agent statistics.
hostCpuGauge|Busiest host: CPU used|Highest CPU use on a Harvester server. Includes VMs and platform processes, even when a single VM is selected.
hostMemoryGauge|Busiest host: memory used|Highest memory use on a Harvester server. Review available memory before starting another VM; host use includes platform overhead.
guestUsed|Memory used inside each VM|Memory currently needed inside each selected VM. Compare with available memory; this differs from the VM process memory on the host.
guestAvailable|Memory available inside each VM|Memory that the guest can use without swapping, including reclaimable cache. A falling trend can explain application slowdown.
configuredGuest|Memory assigned to each VM|RAM configured for the guest operating system. This is the assigned amount, not how much the application is using.
resident|VM process memory on the host|Physical host memory used by the VM process, including virtualization overhead. Do not add this to guest memory: they describe different layers of the same VM.
vcpuUse|CPU used by each VM|Average CPU demand in virtual CPU cores. A value of 1 means one core fully occupied over the measurement window, not one configured CPU.
hostAvailable|Memory available on each host|RAM still available on Harvester servers, including reclaimable cache. Includes every workload on the host, regardless of the VM filter.
guestMissing|VMs missing guest memory statistics|Names of running VMs for which guest OS memory statistics were not received. Check guest support and the balloon driver before interpreting other memory charts.
guestDiskUsed|Space used inside VM filesystems|Bytes used in each reported guest filesystem. The VM operating system sees this space; it differs from Longhorn physical disk usage.
guestDiskCapacity|Size of VM filesystems|Total capacity of each measured filesystem inside the VM. Compare the same VM and mount point with space used.
guestDiskRatio|VM filesystem space used|Percentage used in each measured guest filesystem. A sustained rise toward full requires a guest filesystem review.
scrapeHealth|Can we collect VM and storage metrics?|1 means the endpoint answered successfully; 0 means collection failed. Missing lines can mean discovery failed. Check this before trusting an empty chart.
vmSampleAge|How old are the VM measurements?|Seconds since the most recent VM identity sample. Compare with the 30-second collection interval; an old sample is a visibility problem.
''',
'virtualization-contention': '''
cpuReady|Longest wait for CPU|Highest average CPU scheduling wait among selected VMs. A sustained increase means virtual CPUs are waiting for processing time on the host.
cpuUsage|Busiest VM: CPU used|Highest CPU use relative to the VM's configured virtual CPUs. Compare with CPU waiting time before concluding that the host is overloaded.
memoryUse|Busiest VM: memory used|Highest guest memory-use percentage. Compare with swap activity and page reads to see whether memory pressure is affecting performance.
ready|Time VMs spend waiting for CPU|Average percentage of time each VM's virtual CPUs wait to be scheduled. Look for increases that coincide with a slowdown.
cpu|CPU used by each VM|CPU demand as a percentage of configured virtual CPUs. High use can be productive work; CPU waiting time provides the contention context.
ioWait|Time VMs spend waiting for disk I/O|Time virtual CPUs spend blocked on input/output. Compare with disk response time; it is different from waiting for a turn on the CPU.
memory|Memory used inside each VM|Guest memory use after allowing for reclaimable memory. A rising value together with swap or page reads can indicate memory pressure.
faults|Memory pages fetched from disk|Major page faults per second inside each VM. These reads can slow an application; compare with swap and available memory.
swap|VM swap traffic|Estimated bytes per second moved into or out of swap. Repeated activity can indicate insufficient guest memory; a guest reset can distort the estimate.
readLatency|Time to read from a VM disk|Average milliseconds per completed disk read. Lower is faster. Idle disks have no measured average and remain empty.
writeLatency|Time to write to a VM disk|Average milliseconds per completed disk write. Compare a rise with I/O wait and Longhorn storage latency.
''',
'virtualization-capacity': '''
allocatedCpu|Virtual CPUs assigned to running VMs|Total configured virtual CPUs of running VMs. This is an integer allocation count, not measured CPU consumption.
allocatedMemory|RAM assigned to running VMs|Total guest RAM configured for running VMs. Host processes and virtualization overhead need additional memory.
hostAvailable|Host memory available now|RAM available across the selected Harvester hosts. Check each host as well: free memory on another host may not be usable by the next VM.
cpuRatio|Assigned virtual CPUs per host CPU|Configured VM virtual CPUs divided by host logical CPUs. For example, 2 means two assigned vCPUs per logical CPU; whether that is suitable depends on actual demand.
nMinusOne|Memory balance if the largest host fails|Estimated memory remaining after losing the largest host and accounting for running VM allocations. A negative value means a shortfall even before overhead. A positive value does not guarantee failover.
cpuP95|Typical high CPU demand over 24 hours|CPU demand that a VM stayed below for about 95% of measured points in the last day. Compare with peak demand and sample coverage before resizing.
memoryP95|Typical high memory use over 24 hours|Guest memory use that stayed below this value for about 95% of measured points. Incomplete collection does not represent a full day.
cpuPeak|Peak CPU demand over 24 hours|Largest observed CPU demand in the last day. This is a sampled peak, not every brief spike between collections.
coverage|VM CPU samples collected over 24 hours|Number of CPU measurements available for each current VM. At one sample every 30 seconds, an uninterrupted day is about 2880 samples.
''',
'virtualization-storage': '''
unhealthy|Volumes needing attention|Volumes marked degraded or faulted by Longhorn. Open Longhorn to inspect replicas and scheduling; detached volumes with unknown health are counted separately in the health chart.
neverBackup|Volumes with no recorded backup|Volumes whose last successful backup timestamp is zero. Check which ones actually need backups; this includes non-VM volumes.
staleBackup|Volumes last backed up over 7 days ago|Volumes with a successful backup older than seven days. Compare this review window with your own recovery requirement; never-backed-up volumes appear separately.
volumeHealth|Volume count by health|Number of volumes in each Longhorn health state. Unknown often occurs for detached volumes and does not mean healthy. Select a volume to investigate it.
attachment|Volume count by attachment state|How many volumes are attached, detached or changing state. Detached can be normal for stopped VMs and does not mean that a disk should be deleted.
latency|Time to read or write a storage volume|Current average response time reported by Longhorn for active volumes, in milliseconds. Compare with VM disk latency to locate storage delays.
iops|Storage read and write operations|Read and write operations per second reported by Longhorn. More activity is not automatically a problem; compare with response time.
backupAge|Days since the last successful backup|Age of each non-zero last-backup timestamp. Missing data can mean no recorded backup; check the separate count above.
backupState|Backup count by status|Number of backup records in each status. Completed is metadata from Longhorn; it does not verify backup accessibility or a successful restore.
snapshotSpace|Reported snapshot data per volume|Sum of reported snapshot sizes for each volume. Shared data and replicas mean this is not physical space usage or guaranteed reclaimable space.
logicalCapacity|Size assigned to each volume|Provisioned logical capacity of each volume. Physical usage depends on written data, snapshots and replicas.
physicalStorage|Physical storage used and available capacity|Longhorn-managed capacity, used space and reserved space on each host. Includes all volumes in the cluster, regardless of the volume filter.
scheduledStorage|Disk capacity promised to replicas|Logical capacity scheduled for Longhorn replicas. Thin provisioning can make this exceed physical capacity; it is different from bytes already written.
''',
'imports': '''
registered|Import records|Number of import records retained by VM Import Controller. Deleting a record removes it from this current inventory, even if the VM still exists.
succeeded|Completed imports|Imports for which the controller recorded the VM starting. Check the guest and application separately before accepting the migration.
failed|Failed or invalid imports|Import records classified as failed or invalid. Inspect the controller resource and events for the cause before retrying.
active|Imports still in progress|Records still pending or being processed. Compare the current stage and time since the last update; a long transfer can be legitimate.
phases|Current stage of each import|The legend identifies each import and the stage recorded by the controller. A line at 1 marks the recorded stage; it is not a completion percentage.
controllerRx|Import controller: incoming network traffic|Receive bytes per second per Pod interface, averaged over five minutes. Includes all imports and control traffic; not transfer speed for one VM.
controllerTx|Import controller: outgoing network traffic|Transmit bytes per second per Pod interface, averaged over five minutes. Disk export and image serving are separate stages; do not add receive and transmit as unique migrated bytes.
controllerCPU|Import controller: CPU used|CPU used by each controller container over five minutes. 1000 mCPU equals one CPU core. Compare a slowdown with CPU, memory and network together.
controllerMemory|Import controller: memory used|Working-set memory per controller container. Compare the trend with its configured limit and logs.
imageRx|Shared image services: incoming network traffic|Network receive rate for Longhorn backing-image managers and data sources. These services also handle non-import images; this is shared infrastructure traffic.
imageTx|Shared image services: outgoing network traffic|Network transmit rate for shared image services. Interface labels keep management and storage networks separate. This is not attributed to the selected import.
performanceHealth|Can we collect import performance metrics?|1 means the kubelet metrics endpoint answered; 0 means failure. This does not prove matching importer Pods exist. Check TLS, TCP/10250 and nodes/metrics access if collection fails.
collection|Can we read the import inventory?|1 means recent API reads succeeded; 0 means they failed or became stale. This must work before a zero import count can be trusted.
diskReadiness|Disk images ready for the VM|Percentage of recorded disks marked ready. Even at 100%, VM creation and boot may still be pending; this is not transfer progress.
disks|Total, ready and failed disks per import|Counts of disk objects recorded for each import. Compare ready with total; a failed disk requires checking controller events.
activeAge|Time since an active import was created|Elapsed time including queueing and all processing stages. This does not predict when the import will finish.
lastCondition|Time since an active import last changed status|Age of the latest recorded condition. Long copy stages may have no updates, so an old condition alone does not prove a stalled transfer.
logicalDisks|Source disk capacity recorded by the import|Logical disk sizes read from the controller. These are not bytes already transferred or measured storage usage.
stageTimes|Time spent in recorded import stages|Duration of stages with explicit start and end timestamps. These intervals do not measure the entire migration or application acceptance.
''',
'applications': '''
rps|Requests per second|Average application traffic during the selected period. Fractional values are normal: 0.5 requests/s means about one request every two seconds.
requests1h|Requests in the selected period|Estimated number of completed requests in the selected time range. Counter sampling can make the estimate fractional; the display rounds to whole requests.
requests24h|Server errors in the selected period|Estimated number of HTTP 5xx responses in the selected range. Check affected routes and application logs.
success|Successful responses and redirects|Percentage of measured requests with HTTP 2xx or 3xx responses during the selected period. Compare with both client and server errors; no traffic cannot establish success.
error5xx|Requests ending in a server error|Percentage of completed requests with an HTTP 5xx response. Timeouts before instrumentation may not be counted.
p95_1h|Response time for 95% of requests|About 95% of measured requests completed within this time. This estimate uses histogram buckets; a few slow requests can still take longer.
throughput|Traffic by application route|Requests per second for each measured route, such as an API endpoint. Compare traffic changes with errors and response time.
outcomes|Successful responses and errors over time|Traffic grouped by response type. HTTP 4xx usually indicates a rejected client request; HTTP 5xx indicates a server-side failure.
errorRoutes|Where and when requests fail|Error requests per second by route. Select a time with an increase and inspect that application's logs or traces.
errorTotals|Errors by route and response code|Estimated errors in the selected period, grouped by application, route and code. Read the legend or open details to identify repeated failures.
latency|Response time over time|Compare typical and slow-request response times. A rising tail can reveal slow requests hidden by the average.
routeTotals|Requests by route in the selected period|Estimated requests per application route. These totals describe the selected period; a flat line is a period summary, not a traffic trend.
slowServices|Slowest applications|Applications with the highest response time for 95% of requests. Compare traffic volume because low sample counts can make this estimate unstable.
availability5m|Requests without server errors|Share of completed requests that did not return HTTP 5xx over the last five minutes. This is request-based availability, not measured uptime.
burnRate|How quickly errors use the allowed budget|1 means errors consume the allowed budget at the planned rate; 10 means ten times that rate. Compare both windows and your agreed availability target.
sampleAge|How old are the request measurements?|Seconds since the newest request-counter sample. A counter may stay unchanged with no traffic while its samples remain fresh.
''',
'traefik': '''
rps|Requests per second|Incoming traffic averaged over the last five minutes. Fractional rates are normal and do not imply a fractional request.
meanLatency|Average response time|Average time for completed requests over five minutes. Compare with the 95% and 99% response-time tiles to find slow outliers.
requestRate|Incoming traffic over time|Requests per second averaged over five minutes. Look for traffic changes at the same time as errors or delays.
requests1h|Requests in the selected period|Estimated completed requests during the selected time range. Sampling estimates are displayed as whole requests.
client4xx|Rejected requests: HTTP 4xx|Estimated HTTP 4xx responses in the selected period. Check authentication, permissions and invalid paths; these are not automatically server outages.
error5xx|Server errors: HTTP 5xx|Estimated HTTP 5xx responses in the selected period. Review backend availability and logs for the affected application.
p95|95% of requests within|About 95% of requests completed within this time over the last five minutes. Some requests can be slower; compare the 99% tile.
p99|99% of requests within|About 99% of requests completed within this time over five minutes. This highlights the slowest requests and is less stable with little traffic.
serviceRequests24h|Requests per application in the selected period|Estimated traffic totals per application. A flat line is a summary for the selected period, not a trend.
serviceErrorRatio|Server-error percentage by application|Percentage of completed requests returning HTTP 5xx per application during the selected period. Inspect the busiest and highest-error applications together.
serviceTraffic|Traffic by application|Requests per second sent through Traefik to each application. Compare with application instrumentation when investigating a difference.
byCode|Traffic by HTTP response code|Requests per second grouped by response code. Use this to distinguish successful responses, redirects, rejected requests and server errors.
latency|Response time over time|Average and percentile response times through Traefik. A higher 99% line reveals slow requests that the average may hide.
serviceLatency|Slowest applications through Traefik|Response time for 95% of requests by application. Includes the path measured by Traefik, which differs from time measured inside an application.
bandwidth|Data transferred per second|Request and response bytes per second measured by Traefik. Compare with traffic to spot unusually large payloads.
tlsExpiry|Days until certificates expire|Time remaining before Traefik TLS certificates expire. A negative value means expired. This covers the whole selected cluster.
codeTotals|Requests by application, code and method|Estimated request totals for the selected period. Use the labels to identify which application, HTTP code and method account for the traffic.
errorTimeline|Server errors in each time interval|Estimated HTTP 5xx responses per chart interval and application. Each point covers the interval ending at its timestamp; inspect logs at the same time.
clientErrorTimeline|Rejected requests in each time interval|Estimated HTTP 4xx responses per chart interval and application. Compare bursts with authentication changes, invalid requests or scans.
connections|Open connections|Concurrent connections by Traefik entry point and protocol. This is not a request count and is not narrowed by application filters.
scrapeHealth|Can we collect Traefik metrics?|1 means the endpoint answered; 0 means collection failed. No series can mean no discovered target. This is a collection check, not application health.
''',
'resources': '''
cpuUsageTop|CPU used by the five busiest pods|Actual CPU use for the five pods selected as busiest at the end of the period. Compare the same names in reserved CPU and CPU limits.
cpuRequestTop|CPU reserved for those same pods|Scheduling requests for the same five pods. Reserved CPU is not actual consumption; 1000 mCPU equals one CPU core.
cpuLimitTop|CPU limit for those same pods|Configured CPU ceiling for the same five pods. A missing limit is different from a zero-CPU allowance.
cpuRequestMissingList|Pods with no CPU reservation|Count of pods with at least one container missing a CPU request. Review their scheduling requirements before setting values.
cpuLimitMissingList|Pods with no CPU limit|Count of pods with at least one container missing a CPU limit. Whether a limit is needed depends on workload policy.
cpuUseGauge|Pod closest to its CPU limit|Highest measured CPU use relative to a configured limit. Compare with throttling and latency; a high percentage alone does not prove a user impact.
memUsageTop|Memory used by the five busiest pods|Working-set memory for the five pods selected as busiest at the end of the period. Compare the same names in reserved memory and limits.
memRequestTop|Memory reserved for those same pods|Scheduling memory requests for the same five pods. These reservations differ from actual memory use.
memLimitTop|Memory limit for those same pods|Configured memory ceiling for the same pods. Exceeding a container limit can cause an out-of-memory termination.
memRequestMissingList|Pods with no memory reservation|Count of pods with at least one container missing a memory request. Review sizing and scheduling requirements.
memLimitMissingList|Pods with no memory limit|Count of pods with at least one container missing a memory limit. Review workload policy and host capacity before choosing limits.
memUseGauge|Pod closest to its memory limit|Highest memory-use percentage relative to a configured limit. Check the trend and container termination reasons before changing resources.
missingSettingsPods|Which pods have missing resource settings?|The legend lists affected pods and missing settings. A line is an inventory marker, not a trend; use the details link for columns.
memoryRisk|Pods using the largest share of their memory limit|Ten highest memory-to-limit percentages. A sustained rise toward the limit may need investigation; check the relevant containers.
cpuReservation|CPU used compared with CPU reserved|CPU use divided by the scheduling request. More than 100% is possible and does not by itself mean a limit was exceeded.
throttling|CPU work delayed by configured limits|Share of CPU scheduling periods in which containers were throttled. Compare with application response time before raising limits.
workingSetRSS|Pod memory: working set and resident memory|Two views of memory for the same busiest pods. Working set and resident memory overlap; do not add them together.
inventoryHealth|Can we read pod resource settings?|1 means pod configuration collection is working; 0 means it failed. Check this before trusting missing-setting counts.
cpuLimitReview|Which pods exceed 80% of their CPU limit?|List of pods above the review threshold. It is a starting point for investigation, not an automatic resizing recommendation.
memLimitReview|Which pods exceed 80% of their memory limit?|List of pods above the review threshold. Compare sustained usage and recent memory-related restarts.
cpuOver80Count|Pods above 80% of their CPU limit|Count of measured pods above the CPU review threshold. See the adjacent detail list for the affected names.
cpuRequestMissingValues|Top 10 pods without CPU requests: current CPU use (mCPU)|Ten highest measured values and five-minute CPU use of affected running pods. Review peak demand and scheduling needs before choosing requests.
cpuLimitMissingValues|Top 10 pods without CPU limits: current CPU use (mCPU)|Ten highest measured values and five-minute CPU use of affected running pods. CPU limits are a policy choice; check throttling and latency before adding them.
memRequestMissingValues|Top 10 pods without memory requests: current memory use|Ten highest measured values and five-minute working-set use of affected running pods. Review sustained and peak use before choosing requests.
memLimitMissingValues|Top 10 pods without memory limits: current memory use|Ten highest measured values and five-minute working-set use of affected running pods. Review application peaks and recent OOM events before choosing limits.
memOver80Count|Pods above 80% of their memory limit|Count of measured pods above the memory review threshold. See the detail list and inspect individual containers.
''',
'platform': '''
ready|Servers ready to run workloads|Percentage of known nodes reporting Ready. A missing or unready server needs investigation before capacity planning.
coverage|Servers with working OS metrics|Percentage of known servers with successful operating-system collection. Missing visibility is different from an unavailable server.
nonRunning|Pods needing attention|Count of pods in concerning states, excluding completed jobs. Use the detail list to see whether the issue is scheduling, startup or readiness.
nonRunningList|Which pods need attention?|Names and observed states of affected pods. Read the legend or open details; lines mark inventory entries, not a performance trend.
restarts|Which pods restarted in the last hour?|Estimated container restarts grouped by pod. Inspect previous logs and termination reasons; a restart alone does not prove a memory problem.
availability|Which applications are missing copies?|Workloads running fewer ready copies than requested. Check scheduling, images and readiness probes for the affected workload.
filesystem|Host filesystem space used|Percentage used on monitored host filesystems. Review the device and mount point; not every exposed device is a separate physical disk.
nodeUsed|Space used on host filesystems|Bytes used on each monitored server filesystem. Compare the same filesystem with capacity and percentage used.
nodeTotal|Size of host filesystems|Total measured filesystem capacity. Device filters exclude several duplicate or irrelevant mounts.
inodeRisk|Filesystem file entries used|Percentage of inode entries used. A filesystem can run out of file entries even when bytes remain available.
pvcRisk|Application volume space used|Percentage used in PVC filesystems that expose usage metrics. Raw block volumes and some drivers cannot supply this measurement.
pvcUsed|Space used in application volumes|Bytes used in measured PVC filesystems. Match the namespace and volume when comparing with capacity.
pvcCapacity|Size of measured application volumes|Reported filesystem capacity for measured PVCs. This is not the total physical capacity of the storage system.
pvcUnmeasured|Volumes without filesystem usage data|Claims lacking filesystem usage measurements. This can be expected for block volumes; verify the storage mode before treating it as a fault.
pvPhases|Storage volumes by status|Current Kubernetes PV status listed by volume. Released requires an ownership and retention review; it is not permission to delete data.
pvcPhases|Application storage requests by status|Current PVC status listed by claim. Pending means the requested storage is not yet bound; inspect provisioning and scheduling events.
etcdLeader|Can database members see a leader?|Each etcd member should report 1 when it sees a leader. A single healthy member does not provide redundancy.
etcdLeaderChanges|Database leader changes in the last hour|Leader changes observed by each database member. Repeated changes may indicate instability; do not sum members as distinct elections.
etcdPending|Database writes waiting for agreement|Proposals waiting for consensus in etcd. A sustained queue can explain slow cluster API operations.
etcdApplyLag|Agreed database writes not yet applied|Difference between committed and applied proposals. A growing gap suggests the database is struggling to apply changes.
etcdFailed|Failed database operations in 15 minutes|Estimated failed proposals recorded by each etcd member. Correlate with API errors, leader changes and storage latency.
etcdWAL|Database log write time: slowest 1%|99th-percentile time to flush the etcd write-ahead log, in milliseconds. Slow storage can affect the whole cluster control plane.
etcdCommit|Database commit time: slowest 1%|99th-percentile etcd backend commit time. Compare with disk latency and pending operations.
etcdDB|Database size compared with its quota|Percentage of etcd's configured storage quota used. Review compaction and maintenance procedures before the quota is exhausted.
etcdScrape|Can we collect cluster database metrics?|1 means an etcd endpoint was collected successfully. Empty data is expected when optional etcd collection is disabled.
etcdPeer|Time for database members to communicate|99th-percentile network round-trip time between etcd members. A single-member cluster may have no peer measurements.
hostCPU|CPU used on each server|Percentage of server CPU time spent busy. Includes applications and platform processes.
hostMemory|Memory available on each server|Percentage of RAM the operating system considers available, including reclaimable cache. Lower means less headroom.
ioPressure|Disk operations waiting or in progress|Average disk operations in progress over the measurement window. Compare with disk response time to interpret a sustained queue.
memoryPressure|Host memory pages fetched from disk|Major page faults per second on each host. Compare with available memory and application latency.
cpuGauge|Busiest server: CPU used|Highest measured server CPU-use percentage. Colors are review thresholds; inspect duration and user impact before acting.
memoryGauge|Busiest server: memory used|Highest server memory-use percentage after allowing for reclaimable memory. Review available RAM and workload growth.
diskGauge|Fullest host filesystem|Highest filesystem-use percentage among measured hosts and mounts. The label identifies the filesystem to investigate.
networkErrors|Network interface errors|Receive and transmit errors per second by interface. Sustained increases need a network and host review.
collectorQueue|Metrics waiting to be delivered|Bytes queued by collectors for delivery to SUSE Observability. A growing queue can indicate a network, authentication or backend issue.
collectorRetries|Metric delivery retries in 15 minutes|Estimated retry attempts by collectors. Inspect collector logs and delivery queues when retries persist.
diskLatency|Time to read or write a host disk|Average response time per completed host disk operation. Idle disks have no meaningful response-time average.
missingCopies|Missing application copies|Total gap between desired and available workload copies. Open the detail list to find the affected applications.
restartCount|Container restarts in the last hour|Estimated restart count across selected pods. Rounded to whole restarts for display; counter sampling can affect estimates.
'''
}

REMOVE = {
 'harvester': 'guestTotal domainRequest domainLimit vcpuRequest vcpuLimit hostUsed hostRequests hostLimits cpuReady cpuWait majorFaults swapin swapout diskread diskwrite diskIOPS storageHealth storageUsage'.split(),
 'traefik': ['collection','openConnections'],
}
COUNTS = {
 'harvester': {'runningCount','scrapeHealth','guestMissing'}, 'virtualization-capacity': {'allocatedCpu','coverage'},
 'virtualization-storage': {'unhealthy','neverBackup','staleBackup','volumeHealth','attachment','backupState'},
 'imports': {'registered','succeeded','failed','active','disks','phases','collection'},
 'applications': {'requests1h','requests24h','errorTotals','routeTotals'},
 'traefik': {'requests1h','client4xx','error5xx','serviceRequests24h','codeTotals','connections','scrapeHealth','errorTimeline','clientErrorTimeline'},
 'resources': {'cpuRequestMissingList','cpuLimitMissingList','memRequestMissingList','memLimitMissingList','cpuOver80Count','memOver80Count','inventoryHealth','missingSettingsPods'},
 'platform': {'nonRunning','nonRunningList','restarts','availability','pvcUnmeasured','pvPhases','pvcPhases','etcdLeader','etcdLeaderChanges','etcdPending','etcdApplyLag','etcdFailed','etcdScrape','collectorRetries','missingCopies','restartCount'},
}
SECTIONS = {
 'harvester': [('Summary','runningCount guestCpuGauge guestMemoryGauge guestDiskGauge hostCpuGauge hostMemoryGauge'),('Memory and CPU inside the VMs','guestUsed guestAvailable configuredGuest resident vcpuUse hostAvailable'),('Filesystems inside the VMs','guestDiskRatio guestDiskUsed guestDiskCapacity guestMissing'),('Check the measurements','scrapeHealth vmSampleAge')],
 'virtualization-contention': [('Summary','cpuReady cpuUsage memoryUse'),('CPU and memory: find the bottleneck','ready cpu ioWait memory faults swap'),('Disk response time','readLatency writeLatency')],
 'virtualization-capacity': [('Assigned resources and headroom','allocatedCpu allocatedMemory hostAvailable'),('Capacity and failure planning','cpuRatio nMinusOne'),('Review VM sizing using the last 24 hours','cpuP95 cpuPeak memoryP95 coverage')],
 'virtualization-storage': [('What needs review?','unhealthy neverBackup staleBackup'),('Volume health and storage space','volumeHealth attachment physicalStorage scheduledStorage logicalCapacity snapshotSpace'),('Storage activity and speed','iops latency'),('Backup records','backupAge backupState')],
 'imports': [('Import summary','registered succeeded failed active'),('Current progress','phases diskReadiness disks'),('Time and disk capacity','activeAge lastCondition stageTimes logicalDisks'),('Import infrastructure performance','controllerRx controllerTx controllerCPU controllerMemory imageRx imageTx performanceHealth'),('Check the measurements','collection')],
 'applications': [('Traffic, errors and speed','rps requests1h requests24h success error5xx p95_1h'),('Find affected routes and applications','throughput outcomes errorRoutes latency slowServices errorTotals routeTotals'),('Availability target and data freshness','availability5m burnRate sampleAge')],
 'traefik': [('Traffic, errors and speed','rps client4xx error5xx requests1h meanLatency p95 p99'),('Find affected applications','requestRate serviceTraffic byCode latency serviceLatency errorTimeline clientErrorTimeline bandwidth'),('Selected-period summaries','serviceRequests24h serviceErrorRatio codeTotals'),('Connections, certificates and data collection','connections tlsExpiry scrapeHealth')],
 'resources': [('Resource limits and missing settings','cpuUseGauge memUseGauge cpuOver80Count memOver80Count'),('Pods needing review','memLimitReview cpuLimitReview cpuRequestMissingList cpuRequestMissingValues cpuLimitMissingList cpuLimitMissingValues memRequestMissingList memRequestMissingValues memLimitMissingList memLimitMissingValues'),('Compare the same five pods: CPU','cpuUsageTop cpuRequestTop cpuLimitTop'),('Compare the same five pods: memory','memUsageTop memRequestTop memLimitTop'),('Investigate settings and resource pressure','missingSettingsPods memoryRisk cpuReservation throttling workingSetRSS'),('Check the measurements','inventoryHealth')],
 'platform': [('Cluster summary','ready coverage nonRunning missingCopies restartCount cpuGauge memoryGauge diskGauge'),('Applications needing attention','nonRunningList availability restarts'),('Server resources','hostCPU hostMemory filesystem inodeRisk nodeUsed nodeTotal diskLatency ioPressure memoryPressure networkErrors'),('Application storage','pvcRisk pvcUsed pvcCapacity pvcUnmeasured pvPhases pvcPhases'),('Cluster database: etcd (optional collection)','etcdLeader etcdLeaderChanges etcdPending etcdApplyLag etcdFailed etcdDB etcdWAL etcdCommit etcdPeer etcdScrape'),('Check metric delivery','collectorQueue collectorRetries')],
}

SECTION_HELP = {
 'Memory and CPU inside the VMs':'Compare used and available memory for the same VM. Assigned memory is configuration; VM process memory and host memory describe different layers.',
 'Filesystems inside the VMs':'Look at the VM and mount-point labels. Used bytes, total size and percentage describe the same guest filesystem; QEMU Guest Agent must provide these measurements.',
 'Check the measurements':'Check collection and sample age before interpreting missing data. A running collector Pod alone does not prove that measurements are arriving.',
 'CPU and memory: find the bottleneck':'Compare changes at the time of a slowdown. CPU use, CPU waiting and memory pressure answer different questions.',
 'Disk response time':'Compare read and write response times. Idle disks have no measured average; an empty latency chart alone is not a failure.',
 'Capacity and failure planning':'These estimates help planning. Assigned virtual CPUs are not actual CPU demand, and a positive memory balance does not guarantee failover.',
 'Review VM sizing using the last 24 hours':'Compare typical high demand, the sampled peak and collection coverage. A short history does not become a full day simply by selecting 24 hours.',
 'Volume health and storage space':'Health states and storage sizes are different measurements. Physical bytes used, provisioned volume size and scheduled replicas must not be added together.',
 'Storage activity and speed':'Operations per second measure activity; response time measures how long an operation takes. Compare them to identify delays under load.',
 'Backup records':'Check the backup policy for the selected volumes. Backup timestamps and statuses are useful records, but only a restore test demonstrates recoverability.',
 'Current progress':'The stage is recorded by VM Import Controller. Disk readiness covers disk preparation, not transfer percentage or application acceptance.',
 'Time and disk capacity':'Elapsed times include only the recorded stages or object age. Disk capacity is logical source size, not bytes transferred; no completion time is predicted.',
 'Find affected routes and applications':'Use traffic, errors and response time together. Follow the application or route labels, then inspect logs and traces at the time of the problem.',
 'Availability target and data freshness':'Request availability excludes unmeasured failures and is undefined without traffic. Error-budget use is meaningful only against an agreed target and reliable measurements.',
 'Find affected applications':'Compare the same application across traffic, errors and response time. Traefik measurements include the request path it observes and may differ from application instrumentation.',
 'Selected-period summaries':'These panels summarize the whole selected period. Their flat lines are totals or ratios, not trends; use the traffic and error charts above to locate changes in time.',
 'Connections, certificates and data collection':'Connections and certificates cover the selected cluster, regardless of the application filter. Check collection before trusting missing Traefik measurements.',
 'Compare the same five pods: CPU':'Read the same pod name across used CPU, reserved CPU and CPU limit. 1000 mCPU equals one CPU core. A missing limit does not mean a zero allowance.',
 'Compare the same five pods: memory':'Read the same pod name across working-set use, scheduling reservation and memory limit. These values have different meanings and must not be added together.',
 'Investigate settings and resource pressure':'Lists identify affected pods; trends show how demand changed. Use application impact and container details before changing requests or limits.',
 'Applications needing attention':'A pod can be starting, waiting or failing. Read the observed state and inspect events and previous logs before declaring an incident.',
 'Server resources':'Host CPU, memory, filesystems and I/O include both applications and platform services. Compare sustained changes with application availability and response time.',
 'Application storage':'Filesystem usage is available only for supported volume modes and drivers. Missing measurements for a raw block volume can be expected.',
 'Cluster database: etcd (optional collection)':'etcd stores the cluster configuration. Begin with leader visibility, then check queues, disk latency and quota. Empty charts are expected when optional collection is disabled; one member has no peer traffic or redundancy.',
 'Check metric delivery':'A growing delivery queue or repeated retries can make the dashboard stale. Check collector logs, network connectivity and the SUSE backend.',
}

UNITS = {
 'imports': {'controllerCPU':('none','mCPU (1000 = 1 CPU)','mCPU')},
 'resources': {key:('none','mCPU (1000 = 1 CPU)','mCPU') for key in ('cpuUsageTop','cpuRequestTop','cpuLimitTop')},
 'harvester': {'vcpuUse':('decimal','CPU cores','CPU cores')},
 'virtualization-contention': {'faults':('decimal','Pages per second','pages/s')},
 'virtualization-capacity': {'cpuP95':('decimal','CPU cores','CPU cores'),'cpuPeak':('decimal','CPU cores','CPU cores'),'cpuRatio':('decimal','Assigned vCPUs per host CPU','')},
 'virtualization-storage': {'iops':('decimal','Operations per second','operations/s'),'backupAge':('decimal','Days','')},
 'traefik': {**{key:('milliseconds','Milliseconds','ms') for key in ('meanLatency','p95','p99','latency','serviceLatency')},'tlsExpiry':('decimal','Days','')},
 'applications': {**{key:('milliseconds','Milliseconds','ms') for key in ('p95_1h','latency','slowServices')},'burnRate':('decimal','Budget consumption multiplier','times the allowed rate')},
 'platform': {**{key:('milliseconds','Milliseconds','ms') for key in ('diskLatency','etcdCommit','etcdPeer','etcdWAL')},'ioPressure':('decimal','Average operations in progress','operations'),'memoryPressure':('decimal','Pages per second','pages/s'),'networkErrors':('decimal','Errors per second','errors/s')},
}

def query(panel, expression, alias):
    panel['spec']['queries'] = [{'kind':'TimeSeriesQuery','spec':{'plugin':{'kind':'PrometheusTimeSeriesQuery','spec':{'query':expression,'alias':alias}}}}]

# Native SUSE 2.10.2 has no Table widget. StatChart preserves each series/value
# pair; its TimeSeries legend Last column can misattribute values.
ACTION_LISTS = {'resources': {'memLimitReview','cpuLimitReview','cpuRequestMissingValues',
    'cpuLimitMissingValues','memRequestMissingValues','memLimitMissingValues'}}

def add_actionable_panels(slug, panels):
    if slug == 'resources':
        selector='cluster_name=~"${workload_cluster}",namespace=~"${workload_namespace}"'
        keys='cluster_name,namespace,pod_name,container'; pods='cluster_name,namespace,pod_name'
        running=f'max by ({keys}) (last_over_time(sre_pod_container_running{{{selector}}}[5m] @ end()) == 1)'
        for resource, short in [('cpu','cpu'),('memory','mem')]:
            usage=(f'avg_over_time(container_cpu_usage{{{selector}}}[5m] @ end()) / 1000000' if resource=='cpu'
                   else f'avg_over_time(container_memory_working_set{{{selector}}}[5m] @ end())')
            used=f'sum by ({pods}) ((max by ({keys}) ({usage})) and on ({keys}) ({running}))'
            for setting, label in [('requested','Request'),('limit','Limit')]:
                missing=f'max by ({pods}) (({running}) unless on ({keys}) (max by ({keys}) (last_over_time(sre_pod_container_{resource}_{setting}{{{selector}}}[5m] @ end())) > 0))'
                expression=f'({used}) and on ({pods}) ({missing})'
                key=short+label+'MissingValues'
                panels[key]=copy.deepcopy(panels['memoryRisk'])
                panels[key]['spec'].pop('links',None)
                panels[key]['spec']['display']={'name':key,'description':'Latest five-minute average for running regular containers, grouped by Pod. At least one running container has no positive setting. Not a recommended request or limit. Empty means no matching measured Pod, or missing usage data; check inventory health and the count. Hover for full names; open the table for all labels.'}
                panels[key]['spec']['plugin']['spec']['yAxis']['format']={'unit':'none' if resource=='cpu' else 'bytes(IEC)'}
                query(panels[key],f'max by (sre_series) (label_join(({expression}), "sre_series", " · ", "cluster_name", "namespace", "pod_name"))','${sre_series}')
        for key in ACTION_LISTS[slug]:
            p=panels[key]['spec']; q=p['queries'][0]['spec']['plugin']['spec']
            if q['query'].startswith('sort_by_label('):
                q['query']=q['query'][14:-15]
            if key.endswith('MissingValues'): q['query']='topk(10, '+q['query']+')'
            unit='percentunit' if key.endswith('LimitReview') else ('none' if key.startswith('cpu') else 'bytes(IEC)')
            p['plugin']={'kind':'StatChart','spec':{'calculation':'last','sparkline':False,'valueFontSize':20,'format':{'unit':unit,'decimalPlaces':1},'thresholds':{'defaultColor':'#1976B9','steps':[]}}}
            if key.endswith('LimitReview'):p['plugin']['spec']['thresholds']={'defaultColor':'#1976B9','steps':[{'value':0.8,'color':'#E5A000'},{'value':0.95,'color':'#D3443B'}]}

            p['display']['description']=p['display'].get('description','').replace('use the details link for columns','read the value beside each name')
    if slug == 'imports':
        select='cluster_name=~"${import_cluster}",job="sre-import-performance"'
        controller=select+',namespace="harvester-system",pod_name=~"harvester-vm-import-controller-.+"'
        images=select+',namespace="longhorn-system",pod_name=~"(bim-|backing-image-manager-|backing-image-ds-).+"'
        for key,sel,direction in [('controllerRx',controller,'receive'),('controllerTx',controller,'transmit'),('imageRx',images,'receive'),('imageTx',images,'transmit')]:
            panels[key]=copy.deepcopy(panels['activeAge']); p=panels[key]['spec'];p.pop('links',None)
            p['display']={'name':key,'description':'cAdvisor per-Pod interface counter. rate() is applied before deduplication by cluster, namespace, pod and interface. Loopback excluded. Cluster scope: import and namespace filters do not narrow shared infrastructure. No bandwidth percentage without an independently known link capacity. No active-transfer validation in this lab; retained imports are completed.'}
            p['plugin']['spec']['yAxis']['format']={'unit':'bytes/sec'}
            query(panels[key],f'max by (cluster_name,namespace,pod_name,interface) (rate(harvester_import_network_{direction}_bytes_total{{{sel},interface!="lo"}}[5m]))','${cluster_name} · ${pod_name} · ${interface}')
        for key,metric,unit in [('controllerCPU','1000 * rate(harvester_import_cpu_usage_seconds_total{'+controller+',container!="",container!="POD"}[5m])','none'),('controllerMemory','harvester_import_memory_working_set_bytes{'+controller+',container!="",container!="POD"}','bytes(IEC)'),('performanceHealth','up{'+select+'}','decimal')]:
            panels[key]=copy.deepcopy(panels['activeAge']);p=panels[key]['spec'];p.pop('links',None)
            p['display']={'name':key,'description':'Direct TLS-verified kubelet /metrics/cadvisor collection. Cluster scope; import and namespace filters do not apply. CPU is mCPU (1000 = one core), memory is working-set bytes. Empty is missing telemetry, not zero. Collection can be disabled with imports.performance.enabled: false.'}
            p['plugin']['spec']['yAxis']['format']={'unit':unit}
            query(panels[key],f'max by (cluster_name,node,namespace,pod_name,container) ({metric})','${cluster_name} · ${pod_name} · ${container}' if key!='performanceHealth' else '${cluster_name} · ${node}')

guide_rows = ['# Dashboard reading guide', '', 'Each row explains what a panel shows. Open its description in SUSE for the formula, time window and measurement limits.', '', 'Counts use whole numbers; rates can be fractional. Missing data is not proof of health. Period-total panels summarize the selected window and do not show a trend. This is a community lab project, not recommended for production.', '']
reviewed = {}
for slug, (name, purpose, guide) in META.items():
    path = CONTENT / 'dashboards' / (slug + '.json')
    d = json.loads(path.read_text()); d.update(name=name, description=purpose)
    s = d['dashboard']['spec']; panels = s['panels']
    for key in list(panels):
        if key in REMOVE.get(slug, []) or key.startswith('section_') or key == 'etcdGuide':
            del panels[key]
    add_actionable_panels(slug, panels)
    rows = {r.split('|',2)[0]:r.split('|',2)[1:] for r in READING[slug].strip().splitlines()}
    assert set(rows) == set(panels) - {'guide'}, (slug, set(rows) ^ (set(panels)-{'guide'}))
    reviewed[slug] = rows
    if slug == 'platform':
        for key, label in [('ready','Ready servers'),('coverage','OS metrics coverage')]:
            panels[key]['spec']['queries'][0]['spec']['plugin']['spec']['alias']=label
    if slug == 'imports':
        for key in ('registered','succeeded','failed','active'):
            panels[key]['spec']['queries'][0]['spec']['plugin']['spec']['alias']='Imports'
        q=panels['phases']['spec']['queries'][0]['spec']['plugin']['spec']
        if 'display_phase' not in q['query']:
            expression='label_replace('+q['query']+',"display_phase","$1","phase","(.+)")'
            for phase,label in {'sourceReady':'Source ready','disksExported':'Disks exported','diskImageSubmitted':'Preparing disk images','diskImagesReady':'Disk images ready','diskImageFailed':'Disk image failed','virtualMachineCreated':'VM created','virtualMachineRunning':'VM started (controller completed)','virtualMachineImportValid':'Import validated','virtualMachineImportInvalid':'Invalid import','VMMigrationFailed':'Import failed','pending':'Pending','unknown':'Unknown stage'}.items():
                expression='label_replace('+expression+',"display_phase","'+label+'","phase","'+phase+'")'
            q['query']=expression
        q['alias']='${cluster_name} · ${namespace} · ${import_name} · ${display_phase}'
        q=panels['stageTimes']['spec']['queries'][0]['spec']['plugin']['spec']
        if 'display_stage' not in q['query']:
            q['query']='label_replace(label_replace('+q['query']+',"display_stage","Power off to export","stage","poweroff_to_export"),"display_stage","Disk image preparation","stage","images_submitted_to_ready")'
        q['alias']='${cluster_name} · ${namespace} · ${import_name} · ${display_stage}'
    if slug == 'virtualization-contention':
        for key in ('cpuReady','cpuUsage','memoryUse'):
            q=panels[key]['spec']['queries'][0]['spec']['plugin']['spec']
            if q['query'].startswith('max('):
                q['query']='last_over_time((topk(1,'+q['query'][4:-1]+'))[1s:1s] @ end())'
            q['alias']='${k8s_cluster_name} · ${namespace} · ${name}'
    if slug == 'harvester':
        q=panels['runningCount']['spec']['queries'][0]['spec']['plugin']['spec']
        if 'phase="running"' not in q['query']:
            q['query']=q['query'].replace('name=~"${vm_name}"','name=~"${vm_name}",phase="running"')
        # Domain CPU includes overhead and can exceed the configured vCPU ratio.
        panels['guestCpuGauge']['spec']['plugin']={'kind':'StatChart','spec':{'calculation':'last','format':{'unit':'percentunit','decimalPlaces':1},'sparkline':False,'valueFontSize':40,'thresholds':{'defaultColor':'#1976B9','steps':[]}}}
    if slug == 'virtualization-storage':
        selector='k8s_cluster_name=~"${storage_cluster}",volume=~"${storage_volume}"'
        for key,metric in [('volumeHealth','longhorn_volume_robustness'),('attachment','longhorn_volume_state')]:
            query(panels[key],f'sum by (k8s_cluster_name,state) (max by (k8s_cluster_name,volume,state) ({metric}{{{selector}}}))','${k8s_cluster_name} · ${state}')
        base=f'max by (k8s_cluster_name,volume,backup) (longhorn_backup_state{{{selector}}})'
        panels['backupState']['spec']['queries']=[]
        for value,label in enumerate(['New','Pending','In progress','Completed','Error','Unknown']):
            p=copy.deepcopy(panels['backupAge'])
            query(p,f'count by (k8s_cluster_name) ({base} == {value}) or on (k8s_cluster_name) (0 * count by (k8s_cluster_name) ({base}))','${k8s_cluster_name} · '+label)
            panels['backupState']['spec']['queries']+=p['spec']['queries']
    guide_rows += ['## '+name,'',purpose,'','| Panel | What it shows (description in SUSE) |','|---|---|']
    for key,(title,intro) in rows.items():
        p=panels[key]['spec']; old=p['display'].get('description','')
        details=old.split('\n\nMeasurement details:\n',1)[-1]
        details=details.split('\n\nWhen to investigate / alert coverage:',1)[0]
        if any('range_sum(' in q['spec']['plugin']['spec']['query'] for q in p.get('queries',[])):
            details=details.replace('non-overlapping one-minute counter changes','non-overlapping counter changes at the chart resolution (minimum one minute)').replace('partial minute boundaries','partial interval boundaries')
        if slug=='traefik' and key in ('errorTimeline','clientErrorTimeline'):
            for q in p['queries']:
                ps=q['spec']['plugin']['spec'];ps['query']=ps['query'].replace('[1i]','[${__interval}]').replace('[1m]','[${__interval}]');ps['minStep']='1m'
            details='Each point estimates the counter increase over one chart step (SUSE ${__interval}, minimum one minute). The interval grows when zooming out. Labels identify cluster, namespace, application and response code. These are sampled counts, not exact request timestamps. Use the period-total panels for the complete selected range and access logs for individual requests.'
        if key in ('volumeHealth','attachment','backupState') and slug=='virtualization-storage':
            details={'volumeHealth':'Sum of deduplicated 0/1 health-state gauges, grouped by cluster and state. All selected volumes are included. Missing source metrics remain empty.', 'attachment':'Sum of deduplicated 0/1 attachment-state gauges by cluster and state. Not a deletion list. Missing source metrics remain empty.', 'backupState':'Longhorn 1.11.2 codes are counted and named: 0 New, 1 Pending, 2 In progress, 3 Completed, 4 Error, 5 Unknown. Zeros appear only when backup-state metrics exist.'}[key]
        if slug=='harvester' and key=='runningCount': details='Count of unique cluster, namespace and VM names with kubevirt_vmi_info phase="running". Missing input stays empty; it is not a count of stopped VM definitions.'
        plug=p['plugin']; spec=plug['spec']
        fmt=spec.get('format', spec.get('yAxis',{}).get('format',{}))
        label=''
        if 'yAxis' in spec:spec['yAxis'].pop('label',None)
        if key in UNITS.get(slug,{}):
            unit,label,suffix=UNITS[slug][key];fmt['unit']=unit
            if suffix:title+=' ('+suffix+')'
        elif fmt.get('unit')=='seconds':
            title+=' (seconds)';label='Seconds'
        elif fmt.get('unit')=='milliseconds':
            title+=' (ms)';label='Milliseconds'
        elif fmt.get('unit') in ('bytes/sec','Bps'):
            title+=' (bytes/s)';label='Bytes per second'
        elif fmt.get('unit')=='reqps':label='Requests per second'
        if 'yAxis' in spec and label:spec['yAxis']['label']=label
        rows[key][0]=title
        p['display']={'name':title,'description':intro+'\n\nMeasurement details:\n'+details}
        fmt['decimalPlaces']=0 if key in COUNTS.get(slug,set()) else (2 if key in ('success','error5xx','availability5m','serviceErrorRatio','cpuRatio','burnRate') else 1)
        if key in COUNTS.get(slug,set()): fmt['unit']='none' if plug['kind']=='StatChart' else 'decimal'
        if plug['kind']=='TimeSeriesChart':
            spec['legend']['values']=[]

            spec.setdefault('visual',{})['connectNulls']=False
        if slug=='traefik' and key in ('errorTimeline','clientErrorTimeline'):
            plug['kind']='TimeSeriesChart'; spec['visual']={'connectNulls':False}
        if p.get('queries') and (p.get('links') or key in ACTION_LISTS.get(slug,set())):
            # SUSE expands variables and URL-encodes this parameter itself.
            # Pre-encoding it produces %255B and breaks the explorer link.
            expressions=[q['spec']['plugin']['spec']['query'] for q in p['queries']]
            if key.endswith('MissingValues') and expressions[0].startswith('topk(10, '): expressions[0]=expressions[0][9:-1]
            if key in ('memLimitReview','cpuLimitReview'):expressions[0]='round(100 * ('+expressions[0]+'), 0.1)'
            state=[[[expression] for expression in expressions], [0,[6,[True,'']]]]
            encoded=json.dumps(state,separators=(',',':'))
            for char in '<>%&+#':encoded=encoded.replace(char,'\\u'+format(ord(char),'04x'))
            p['links']=[{'name':'Open values table','targetBlank':True,
              'tooltip':'All matching measured resources, including those outside Top 10. Select Table view. Check the time range; percentages use 0–100, CPU mCPU, memory bytes.',
              'url':'./#/metrics?metrics='+encoded}]
        guide_rows.append('| '+title+' | '+intro+' |')
    guide_rows.append('')
    panels['guide']['spec']['display']={'name':'What this dashboard tells you','description':purpose}
    panels['guide']['spec']['plugin']['spec']['text']='**'+purpose+'** '+guide+' **No data is not the same as zero.** Use the description icon for measurement details.'
    items=[{'x':0,'y':0,'width':24,'height':1,'content':{'$ref':'#/spec/panels/guide'}}]; y=1
    seen=[]
    for index,(heading,keys) in enumerate(SECTIONS[slug]):
        x=0; row_height=0
        for key in keys.split():
            kind=panels[key]['spec']['plugin']['kind'];width=8 if kind in ('StatChart','GaugeChart') else 12
            if slug=='imports' and key in ('registered','succeeded','failed','active'):width=6
            if slug=='imports' and key==keys.split()[-1] and width==12 and x in (0,24):width=24
            if slug=='traefik' and key in ('requests1h','meanLatency','p95','p99'):width=12
            height=1 if kind=='StatChart' else (2 if kind=='GaugeChart' else 3)
            if slug=='resources' and key in ('cpuUseGauge','memUseGauge','cpuOver80Count','memOver80Count'):width=6;height=2
            if key in ACTION_LISTS.get(slug, set()): width=24; height=3
            if x+width>24:y+=row_height;x=0;row_height=0
            items.append({'x':x,'y':y,'width':width,'height':height,'content':{'$ref':'#/spec/panels/'+key}})
            x+=width;row_height=max(row_height,height);seen.append(key)
        y+=row_height
    assert len(seen)==len(set(seen)) and set(seen)==set(rows),slug
    s['layouts'][0]['spec']['items']=items
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+'\n')

coverage_path=CONTENT/'files/panel-monitor-coverage.json'
coverage=json.loads(coverage_path.read_text())
known={(r['dashboard'],r['panel']) for r in coverage}
for slug,rows in reviewed.items():
    for key in rows:
        if (slug,key) not in known:coverage.append({'dashboard':slug,'panel':key,'title':rows[key][0],'monitors':[],'guidance':'Investigation context; verify collection and source data before acting.'})
coverage=[r for r in coverage if r['panel'] in reviewed[r['dashboard']]]
for row in coverage:row['title']=reviewed[row['dashboard']][row['panel']][0]
coverage.sort(key=lambda r:(r['dashboard'],r['panel']))
coverage_path.write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
(ROOT.parent/'docs/panel-guide.md').write_text('\n'.join(guide_rows)+'\n')
print('Reviewed',sum(len(r) for r in reviewed.values()),'metric panels across',len(reviewed),'dashboards')
