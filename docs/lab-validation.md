# Lab validation — October 26, 2026

This records what was checked in this lab. It is not a support matrix or a production certification. **This community project is not recommended for production.**

## 1.3.0 — Live removal and installation using Helm and kubectl

This run followed the module guides and the multiple-cluster layout. Cluster changes used direct `helm` and `kubectl` commands: no local installer script, Python helper or local SUSE CLI was used to remove or install the modules. Existing platform prerequisites were checked and reused; the SUSE server, Agents, Traefik configuration and VM Import Controller were not reinstalled.

### Procedure tested

1. Saved values and manifests for the 11 existing releases and recorded protected resource UIDs/specifications.
2. Added the public Helm repository and verified a downloaded 1.3.0 package against the validated artifact.
3. Upgraded the five existing 1.2.0 central publishers to 1.3.0 with their saved values and existing publisher identities. This adds the new cleanup hooks; the dashboard and monitor definitions are byte-for-byte unchanged.
4. Ran `helm uninstall` for six source collector releases and five central publishers. All commands succeeded. The nine project dashboards disappeared; the native SUSE dashboard retained its original ID. No project release remained in any cluster.
5. Reinstalled the six source releases and five central publishers using 1.3.0 packages from the public Helm repository and small values files. Source releases use `mode: telemetry`; central releases use `mode: content`. Existing Secret names, etcd collection and the approved Longhorn policy are documented optional settings.
6. Checked readiness, fresh samples, source comparisons and the SUSE dashboard interface.

### Results

- **11 releases deployed at revision 1**, with **24 ready collector Pods**. Successful publishing and cleanup Jobs disappeared automatically.
- **828 protected resources kept their UIDs and specifications** through removal and reinstallation: 86 in Observability, 29 in Rancher and 713 in Harvester. This run includes persistent volumes as well as workloads, PVCs, VMs, VMIs and Longhorn volumes, so its count is broader than the older 628-object check.
- Both demonstration applications, the official platform releases and metric history were preserved. Coriolis remained stopped. All 62 regular chart-owned resources were newly created during the reinstall; 13 project workload objects received new UIDs.
- All nine native Longhorn NetworkPolicies retained their UIDs and rules. The project policy was recreated with the same rule: TCP/9500 from the specified collector Pod labels **and** namespace together.
- **362 query checks passed** through the Kubernetes service proxy to VictoriaMetrics: every one of the 181 panel queries with Everything selected, plus the same queries with a nonexistent cluster. No execution errors or non-finite numbers. All 181 negative cases returned no series. The only two empty positive cases were active-import age/status-age panels, because all eight retained imports were complete.
- Source comparisons matched **10 running VMIs, 50 assigned vCPUs, 100 GiB of configured guest RAM, 184 Longhorn volumes and eight completed imports**. Longhorn reported 41 healthy, one degraded and 142 unknown volumes, matching the source. The degraded condition already existed before this run; storage was not changed to hide it.
- Five KubeVirt targets and one Longhorn target reported `up=1`; their samples were less than 30 seconds old at the freshness check. All 23 expected node, etcd and Traefik targets reported `up=1`. The import inventory reported healthy and recent data.
- Nine dashboards and 34 monitors were republished by the chart Jobs, which verify their persisted definitions. Integer counts and populated summary charts were checked in the SUSE UI.
- **61 local tests passed**. CI passed with Helm 3.19.0 and Helm 4.1.1. Package integrity, generation, deletion scope, identity reuse, opt-out/plan behavior and module isolation were checked. All 11 real configurations also passed Helm server dry-runs before any mutation.

### Corrections found while following the guide

- Helm 4 does not accept `helm list --all`; the guide now uses the compatible listing command.
- Not every collector has the release-instance label. Module checks now name the actual Deployments and DaemonSets, so the command checks the complete expected collector set instead of returning a misleading empty list.
- Successful Jobs are removed automatically in 1.3.0, so the guides check Helm status and dashboard results rather than requiring completed Jobs to remain visible.

This was a lifecycle and collection validation. The comprehensive native API/filter audit recorded under 1.2.0 was not rerun in full. No new migration, backup restore, failover, alert delivery or production-readiness test was performed. An empty result still needs an applicability check; it is not a healthy zero.

## 1.2.1 — Direct Helm documentation and distribution

This revision replaces the local installer helper with direct Helm and kubectl instructions and publishes versioned chart packages. It does not change dashboard queries, collector settings or publisher behavior. The checks for this revision are recorded separately below; the live metric evidence from 1.2.0 remains historical evidence, not a new collection run.

- **58 local tests passed**, including the published package digests and exact current-package/source comparison. The three tests specific to the removed installer helper were replaced by two repository-integrity tests.
- All five version 1.2.1 packages passed Helm lint. Existing Helm rendering and negative configuration checks passed.
- Packaged charts rendered with the 11 existing deployment configurations passed server-side admission dry-runs across Observability, Rancher and Harvester. Publishing hooks were excluded from this admission check because they already exist and are replaced by Helm during a real upgrade.
- Documentation links and YAML examples were checked. End-user command blocks contain only Helm and kubectl. Generated chart and panel-guide sources were repeatable.
- No new install, uninstall or server upgrade was performed for this documentation revision. Existing live-metric results below were not rerun or presented as new results.

