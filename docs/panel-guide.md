# Dashboard reading guide

Each row explains what a panel shows. Open its description in SUSE for the formula, time window and measurement limits.

Counts use whole numbers; rates can be fractional. Missing data is not proof of health. Period-total panels summarize the selected window and do not show a trend. This is a community lab project, not recommended for production.

## Virtualization · VM & Host Overview

Are my virtual machines and their hosts running out of resources?

| Panel | What it shows (description in SUSE) |
|---|---|
| Running VMs | Number of running VM instances currently reported by KubeVirt. Powered-off VM definitions are not included; compare this with the running list in Harvester. |
| Busiest VM: CPU used | CPU use of the busiest selected VM compared with its configured virtual CPUs. If high, open VM Performance to check whether CPU is actually waiting. |
| Busiest VM: memory used | Highest memory-use percentage inside a selected VM. This counts memory the guest cannot readily reclaim; check the VM trend before adding RAM. |
| Fullest VM filesystem | Highest measured filesystem use inside a VM. Review the named VM and mount point before it fills up. Requires QEMU Guest Agent statistics. |
| Busiest host: CPU used | Highest CPU use on a Harvester server. Includes VMs and platform processes, even when a single VM is selected. |
| Busiest host: memory used | Highest memory use on a Harvester server. Review available memory before starting another VM; host use includes platform overhead. |
| Memory used inside each VM | Memory currently needed inside each selected VM. Compare with available memory; this differs from the VM process memory on the host. |
| Memory available inside each VM | Memory that the guest can use without swapping, including reclaimable cache. A falling trend can explain application slowdown. |
| Memory assigned to each VM | RAM configured for the guest operating system. This is the assigned amount, not how much the application is using. |
| VM process memory on the host | Physical host memory used by the VM process, including virtualization overhead. Do not add this to guest memory: they describe different layers of the same VM. |
| CPU used by each VM (CPU cores) | Average CPU demand in virtual CPU cores. A value of 1 means one core fully occupied over the measurement window, not one configured CPU. |
| Memory available on each host | RAM still available on Harvester servers, including reclaimable cache. Includes every workload on the host, regardless of the VM filter. |
| VMs missing guest memory statistics | Names of running VMs for which guest OS memory statistics were not received. Check guest support and the balloon driver before interpreting other memory charts. |
| Space used inside VM filesystems | Bytes used in each reported guest filesystem. The VM operating system sees this space; it differs from Longhorn physical disk usage. |
| Size of VM filesystems | Total capacity of each measured filesystem inside the VM. Compare the same VM and mount point with space used. |
| VM filesystem space used | Percentage used in each measured guest filesystem. A sustained rise toward full requires a guest filesystem review. |
| Can we collect VM and storage metrics? | 1 means the endpoint answered successfully; 0 means collection failed. Missing lines can mean discovery failed. Check this before trusting an empty chart. |
| How old are the VM measurements? (seconds) | Seconds since the most recent VM identity sample. Compare with the 30-second collection interval; an old sample is a visibility problem. |

## Virtualization · VM Performance

Which VMs are busiest, and what could be slowing them down?

| Panel | What it shows (description in SUSE) |
|---|---|
| Top 5 VMs by CPU waiting time | Up to five running VMs with the most CPU scheduling wait at the end of the selected period. Values average the previous 5 minutes. A sustained increase means virtual CPUs are waiting for processing time on the host. |
| Top 5 VMs by CPU use | Up to five running VMs with the highest CPU use relative to configured virtual CPUs, averaged over 5 minutes at the end of the selected period. Compare with CPU waiting time before concluding that the host is overloaded. |
| Top 5 VMs by guest memory use | Up to five running VMs with the highest guest memory-use percentage at the end of the selected period. Reclaimable memory is excluded. Compare with swap activity and page reads before adding RAM. |
| Time VMs spend waiting for CPU | Average percentage of time each VM's virtual CPUs wait to be scheduled. Look for increases that coincide with a slowdown. |
| CPU used by each VM | CPU demand as a percentage of configured virtual CPUs. High use can be productive work; CPU waiting time provides the contention context. |
| Time VMs spend waiting for disk I/O | Time virtual CPUs spend blocked on input/output. Compare with disk response time; it is different from waiting for a turn on the CPU. |
| Memory used inside each VM | Guest memory use after allowing for reclaimable memory. A rising value together with swap or page reads can indicate memory pressure. |
| Memory pages fetched from disk (pages/s) | Major page faults per second inside each VM. These reads can slow an application; compare with swap and available memory. |
| VM swap traffic (bytes/s) | Estimated bytes per second moved into or out of swap. Repeated activity can indicate insufficient guest memory; a guest reset can distort the estimate. |
| Time to read from a VM disk (ms) | Average milliseconds per completed disk read. Lower is faster. Idle disks have no measured average and remain empty. |
| Time to write to a VM disk (ms) | Average milliseconds per completed disk write. Compare a rise with I/O wait and Longhorn storage latency. |

