# Alerts: what is covered and what is not

The five modules publish **39 enabled monitors** in total. They do not configure notification channels. A monitor evaluates a query and attaches its result to a topology component; routing an alert to a person is a separate SUSE configuration.

> Community lab thresholds, not recommended for production without validation against your own workload and incident policy.

## Coverage by module

| Module | Checks | Important limits |
|---|---|---|
| Virtualization (7) | VM guest memory, CPU scheduling wait, disk response, guest filesystem use; metric collection; Longhorn degraded/faulted volumes | VM checks need the applicable guest metrics. Longhorn rules attach only volumes with PVC metadata. Host-memory and etcd rules belong to Kubernetes. |
| Imports (3) | Failed/invalid import records, unsuccessful inventory reads, failed optional kubelet performance scrape | Import events attach to the namespace and name the import in the title. No duration, per-VM throughput or completion-percentage alert. |
| Kubernetes (21) | Node memory/filesystems/inodes, PVC space/trends, container memory limits, etcd, collector health | Only collected signals are evaluated; etcd is opt-in. A missing CPU limit is not automatically an incident. |
| Traefik (6) | HTTP 5xx, p95 latency, certificate expiry, metric and ingress inventory collection | Requires traffic and relevant metrics; thresholds are not an availability SLO. |
| Applications (2) | HTTP 5xx and p95 latency | Requires compatible instrumented HTTP metrics and traffic. |

## New storage and import checks

- **Degraded Longhorn volume for 5 minutes:** warning (`DEVIATING`). The alert names the cluster, PVC namespace/name and volume. Inspect replica health and scheduling.
- **Faulted Longhorn volume for 1 minute:** critical. Check workload impact and replica availability; do not delete disks based on the alert.
- **Failed or invalid import for 5 minutes:** warning. Inspect the named import and controller conditions. An old failed record remains a failed record; it is not silently treated as a new incident.
- **Import inventory unavailable for 3 minutes:** warning on the cluster. Check the collector, CRD, read access and metric delivery.
- **Import performance scrape failing for 3 minutes:** warning on the node. Applies only with performance collection enabled. Check TLS/10250, nodes/metrics access and collector memory.

The windows use observed samples, evaluated every 60 seconds. They do not prove uninterrupted coverage between scrapes. A disappeared target can produce no series; monitor collection/workload health as well. None of these rules proves that a notification was delivered.

## Deliberately left as investigation panels

- No recorded backup / backup older than seven days: review against your backup policy and RPO. Temporary images and disposable volumes may not need backups. A successful backup record does not prove a successful restore.
- Long imports / low network traffic: duration and expected throughput depend on disk size, source, stage and infrastructure. Shared image-service traffic cannot be assigned reliably to one VM.
- Missing requests or limits: inspect the named Pods and their current/peak demand. A CPU limit is a policy choice, not always a fix.
- Capacity forecasts and N−1 estimates: planning context, not a guarantee of successful failover.

## Check monitors and notifications

1. Open **Monitors** in SUSE and find the `SRE ·` rules for your module. Confirm they are enabled and evaluating.
2. Inspect a result and confirm it is attached to the intended PVC, node, namespace or cluster. A valid query without a matching topology component is not enough.
3. Read the remediation hint and compare it with the source before taking action.
4. Configure your own [SUSE notifications](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/alerting/notifications/configure.html) if needed, then test delivery through the intended channel. This project has not tested email or other external notification delivery.

Use a safe, planned failure test before relying on a rule. This lab did not fault disks, stop VMs or start a failed migration to trigger alerts. Helm upgrades reapply managed definitions; review and maintain changed thresholds in the chart source or create separately owned rules.

## Exact installed rules

Names include the main threshold/time window. Inspect the chart catalog for the complete query, traffic gates, topology mapping and remediation.

| Rule | Failure state |
|---|---|
| etcd without leader · 1m | CRITICAL |
| etcd leader changes above 3 in 15m | DEVIATING |
| etcd failed proposals in 15m | DEVIATING |
| etcd pending proposals above 100 | DEVIATING |
| etcd apply backlog above 1000 | DEVIATING |
| etcd WAL p99 above 10ms | DEVIATING |
| etcd commit p99 above 25ms | DEVIATING |
| etcd database above 80 percent quota | DEVIATING |
| etcd scrape failing · 3m | CRITICAL |
| filesystem below 10 percent available · 15m | CRITICAL |
| filesystem below 10 percent free inodes · 15m | CRITICAL |
| host OS below 10 percent available RAM · 15m | DEVIATING |
| missing node OS telemetry · 5m | DEVIATING |
| PVC filesystem below 10 percent available · 15m | CRITICAL |
| container working set above 95 percent limit · 5m | DEVIATING |
| VM guest OS below 10 percent available RAM · 15m | DEVIATING |
| Traefik certificate expires within 30 days | DEVIATING |
| Traefik certificate expires within 7 days | CRITICAL |
| PVC filesystem projected full within 12h | CRITICAL |
| PVC filesystem projected full within 96h | DEVIATING |
| metric collection backlog persists · 10m | DEVIATING |
| metric collector discarded data · 15m | CRITICAL |
| etcd telemetry disappeared · 5m | CRITICAL |
| Ingress inventory collection failing · 3m | DEVIATING |
| Traefik metrics scrape failing · 3m | DEVIATING |
| host disk response above 20ms · 10m | DEVIATING |
| VM CPU scheduler wait above 10 percent · 10m | DEVIATING |
| VM disk response above 20ms · 10m | DEVIATING |
| Traefik HTTP 5xx above 5 percent · 5m | DEVIATING |
| Traefik p95 response above 3s · 10m | DEVIATING |
| instrumented app HTTP 5xx above 5 percent · 5m | DEVIATING |
| instrumented app p95 above 3s · 10m | DEVIATING |
| VM filesystem above 90 percent used · 15m | DEVIATING |
| Virtualization metrics scrape failing · 3m | DEVIATING |
| Longhorn volume degraded · 5m | DEVIATING |
| Longhorn volume faulted · 1m | CRITICAL |
| VMware import failed or invalid · 5m | DEVIATING |
| VMware import inventory unavailable · 3m | DEVIATING |
| Import performance collection failing · 3m | DEVIATING |