## 1.2.0 — Clean installation and dashboard review

- Reviewed 161 metric panels across nine dashboards: English titles and explanations, integer counts, explicit units and sections built around operational questions.
- Prepared and checked 11 deployment targets: five central publishers and six collector releases across three source clusters.
- Removed the project's releases, dashboards, monitors and owned Kubernetes resources before reinstalling. The native dashboard kept its ID.
- **628 protected objects kept their UIDs** through removal and reinstallation: existing workloads, PVCs, VMs, VMIs and Longhorn volumes. Demo applications were preserved. Coriolis stayed stopped.
- Reinstalled all 11 releases with the generated values, preserving approved publisher identities, etcd collection and existing restricted policies. This historical run used the helper that has since been removed; it is not the current installation procedure.
- **59 local tests passed**, including integer formatting, layouts, repeatable generation and safe handling of external deletion failures. Helm lint, rendering and server-side admission checks passed.
- **7,967 backend query/filter cases**: zero execution errors or non-finite values; 2,930 empty results counted separately. A nonexistent cluster returned no series in any panel.
- **7,967 additional cases through the native SUSE API**: zero execution errors or non-finite values; 2,940 empty results, including filters without matching data. The environment changed between runs.
- **779 historical six-hour cases through the native API**: zero errors or non-finite values; 195 empty results. Covered Everything, individual clusters and representative multiple selections.
- **45 native HTTP-total queries and 18 invariants passed** at 60-, 300- and 900-second steps. All 34 monitor queries returned data without errors; this was not a full incident/notification test.
- Source comparison matched 10 running VMIs, 50 vCPUs, 100 GiB of configured guest RAM, 32 host logical CPUs, 184 Longhorn volumes and eight import records. VMIC phases, disks and recorded intervals matched its API.
- **772 current requests/limits fields matched**, with no missing current fields after collection caught up with the rollout. Newly created Pods were initially detected before their first samples arrived. Old Pod series can remain in backend history and are not treated as current Pods.
- Five KubeVirt targets and one Longhorn target reported `up=1`. Import inventory was healthy. Samples were newer than installation and less than 30 seconds old at the check.
- Reviewed all nine dashboards in the SUSE UI, including integer counts, units, labels and the VM filter (10 total, one selected). Traefik errors use lines because the tested native bar chart did not draw the points correctly.
- Longhorn NetworkPolicy allowed only TCP/9500 from the collector, with namespace and Pod selectors in the same peer. Native policies were preserved.
- Final readiness check: 10 Ready nodes, 11 installed project releases and 24 ready collector Pods across the three clusters.

The clean-install run caught differences between Helm 3/4 flags, cross-namespace admission checks for CA/Longhorn resources, and cleanup of older collectors.

The UI review caught an issue that direct backend checks missed: the SUSE parser rejected `[1i]` in HTTP totals. The final expressions use `${__interval}`, resolved by the native API. The same six-hour window returned 31,895 application requests and 384,384 Traefik requests at all three resolutions. These measure different sources and are not expected to equal each other. VM performance summary panels also retained the identity of the VM with the highest value.

## Observed versions

| Component | Version |
|---|---|
| SUSE Observability | 2.10.2 |
| Publishing CLI | 3.3.6, SHA-256 checked |
| Rancher Prime | 2.14.6 |
| Harvester | 1.8.2 |
| Longhorn | 1.11.2 |
| KubeVirt | 1.7.4 |
| VM Import Controller | 1.8.2 |
| Kubernetes / RKE2 | 1.34.9 / 1.35.6 / 1.35.7 |
| Traefik RKE2 | 3.7.1 / chart 40.1.003 |

These are lab observations. The server, official Agents and existing platforms were preserved.

## Earlier migration — historical evidence

The previous combined releases were inventoried and backed up privately. Five old project dashboards and 33 old monitors were exported and removed, while the native dashboard was preserved. Old platform collectors, the Harvester KubeVirt collector and the central content release were replaced by independent modules. Imports was added separately.

The old KubeVirt collector had a stale CA. The replacement used the current public CA and collected ten VMs. The unused CA copy was backed up and removed after checking that the namespace's 19 Pods/workloads no longer referenced it. SUSE metric history and the demo applications `brasil-dados` and `request-lab` were preserved.

That earlier revision passed 53 local tests, 7,346 query/filter cases (2,030 empty) and 831 historical cases (213 empty), with no query errors or non-finite values. Additional application and Traefik filter audits passed after fixes. HTTP totals were checked with 45 queries and 18 invariants: the same period correctly produced 31,104 requests across three resolutions, whereas the earlier expression incorrectly dropped to 6,252 and 2,053 at wider steps.

### Source comparisons from that migration