## Virtualization · Capacity Planning

How much capacity is assigned to running VMs, and how much room is left?

| Panel | What it shows (description in SUSE) |
|---|---|
| Virtual CPUs assigned to running VMs | Total configured virtual CPUs of running VMs. This is an integer allocation count, not measured CPU consumption. |
| RAM assigned to running VMs | Total guest RAM configured for running VMs. Host processes and virtualization overhead need additional memory. |
| Host memory available now | RAM available across the selected Harvester hosts. Check each host as well: free memory on another host may not be usable by the next VM. |
| Assigned virtual CPUs per host CPU | Configured VM virtual CPUs divided by host logical CPUs. For example, 2 means two assigned vCPUs per logical CPU; whether that is suitable depends on actual demand. |
| Memory balance if the largest host fails | Estimated memory remaining after losing the largest host and accounting for running VM allocations. A negative value means a shortfall even before overhead. A positive value does not guarantee failover. |
| Typical high CPU demand over 24 hours (CPU cores) | CPU demand that a VM stayed below for about 95% of measured points in the last day. Compare with peak demand and sample coverage before resizing. |
| Typical high memory use over 24 hours | Guest memory use that stayed below this value for about 95% of measured points. Incomplete collection does not represent a full day. |
| Peak CPU demand over 24 hours (CPU cores) | Largest observed CPU demand in the last day. This is a sampled peak, not every brief spike between collections. |
| VM CPU samples collected over 24 hours | Number of CPU measurements available for each current VM. At one sample every 30 seconds, an uninterrupted day is about 2880 samples. |

## Virtualization · Storage & Backups

Which volumes need attention, how busy is storage, and what backups are recorded?

| Panel | What it shows (description in SUSE) |
|---|---|
| Volumes needing attention | Volumes marked degraded or faulted by Longhorn. Open Longhorn to inspect replicas and scheduling; detached volumes with unknown health are counted separately in the health chart. |
| Volumes with no recorded backup | Volumes whose last successful backup timestamp is zero. Check which ones actually need backups; this includes non-VM volumes. |
| Volumes last backed up over 7 days ago | Volumes with a successful backup older than seven days. Compare this review window with your own recovery requirement; never-backed-up volumes appear separately. |
| Which volumes need attention? | Up to 5 volumes degraded or faulted at the end of the selected period. Each entry names the PVC and Longhorn volume; 1 means that state is active. Check replicas and scheduling in Longhorn. Open the values table for every affected volume. |
| Which volumes have no recorded backup? | Up to 5 volumes with no successful backup timestamp. Each entry identifies the PVC and Longhorn volume; 1 means no recorded backup. Open the values table for the complete list, then compare it with your backup policy. |
| Which backups are older than 7 days? | Days since the last recorded successful backup, with PVC and volume names. Up to 5 oldest entries; open the values table for all matches. Check the backup schedule and destination against your recovery requirement. |
| Volume count by health | Number of volumes in each Longhorn health state. Unknown often occurs for detached volumes and does not mean healthy. Select a volume to investigate it. |
| Volume count by attachment state | How many volumes are attached, detached or changing state. Detached can be normal for stopped VMs and does not mean that a disk should be deleted. |
| Time to read or write a storage volume (ms) | Current average response time reported by Longhorn for active volumes, in milliseconds. Compare with VM disk latency to locate storage delays. |
| Storage read and write operations (operations/s) | Read and write operations per second reported by Longhorn. More activity is not automatically a problem; compare with response time. |
| Days since the last successful backup | Age of each non-zero last-backup timestamp. Missing data can mean no recorded backup; check the separate count above. |
| Backup count by status | Number of backup records in each status. Completed is metadata from Longhorn; it does not verify backup accessibility or a successful restore. |
| Reported snapshot data per volume | Sum of reported snapshot sizes for each volume. Shared data and replicas mean this is not physical space usage or guaranteed reclaimable space. |
| Size assigned to each volume | Provisioned logical capacity of each volume. Physical usage depends on written data, snapshots and replicas. |
| Physical storage used and available capacity | Longhorn-managed capacity, used space and reserved space on each host. Includes all volumes in the cluster, regardless of the volume filter. |
| Disk capacity promised to replicas | Logical capacity scheduled for Longhorn replicas. Thin provisioning can make this exceed physical capacity; it is different from bytes already written. |

