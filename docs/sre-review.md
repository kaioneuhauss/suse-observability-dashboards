# SRE review and production acceptance

This page records what each dashboard is for, what was checked on 2026-11-09, and what still needs a production acceptance test. The project is community maintained and is not an officially supported SUSE integration. Keep the modules that answer questions you actually operate; do not install all five just to make the catalog look complete.

The review follows the [four golden signals](https://sre.google/sre-book/monitoring-distributed-systems/): traffic, errors, latency and saturation. Infrastructure dashboards also need resource identity, collection health and a next investigation step. A count without the affected resource is insufficient for remediation. Alert thresholds are starting points; [multi-window SLO burn-rate alerts](https://sre.google/workbook/alerting-on-slos/) require a real service objective and traffic policy.

## Dashboard decisions

| Dashboard | Keep when | What the operator should do | Boundary |
|---|---|---|---|
| **Virtualization · VM & Host Overview** | You run Harvester VMs | Check running VM count, host pressure, the busiest VM and data age; select the named VM for its memory and filesystem details | Guest memory/filesystem need guest statistics. A stopped VM has no current usage. |
| **Virtualization · VM Performance** | You investigate slow VMs | Compare CPU scheduler wait, CPU use, guest memory pressure and disk response for the same VM and time window | CPU wait is a KubeVirt signal, not VMware CPU Ready. Idle disks have no defined latency. |
| **Virtualization · Capacity Planning** | You plan placement and growth | Compare assigned vCPU/RAM with sampled demand and collection coverage; check whether the largest host could fail | The N−1 memory balance is a planning estimate, not a failover guarantee. A new collector has less than 24 hours of history. |
| **Virtualization · Storage & Backups** | You use Longhorn | Start with the unhealthy-volume list, then inspect its PVC/VM or Pod owner and backup age | The count covers all selected Longhorn volumes, including non-VM ones. No recorded backup is not automatically a policy violation or proof of restore failure. |
| **Virtualization · VMware Import Progress** | VM Import Controller is installed | Find failed/active records and disk readiness; optionally correlate shared importer CPU, memory and network use | Retained CRs are the inventory. No active import was available for a transfer test. Coriolis and per-VM bandwidth/ETA are outside this contract. |
| **Kubernetes · Cluster Health** | You operate Kubernetes/RKE2 or the Harvester control plane | Start with ready nodes, unavailable workload replicas and named Pods; then inspect host, PVC and optional etcd panels | The 40 panels are a drill-down view. Only enable etcd collection when the local endpoint exists. Workload replica gaps during rollout need context. |
| **Kubernetes · Application Resource Usage** | You set Pod requests/limits | Use the named Pod lists and measured values to investigate pressure; compare use with requests and limits | A missing CPU limit can be intentional. No usage sample is not zero. |
| **Traefik · Incoming Traffic & Errors** | Traefik exposes Prometheus metrics | Filter cluster, namespace and backend; follow request rate, 5xx and response time at ingress | It measures the ingress path, not application-internal latency. Service mapping requires matching ingress inventory. |
| **Applications · Traffic, Errors & Speed** | Applications export the documented HTTP metric contract | Select an instrumented service; review traffic, failed routes, p95 and request-data age | Traces alone do not supply these metrics. It measures application HTTP handling, which can differ from Traefik. |

The Traefik and Applications dashboards serve different measurement points. Install one or both according to what you need to troubleshoot. Imports is optional even when Virtualization is installed. The two Kubernetes dashboards are complementary: cluster health for availability and infrastructure, resource usage for Pod sizing.

## Evidence from the current lab

On **2026-11-09**, chart `1.8.0` and SUSE Observability server `2.10.2` were checked without changing the live releases:

- All **nine** project dashboards were stored in SUSE; the native Kubernetes dashboard remained separate. All **39** project monitors were enabled, had a successful recent run, reported no execution errors and had no unmatched topology results. This does **not** prove notification delivery.
- The native SUSE metrics API accepted **8,854 query/filter combinations** across all nine dashboards with **zero errors** and **zero non-finite values**. That covers the available single-value filter paths, representative multi-select, Everything and a nonexistent cluster. It is not a pixel-level browser test or every possible time range.
- All **62** currently visible `up` target series reported `1`; `time() - timestamp(up)` placed their samples between about **4 and 28 seconds** old at the snapshot. This verifies live target collection, not every optional guest or application metric.
- With all filters set to Everything, the only empty queries were **active import age** and **time since the last active import status change** (there was no active import), plus **Longhorn read latency** at an instant with no reads. Empty results are not displayed as zero or healthy.
- Direct Harvester API comparisons matched **10 running VMs**, **50 assigned vCPUs**, **100 GiB guest RAM**, **184 Longhorn volumes** by state (41 healthy, 1 degraded, 142 unknown) and **8 retained import records**. The dashboard showed one degraded volume, matching Longhorn. The 183 volumes with no recorded backup are an inventory observation; backup policy must decide which ones require protection.
- The four missing-request/limit Pod summaries were checked against running-container specs in **all three clusters**: 53/83/53/82 for Harvester, 45/58/45/58 for Observability and 27/43/27/43 for Rancher (CPU request, CPU limit, memory request, memory limit). All 12 dashboard counts matched their source snapshots.
- Filters exposed both instrumented applications (`brasil-dados-api`, `request-lab`), Traefik clusters `observability-cluster` and `rancher-kaio`, the available namespaces/backends and all 10 VM names. HTTP period totals passed **18 cross-resolution checks** at 60, 300 and 900 seconds, including route-total reconciliation.
- The repository's **69 unit tests** and Helm render/lint checks passed. The last live browser walkthrough of all nine dashboards was on **2026-11-03**. Browser access was not available for a fresh visual walkthrough on 2026-11-09; query/API validation above is current.

These checks validate the observed metric contract and source counts in this lab. They do not prove that every optional signal exists on every Kubernetes, Harvester, Agent or application version. See [metric definitions and limits](metric-contracts.md) and [every panel explained](panel-guide.md).

## Production acceptance

Before relying on this project for an incident response workflow, record the result of each gate in the target environment:

1. **Version and ownership:** confirm a supported SUSE server/Agent/Harvester combination from the official documentation, one collector owner for each target, and one publisher per module per SUSE instance. Test the target chart version; the lab's split `telemetry`/`content` deployment does not prove a fresh `mode: all` deployment on every platform.
2. **Security and delivery:** use the dedicated publisher role, private Secrets, valid CA/TLS, scoped network access and approved registries. Verify all images and the checksum-pinned publisher CLI can be fetched, or provide an approved mirror. Review the Longhorn TCP/9500 exposure before enabling its policy.
3. **Data accuracy:** compare known VMs, volumes, Pods, ingress requests and instrumented app requests with their source APIs. Verify sample age, units, labels, query filters, missing-data behavior and retention. Run an actual VMware import before accepting its active-stage/performance panels.
4. **UI and operations:** open every installed dashboard in the target browser, exercise cluster/namespace/resource filters, inspect full resource names and detail links, then test a safe planned failure. Confirm each monitor maps to the right component and a routed notification reaches the intended person. Tune thresholds to the actual workload and SLO.
5. **Platform resilience:** verify SUSE server sizing, persistence, ingress, DNS, backup **and restore**, recovery after restart, and normal traffic during a chart upgrade/rollback. The dashboard chart cannot validate or repair server backups.

The current lab is **not production accepted**: the most recent inspected ClickHouse full-backup Pod failed to resolve its backup Service, and the CronJob's last reported successful full backup was **2026-10-28**. A later incremental backup completed on 2026-11-09, but no restore was tested. One Longhorn volume remains degraded, and the related monitor reports it. The active-import path and notification delivery also remain untested. Resolve these as separate platform/workload tasks before making a production claim.
