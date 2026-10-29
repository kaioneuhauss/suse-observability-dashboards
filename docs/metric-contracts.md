# Metric definitions and limits

A query can run successfully and still be interpreted incorrectly. Check its labels, unit, time window, denominator and behavior when data is missing. Compare values with the source system. The lab results are recorded in [Lab validation](lab-validation.md).

## Units and formulas

| Metric family | How it is used |
|---|---|
| KubeVirt CPU | `rate(cpu_usage_seconds_total[5m])` gives consumed CPU cores. Percentage divides this by configured cores × sockets × threads, not CPU requests. |
| vCPU waiting | Seconds counters become a rate per vCPU. Deduplicate by VM/id, average across vCPUs and multiply by 100. This is not identical to VMware CPU Ready. |
| Guest memory | Estimated use is `available - usable`. Guest available memory, QEMU RSS and configured memory describe different things. |
| Guest swap | KubeVirt exposes cumulative traffic as a gauge. Positive 5-minute change / 300 is an estimate affected by resets; it is not treated as a normal counter. |
| Guest disk latency | Rate of accumulated seconds / rate of operations in the same window, multiplied by 1,000 for ms. No operations means no defined average latency. |
| Host CPU | Rate by mode and CPU, averaged across CPUs. Busy CPU is 1 − idle. Capacity counts logical CPUs. |
| Host memory | `MemTotal - MemAvailable`, in bytes. Available memory includes reclaimable cache. |
| Agent CPU | `container_cpu_usage` is already in nanocores. Divide by 1,000,000 for mCPU; do not apply another `rate()`. Inventory requests/limits are cores, multiplied by 1,000 for mCPU. |
| Agent memory | Working set and RSS are bytes with different meanings. Inventory memory requests/limits are also bytes. |
| Longhorn states | Robustness and attachment have one 0/1 series per state. Count active states after deduplicating the volume, not the number of exposed series. |
| Longhorn I/O | Latency gauges are nanoseconds; divide by 1,000,000 for ms. IOPS and throughput gauges are already rates. |
| Longhorn capacity | Provisioned volume size is logical. Node usage/capacity is physical managed storage. Scheduled capacity is logical replica reservation and can exceed physical capacity. |
| Longhorn backups | Last backup is a Unix timestamp or zero. Calculate age only for positive timestamps. Snapshot size is not guaranteed reclaimable space or total replicated physical usage. |
| HTTP | Calculate counter rates before aggregation. Histogram values are seconds; multiply quantiles by 1,000 for ms. Percentiles depend on bucket boundaries. |
| HTTP period totals | `range_sum(increase(counter[${__interval}]) …)` sums non-overlapping increments using the resolution resolved by SUSE. `[1i]` works in the backend but is rejected by the SUSE 2.10.2 parser. Do not freeze the increase at `@ end()` or assume a fixed one-minute step. |
| HTTP availability | 1 − the 5xx share of completed requests. With no traffic, the ratio is undefined. It is not uptime; 4xx does not consume this particular error budget. |
| VM Import Controller | Inventory of retained CRs. `diskSize` is logical bytes. Intervals use explicit timestamps, not estimated transfer progress or full migration duration. |

`percentunit` takes a ratio from 0 to 1. `percent` takes a value already multiplied by 100. IEC byte units use powers of 1,024. Joins explicitly normalize OTLP's `k8s_cluster_name` and remote write's `cluster_name`.

State and configuration metrics are deduplicated by logical identity before counting. Counter rates are calculated per series before aggregation to account for resets. This is not a reason to run duplicate collectors: each target set should have one collection owner.

## Missing data and history

- Missing telemetry is not assumed to be zero or healthy. Count fallbacks require the relevant inventory/state family. Missing backup metrics do not mean zero unprotected volumes.
- An idle disk can have zero IOPS and no latency value. A stopped VM has no current usage. Missing guest statistics can hide memory or filesystem data. Check collection health to distinguish these cases.
- Old series may remain visible during the backend lookback period. Check sample freshness, not just whether a line exists.
- A 24-hour p95 uses only the history actually collected. New installations do not have a full day of data. Rates, quantiles and sampled counts have limits; missing samples and resets affect them.
- HTTP totals were compared across 60-, 300- and 900-second steps for the same aligned window. Window boundaries, rounding and missing samples still depend on collection resolution.
- These queries use the SUSE MetricsQL backend. They are not automatically portable to plain Prometheus.

## Check again when versions change