## Virtualization · VMware Import Progress

Which VMware imports have finished, failed or are still being processed by VM Import Controller?

| Panel | What it shows (description in SUSE) |
|---|---|
| Import records | Number of import records retained by VM Import Controller. Deleting a record removes it from this current inventory, even if the VM still exists. |
| Completed imports | Imports for which the controller recorded the VM starting. Check the guest and application separately before accepting the migration. |
| Failed or invalid imports | Import records classified as failed or invalid. Inspect the controller resource and events for the cause before retrying. |
| Imports still in progress | Records still pending or being processed. Compare the current stage and time since the last update; a long transfer can be legitimate. |
| Current stage of each import | The legend identifies each import and the stage recorded by the controller. A line at 1 marks the recorded stage; it is not a completion percentage. |
| Import controller: incoming network traffic (bytes/s) | Receive bytes per second per Pod interface, averaged over five minutes. Includes all imports and control traffic; not transfer speed for one VM. |
| Import controller: outgoing network traffic (bytes/s) | Transmit bytes per second per Pod interface, averaged over five minutes. Disk export and image serving are separate stages; do not add receive and transmit as unique migrated bytes. |
| Import controller: CPU used (mCPU) | CPU used by each controller container over five minutes. 1000 mCPU equals one CPU core. Compare a slowdown with CPU, memory and network together. |
| Import controller: memory used | Working-set memory per controller container. Compare the trend with its configured limit and logs. |
| Shared image services: incoming network traffic (bytes/s) | Network receive rate for Longhorn backing-image managers and data sources. These services also handle non-import images; this is shared infrastructure traffic. |
| Shared image services: outgoing network traffic (bytes/s) | Network transmit rate for shared image services. Interface labels keep management and storage networks separate. This is not attributed to the selected import. |
| Can we collect import performance metrics? | 1 means the kubelet metrics endpoint answered; 0 means failure. This does not prove matching importer Pods exist. Check TLS, TCP/10250 and nodes/metrics access if collection fails. |
| Can we read the import inventory? | 1 means recent API reads succeeded; 0 means they failed or became stale. This must work before a zero import count can be trusted. |
| Disk images ready for the VM | Percentage of recorded disks marked ready. Even at 100%, VM creation and boot may still be pending; this is not transfer progress. |
| Total, ready and failed disks per import | Counts of disk objects recorded for each import. Compare ready with total; a failed disk requires checking controller events. |
| Time since an active import was created (seconds) | Elapsed time including queueing and all processing stages. This does not predict when the import will finish. |
| Time since an active import last changed status (seconds) | Age of the latest recorded condition. Long copy stages may have no updates, so an old condition alone does not prove a stalled transfer. |
| Source disk capacity recorded by the import | Logical disk sizes read from the controller. These are not bytes already transferred or measured storage usage. |
| Time spent in recorded import stages (seconds) | Duration of stages with explicit start and end timestamps. These intervals do not measure the entire migration or application acceptance. |

## Applications · Traffic, Errors & Speed

How many requests reach the application, how often do they fail, and how long do they take?