| Check | Observed result |
|---|---|
| Running VMIs | 10 in both API and dashboard |
| Configured CPU topology | 50 vCPUs in both; cores × sockets × threads |
| Configured guest RAM | 107,374,182,400 bytes (100 GiB) in both |
| Host logical CPUs | 32 in both |
| Longhorn volumes | 184 in both |
| Active robustness states | 41 healthy, one degraded, 142 unknown; exact match |
| Last-backup timestamps | 184 checked; 183 had no recorded backup and one had a timestamp |
| Provisioned logical Longhorn size | 10,668,803,620,864 bytes in both; not physical usage |
| VMIC records | Eight, all `virtualMachineRunning`, in both |
| Imported logical disk capacity | 254,476,812,288 bytes in both |
| VMIC disks and recorded intervals | Exact match with the eight API objects |
| Container requests/limits | 772 fields: 318 Observability, 148 Rancher, 306 Harvester; zero mismatches |

### Longhorn access and actual findings

The approved `obs-virtualization-longhorn-metrics` policy selects `app: longhorn-manager` in `longhorn-system`. It permits TCP/9500 from Pods matching both `obs-virtualization` / `sre-kubevirt-telemetry` labels and namespace `suse-observability`. The applied rule was checked; native policies stayed in place, and the target reported `up=1`.

One pre-existing volume was degraded with replica scheduling failure `disks are unavailable`. The dashboard matched the Longhorn API. Replicas, placement, volumes and data were not changed to make a panel green. Single-host capacity was not presented as HA.

### Empty results were kept separate

Active-import age panels were empty because all eight retained imports were complete. Read latency can be empty when no reads occur, and detached volumes have no current I/O. Nonexistent filters produce no series rather than a healthy zero. These cases were not counted as proof of availability.

## Validation boundaries

- **VMIC:** live checks used eight existing completed records. Active/failure phases and inventory failures were covered locally; no new VMware import or transfer failure was triggered.
- **Coriolis:** excluded by the owner; its VM stayed stopped.
- **Backups and history:** no restore was performed. Timestamps, p95 and backup metadata do not prove RPO, application consistency or a full day of data.
- **Metrics:** checks apply to the observed versions and contracts. Dynamic measurements remain subject to collection resolution, gaps and exporter accuracy.
- **Publishing permissions:** existing restricted tokens were preserved. A new organization's role still needs permission/ownership validation.
- **Certificates:** startup with the current CA was checked; a full KubeVirt CA rotation was not triggered.
- **Notifications:** monitor publication and queries do not prove incident opening, email/paging delivery or recovery.
- **Applications:** the default contract was checked live. Alternate OTel aliases passed rendering checks but need validation against their actual metrics.
- **Resilience:** no reboot, host loss, failover, destructive storage test or prolonged load test was performed.
- **Fleet and air gap:** no new deployment in those modes was performed.

Backups, tokens and raw telemetry remain outside the repository. Published examples contain no credentials or private lab addresses.

## 27 October 2026 — chart 1.4.0 dashboard review

This round updated the five existing central content releases and the Harvester Imports collector. It did **not** repeat the earlier clean uninstall, install a new SUSE server or Agent, or start a VMware migration. The from-zero Virtualization walkthrough is for the user to execute; the separate lab handoff preserves the existing central-content/Harvester-telemetry split.

- 64 automated tests passed, including opt-in RBAC, TLS configuration, link round trips, complete offender links, integer counts, rendering and repeatable chart generation. Helm checks passed. The new Agent example was rendered against the official Agent chart 1.2.14; no second Agent was deployed.
- The SUSE native API accepted 1,727 instant query/filter cases (up to two discovered values per variable, including multi-select and nonexistent-cluster cases) and 824 range cases. There were no API errors or nonfinite values. Empty results were retained: negative filters, no active imports and inapplicable measurements are not healthy zeroes. This is not every possible combination of filters or versions.
- At the comparison snapshot, the memory review panel matched all **15** qualifying Pods and their percentages against independently calculated usage/limits from live metrics and Kubernetes Pod specs. Missing-setting counts also matched Kubernetes: **125** CPU requests, **184** CPU limits, **125** memory requests, **183** memory limits. These are point-in-time values, not permanent expected counts.
- The Harvester kubelet scrape reported `up=1` with TLS verification enabled. Eighteen retained CPU/memory/network source series were received. The initial cAdvisor response exceeded 16 MiB; streaming parsing and a 64 MiB response ceiling resolved collection without disabling TLS or granting `nodes/proxy`.
- Optional `nodes` discovery and `nodes/metrics` read access were explicitly approved for the Harvester Imports collector. No Secret, exec, proxy or write permission was added.
- Native UI checks rejected `sort_by_label`, so it is not used. Per-series Stat cards preserve the name/value association; the unsupported dashboard Table widget and unreliable TimeSeries Last column are avoided. The Metrics Explorer link was opened successfully with filters and valid comparisons, and Table view displayed complete names and percentages. Summary counts remain integers; detail percentages are rounded for readability.

The eight existing import objects were completed. The new network panels therefore validate collection and attribution to the controller/shared image Pods during idle operation, **not active VMware transfer throughput or per-VM progress**. No VM power operation, migration, volume removal, restore, failover or notification-delivery test was performed. CPU/memory configuration is not changed by these dashboards.