The implementation was checked against [KubeVirt v1.7.4 metrics](https://github.com/kubevirt/kubevirt/blob/v1.7.4/docs/metrics.md), [Longhorn v1.11.2 volume metrics](https://github.com/longhorn/longhorn-manager/blob/v1.11.2/metrics_collector/volume_collector.go), [Longhorn backup metrics](https://github.com/longhorn/longhorn-manager/blob/v1.11.2/metrics_collector/backup_collector.go) and [VM Import Controller v1.8.2](https://github.com/harvester/vm-import-controller/tree/v1.8.2). Also see [MetricsQL](https://docs.victoriametrics.com/metricsql/) and [Traefik metrics](https://doc.traefik.io/traefik/observe/metrics/overview/).

After a platform or Agent upgrade, check metric types, labels and values against the source API again. Lab validation does not automatically cover another version, workload or instrumentation contract.

SUSE resolves `${__interval}` according to chart resolution; see its [query guidance](https://documentation.suse.com/cloudnative/suse-observability/latest/en/develop/reference/writing-promql.html). Acceptance by VictoriaMetrics alone does not prove acceptance by the SUSE API or UI. The [development guide](../dev/README.md) covers the optional native API audits.

## Actionable resource details (1.4.0)

CPU/memory threshold panels show each qualifying Pod and its measured percentage, at the selected end time, using the existing complete-running-container eligibility checks. Counts remain a compact summary. Missing-request/limit panels add the five highest measured Pod usages; their **Full names and values** link includes every matching measured Pod, not just the Top 5. Missing usage does not become zero. CPU is mCPU, memory is working-set bytes, and threshold table queries multiply the ratio by 100.

SUSE Observability 2.10.2 offers no native dashboard Table widget. We use per-series Stat cards for correctly paired names and values, and Metrics Explorer's Table view for full names. Hover truncated names or open the table. `sort_by_label` was rejected by the native API; enabling the TimeSeries legend's positional Last column is not a safe substitute on this version. Details links preserve dashboard filters, but check the Explorer time range before comparing numbers. No automatic resizing is performed.

## Import infrastructure performance (optional, 1.4.0)

Direct kubelet cAdvisor counters are renamed with `harvester_import_` to avoid colliding with other collectors. Network rates apply `rate(...[5m])` to each original series before deduplicating by cluster, namespace, Pod and interface. CPU is `1000 * rate(cpu_usage_seconds_total[5m])` in mCPU; working-set memory is a gauge in bytes. Container CPU/memory excludes the Pod sandbox. The default controller and image-service names/namespaces are allowlisted in the chart. No host-networked replacement or custom namespace is covered.

The controller handles multiple imports and serves exported images; its traffic includes control requests. Longhorn backing-image managers and data sources are shared infrastructure. The panels do not honor the individual import selector and do not claim per-import attribution, logical-byte transfer percentage, elapsed total migration time, unique transferred-byte totals, remaining time or link utilization. Network interfaces are kept separate; do not add receive and transmit as a single transfer amount.

Performance collection is opt-in. It requires Nodes discovery plus `nodes/metrics` read access, direct TCP/10250 and a trusted serving certificate with the node IP. No `nodes/proxy` grant is used. A failed scrape is `up=0`; no matching Pods is an empty performance chart, even if node collection is up. The inventory health check remains independent. Completed-import validation does not validate active VMware transfer throughput.

SUSE ingestion normalizes cAdvisor `pod` to `pod_name`. The collection allowlist uses the source label `pod`; dashboard selectors and aliases use the stored `pod_name`. A successful query with empty results is not acceptance when the matching source Pods exist.

## Resource labels and Pod-to-volume associations (1.7.0)

A short label is a display projection, not a new identity. Cards and selected long legends preserve the first 18 and last 8 characters with an explicit ellipsis. Full labels remain in each query result and in the **Full names and values** link. Two abbreviated names can collide; use the complete labels before acting. Top 5 determines membership, not a guaranteed descending visual order in the native renderer.

Storage details join Longhorn labels to the official Agent metric `kubernetes_state_pod_volumes_persistentvolumeclaims_readonly` by cluster, PVC namespace and PVC name. A metric value of zero means read/write, not an absent reference, so references are normalized with `0 * metric + 1`. Running/Pending Pod labels are retained, repeated collector series are deduplicated, and ambiguous PVC-to-volume matches are excluded from the join. Unmatched volumes remain visible with a PVC/volume fallback. Several consumers can produce several detail rows; summary counts still count unique volumes.

For KubeVirt hotplug disks, this Agent metric can report the parent `virt-launcher` Pod while the direct PVC mount is in its `hp-volume` child. This is an observed Pod association, not proof of a mounted filesystem, application health, VM ownership or safe deletion. No guest VM name is inferred from a PVC UUID. Freshness and source availability still need checking.

## VM storage association (1.8.0)

The existing Pod-to-PVC association is enriched with `kubevirt_vmi_info{phase="running",vmi_pod!=""}`. Join on cluster, PVC namespace and Pod name after explicitly renaming `vmi_pod`; do not parse a VM name from a Pod or PVC. Only unique launcher mappings are eligible. The result adds `vm_name` and changes the display consumer to `VM: ...`; its value, Pod identity and volume identity stay unchanged. Ordinary Pods and unmapped PVCs remain visible. Stopped VM definitions are not covered by this mapping.

In the tested 2.10.2 dashboard implementation, metric queries accept PromQL, alias and minimum step; they do not expose the component-identifier template supported by native metric bindings. Header links interpolate dashboard variables, not each returned metric series. Native resource-list shortcuts therefore have their own filters; click a resource name there to open its details.