| Panel | What it shows (description in SUSE) |
|---|---|
| Requests per second | Average application traffic during the selected period. Fractional values are normal: 0.5 requests/s means about one request every two seconds. |
| Requests in the selected period | Estimated number of completed requests in the selected time range. Counter sampling can make the estimate fractional; the display rounds to whole requests. |
| Server errors in the selected period | Estimated number of HTTP 5xx responses in the selected range. Check affected routes and application logs. |
| Successful responses and redirects | Percentage of measured requests with HTTP 2xx or 3xx responses during the selected period. Compare with both client and server errors; no traffic cannot establish success. |
| Requests ending in a server error | Percentage of completed requests with an HTTP 5xx response. Timeouts before instrumentation may not be counted. |
| Response time for 95% of requests (ms) | About 95% of measured requests completed within this time. This estimate uses histogram buckets; a few slow requests can still take longer. |
| Traffic by application route | Requests per second for each measured route, such as an API endpoint. Compare traffic changes with errors and response time. |
| Successful responses and errors over time | Traffic grouped by response type. HTTP 4xx usually indicates a rejected client request; HTTP 5xx indicates a server-side failure. |
| Where and when requests fail | Error requests per second by route. Select a time with an increase and inspect that application's logs or traces. |
| Errors by route and response code | Estimated errors in the selected period, grouped by application, route and code. Read the legend or open details to identify repeated failures. |
| Response time over time (ms) | Compare typical and slow-request response times. A rising tail can reveal slow requests hidden by the average. |
| Requests by route in the selected period | Estimated requests per application route. These totals describe the selected period; a flat line is a period summary, not a traffic trend. |
| Slowest applications (ms) | Applications with the highest response time for 95% of requests. Compare traffic volume because low sample counts can make this estimate unstable. |
| Requests without server errors | Share of completed requests that did not return HTTP 5xx over the last five minutes. This is request-based availability, not measured uptime. |
| How quickly errors use the allowed budget (times the allowed rate) | 1 means errors consume the allowed budget at the planned rate; 10 means ten times that rate. Compare both windows and your agreed availability target. |
| How old are the request measurements? (seconds) | Seconds since the newest request-counter sample. A counter may stay unchanged with no traffic while its samples remain fresh. |

## Traefik · Incoming Traffic & Errors

Are requests reaching applications through Traefik, and where are errors or delays occurring?

| Panel | What it shows (description in SUSE) |
|---|---|
| Requests per second | Incoming traffic averaged over the last five minutes. Fractional rates are normal and do not imply a fractional request. |
| Average response time (ms) | Average time for completed requests over five minutes. Compare with the 95% and 99% response-time tiles to find slow outliers. |
| Incoming traffic over time | Requests per second averaged over five minutes. Look for traffic changes at the same time as errors or delays. |
| Requests in the selected period | Estimated completed requests during the selected time range. Sampling estimates are displayed as whole requests. |
| Rejected requests: HTTP 4xx | Estimated HTTP 4xx responses in the selected period. Check authentication, permissions and invalid paths; these are not automatically server outages. |
| Server errors: HTTP 5xx | Estimated HTTP 5xx responses in the selected period. Review backend availability and logs for the affected application. |
| 95% of requests within (ms) | About 95% of requests completed within this time over the last five minutes. Some requests can be slower; compare the 99% tile. |
| 99% of requests within (ms) | About 99% of requests completed within this time over five minutes. This highlights the slowest requests and is less stable with little traffic. |
| Requests per application in the selected period | Estimated traffic totals per application. A flat line is a summary for the selected period, not a trend. |
| Server-error percentage by application | Percentage of completed requests returning HTTP 5xx per application during the selected period. Inspect the busiest and highest-error applications together. |
| Traffic by application | Requests per second sent through Traefik to each application. Compare with application instrumentation when investigating a difference. |
| Traffic by HTTP response code | Requests per second grouped by response code. Use this to distinguish successful responses, redirects, rejected requests and server errors. |
| Response time over time (ms) | Average and percentile response times through Traefik. A higher 99% line reveals slow requests that the average may hide. |
| Slowest applications through Traefik (ms) | Response time for 95% of requests by application. Includes the path measured by Traefik, which differs from time measured inside an application. |
| Data transferred per second (bytes/s) | Request and response bytes per second measured by Traefik. Compare with traffic to spot unusually large payloads. |
| Days until certificates expire | Time remaining before Traefik TLS certificates expire. A negative value means expired. This covers the whole selected cluster. |
| Requests by application, code and method | Estimated request totals for the selected period. Use the labels to identify which application, HTTP code and method account for the traffic. |
| Server errors in each time interval | Estimated HTTP 5xx responses per chart interval and application. Each point covers the interval ending at its timestamp; inspect logs at the same time. |
| Rejected requests in each time interval | Estimated HTTP 4xx responses per chart interval and application. Compare bursts with authentication changes, invalid requests or scans. |
| Open connections | Concurrent connections by Traefik entry point and protocol. This is not a request count and is not narrowed by application filters. |
| Can we collect Traefik metrics? | 1 means the endpoint answered; 0 means collection failed. No series can mean no discovered target. This is a collection check, not application health. |

## Kubernetes · Cluster Health

Are servers and applications available, and is the cluster running out of resources?

| Panel | What it shows (description in SUSE) |
|---|---|
| Servers ready to run workloads | Percentage of known nodes reporting Ready. A missing or unready server needs investigation before capacity planning. |
| Servers with working OS metrics | Percentage of known servers with successful operating-system collection. Missing visibility is different from an unavailable server. |
| Pods needing attention | Count of pods in concerning states, excluding completed jobs. Use the detail list to see whether the issue is scheduling, startup or readiness. |
| Which pods need attention? | Names and observed states of affected pods. Read the legend or open details; lines mark inventory entries, not a performance trend. |
| Which pods restarted in the last hour? | Estimated container restarts grouped by pod. Inspect previous logs and termination reasons; a restart alone does not prove a memory problem. |
| Which applications have unavailable replicas? | Up to 5 affected applications at the end of the selected period, with the number of unavailable replicas beside each name. For example, 1 means one configured instance is not available. Check scheduling, image pulls and readiness probes. A short gap during an update can be normal. |
| Host filesystem space used | Percentage used on monitored host filesystems. Review the device and mount point; not every exposed device is a separate physical disk. |
| Space used on host filesystems | Bytes used on each monitored server filesystem. Compare the same filesystem with capacity and percentage used. |
| Size of host filesystems | Total measured filesystem capacity. Device filters exclude several duplicate or irrelevant mounts. |
| Filesystem file entries used | Percentage of inode entries used. A filesystem can run out of file entries even when bytes remain available. |
| Application volume space used | Percentage used in PVC filesystems that expose usage metrics. Raw block volumes and some drivers cannot supply this measurement. |
| Space used in application volumes | Bytes used in measured PVC filesystems. Match the namespace and volume when comparing with capacity. |
| Size of measured application volumes | Reported filesystem capacity for measured PVCs. This is not the total physical capacity of the storage system. |
| Volumes without filesystem usage data | Claims lacking filesystem usage measurements. This can be expected for block volumes; verify the storage mode before treating it as a fault. |
| Storage volumes by status | Current Kubernetes PV status listed by volume. Released requires an ownership and retention review; it is not permission to delete data. |
| Application storage requests by status | Current PVC status listed by claim. Pending means the requested storage is not yet bound; inspect provisioning and scheduling events. |
| Can database members see a leader? | Each etcd member should report 1 when it sees a leader. A single healthy member does not provide redundancy. |
| Database leader changes in the last hour | Leader changes observed by each database member. Repeated changes may indicate instability; do not sum members as distinct elections. |
| Database writes waiting for agreement | Proposals waiting for consensus in etcd. A sustained queue can explain slow cluster API operations. |
| Agreed database writes not yet applied | Difference between committed and applied proposals. A growing gap suggests the database is struggling to apply changes. |
| Failed database operations in 15 minutes | Estimated failed proposals recorded by each etcd member. Correlate with API errors, leader changes and storage latency. |
| Database log write time: slowest 1% (ms) | 99th-percentile time to flush the etcd write-ahead log, in milliseconds. Slow storage can affect the whole cluster control plane. |
| Database commit time: slowest 1% (ms) | 99th-percentile etcd backend commit time. Compare with disk latency and pending operations. |
| Database size compared with its quota | Percentage of etcd's configured storage quota used. Review compaction and maintenance procedures before the quota is exhausted. |
| Can we collect cluster database metrics? | 1 means an etcd endpoint was collected successfully. Empty data is expected when optional etcd collection is disabled. |
| Time for database members to communicate (ms) | 99th-percentile network round-trip time between etcd members. A single-member cluster may have no peer measurements. |
| CPU used on each server | Percentage of server CPU time spent busy. Includes applications and platform processes. |
| Memory available on each server | Percentage of RAM the operating system considers available, including reclaimable cache. Lower means less headroom. |
| Disk operations waiting or in progress (operations) | Average disk operations in progress over the measurement window. Compare with disk response time to interpret a sustained queue. |
| Host memory pages fetched from disk (pages/s) | Major page faults per second on each host. Compare with available memory and application latency. |
| Busiest server: CPU used | Highest measured server CPU-use percentage. Colors are review thresholds; inspect duration and user impact before acting. |
| Busiest server: memory used | Highest server memory-use percentage after allowing for reclaimable memory. Review available RAM and workload growth. |
| Fullest host filesystem | Highest filesystem-use percentage among measured hosts and mounts. The label identifies the filesystem to investigate. |
| Network interface errors (errors/s) | Receive and transmit errors per second by interface. Sustained increases need a network and host review. |
| Metrics waiting to be delivered | Bytes queued by collectors for delivery to SUSE Observability. A growing queue can indicate a network, authentication or backend issue. |
| Metric delivery retries in 15 minutes | Estimated retry attempts by collectors. Inspect collector logs and delivery queues when retries persist. |
| Time to read or write a host disk (ms) | Average response time per completed host disk operation. Idle disks have no meaningful response-time average. |
| Unavailable application replicas | Total number of configured application instances that are not available. For example, 3 configured and 2 available means 1 unavailable replica. This counts instances, not applications or lost data. Check the named applications below; brief gaps during updates can be normal. |
| Container restarts in the last hour | Estimated restart count across selected pods. Rounded to whole restarts for display; counter sampling can affect estimates. |

## Kubernetes · Application Resource Usage

Are applications using the CPU and memory reserved for them, or approaching their limits?

| Panel | What it shows (description in SUSE) |
|---|---|
| CPU used by the five busiest pods (mCPU) | Actual CPU use for the five pods selected as busiest at the end of the period. Compare the same names in reserved CPU and CPU limits. |
| CPU reserved for those same pods (mCPU) | Scheduling requests for the same five pods. Reserved CPU is not actual consumption; 1000 mCPU equals one CPU core. |
| CPU limit for those same pods (mCPU) | Configured CPU ceiling for the same five pods. A missing limit is different from a zero-CPU allowance. |
| Pods with no CPU reservation | Count of pods with at least one container missing a CPU request. Review their scheduling requirements before setting values. |
| Pods with no CPU limit | Count of pods with at least one container missing a CPU limit. Whether a limit is needed depends on workload policy. |
| Highest Pod CPU % | Highest measured CPU use relative to a configured limit. Compare with throttling and latency; a high percentage alone does not prove a user impact. |
| Memory used by the five busiest pods | Working-set memory for the five pods selected as busiest at the end of the period. Compare the same names in reserved memory and limits. |
| Memory reserved for those same pods | Scheduling memory requests for the same five pods. These reservations differ from actual memory use. |
| Memory limit for those same pods | Configured memory ceiling for the same pods. Exceeding a container limit can cause an out-of-memory termination. |
| Pods with no memory reservation | Count of pods with at least one container missing a memory request. Review sizing and scheduling requirements. |
| Pods with no memory limit | Count of pods with at least one container missing a memory limit. Review workload policy and host capacity before choosing limits. |
| Highest Pod memory % | Highest memory-use percentage relative to a configured limit. Check the trend and container termination reasons before changing resources. |
| Which pods have missing resource settings? | The legend lists affected pods and missing settings. A line is an inventory marker, not a trend; use the details link for columns. |
| Pods using the largest share of their memory limit | Five highest memory-to-limit percentages. A sustained rise toward the limit may need investigation; check the relevant containers. |
| CPU used compared with CPU reserved | CPU use divided by the scheduling request. More than 100% is possible and does not by itself mean a limit was exceeded. |
| CPU work delayed by configured limits | Share of CPU scheduling periods in which containers were throttled. Compare with application response time before raising limits. |
| Pod memory: working set and resident memory | Two views of memory for the same busiest pods. Working set and resident memory overlap; do not add them together. |
| Can we read pod resource settings? | 1 means pod configuration collection is working; 0 means it failed. Check this before trusting missing-setting counts. |
| Which pods exceed 80% of their CPU limit? | Up to five pods with the highest use above the review threshold. Open the values table for every affected pod. Investigate throttling and demand before changing limits. |
| Which pods exceed 80% of their memory limit? | Up to five pods with the highest use above the review threshold. Open the values table for every affected pod. Compare sustained usage and recent memory-related restarts. |
| Pods over 80% CPU limit | Count of measured pods above the CPU review threshold. See the adjacent detail list for the affected names. |
| Top 5 pods without CPU requests: current CPU use (mCPU) | Five highest measured values and five-minute CPU use of affected running pods. Review peak demand and scheduling needs before choosing requests. |
| Top 5 pods without CPU limits: current CPU use (mCPU) | Five highest measured values and five-minute CPU use of affected running pods. CPU limits are a policy choice; check throttling and latency before adding them. |
| Top 5 pods without memory requests: current memory use | Five highest measured values and five-minute working-set use of affected running pods. Review sustained and peak use before choosing requests. |
| Top 5 pods without memory limits: current memory use | Five highest measured values and five-minute working-set use of affected running pods. Review application peaks and recent OOM events before choosing limits. |
| Pods over 80% memory limit | Count of measured pods above the memory review threshold. See the detail list and inspect individual containers. |

