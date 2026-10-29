# Lab validation

This records what was checked in this lab. It is not a support matrix or a production certification. **This community project is not recommended for production.**

## 2026-10-29 — Chart 1.7.0 filters, resource identity and usability

This round updated the five central **content** releases. It did not uninstall the platform, reinstall collectors or change application, VM or volume configuration. Dashboard definitions were compared with the source after publication: **all nine matched and retained their IDs**. The native Kubernetes dashboard retained its ID too.

### What changed

- VM and Pod cards show compact names, larger values and a **Full names and values** link. Long PVC/certificate legends use the same approach. The complete identity remains in the query; a shortened label alone is not unique.
- CPU/memory summary cards have more horizontal space. Separate Top 5 VM lists remain available for CPU demand, memory demand and CPU waiting.
- Storage details include Pod references from the official Agent, with a PVC fallback when no unambiguous current association is available. Summary counts still count unique volumes.
- The README explains parent/child filters, **None** versus **Everything**, Traefik namespace discovery and the difference between infrastructure signals, guest telemetry and application tracing.
- Helm uses `patch` by default for dashboard updates. Managed content can still overwrite personal edits; uninstall/reinstall can change IDs.

### Checks completed

- **8,827 native API query/filter cases:** every discovered single-value filter path, parent + Everything paths, representative multi-selection and a nonexistent cluster. **Zero query errors or nonfinite values**; 3,350 empty cases were recorded separately. All 195 nonexistent-cluster query cases returned no series.
- **833 six-hour query cases:** zero errors or nonfinite values; 209 empty cases. Range checks covered Everything, individual clusters, representative multiple clusters and the negative cluster.
- Final display projections were compared with their underlying expressions in **22 same-evaluation checks**. Full identities matched; numerical differences were at floating-point rounding scale (maximum observed absolute difference about `5.6e-17`, tolerance `1e-12`). These comparisons check display changes, not exporter accuracy.
- All **69 automated tests**, Helm lint/render/configuration checks, generation repeatability and package/source checks passed. End-user installation/removal still uses Helm and kubectl.
- Browser checks covered the nine dashboards, their panel layouts and return navigation. No false unsaved-changes warning was reproduced. Tests included Everything, an empty selection, one cluster/namespace, multiple Traefik namespaces, an application, VM namespace selection and one storage volume. The complete Pod/PVC/volume row was opened in Metrics Explorer Table view. The tested browser viewport was 1280 pixels wide; this is not a guarantee for every window size or future resource name.
- Native label discovery returned the VM namespace after selecting Harvester. An empty Cluster selection correctly produced no namespace choices. Traefik showed one namespace in the Observability cluster and two in the Rancher cluster, matching the discovered standard Ingress backends. No new application/Ingress was created for this check.
- **184 Longhorn volumes** were reconciled with the source. The detail queries retained 183 volumes without a recorded backup, one older backup and the degraded volume. **41 Pod associations** were checked: 28 direct PVC references and 13 KubeVirt hotplug associations confirmed through the child Pod's owner UID. No VM name was guessed from a PVC UUID.
- The read-only inventory found **10 Ready nodes and 338 Pods that were Ready or Succeeded**. This does not establish overall health. All **39 monitors** were enabled, with no execution errors or unmatched topology states in the sampled status.

### Actual findings and limits

One Longhorn volume was degraded, the Harvester host exceeded the configured etcd WAL latency threshold, and an Elasticsearch container exceeded the configured sustained memory/limit threshold. Those findings were retained rather than changing infrastructure or thresholds to make the dashboards green. The degraded volume had no matched current Pod reference; that does not prove that its data is disposable.

A license warning appeared briefly during an initial page load, then disappeared when the dashboard loaded. This was not confirmed as an invalid license and no license change was required.

This is bounded lab validation, not proof that every possible environment or failure is covered. No active VMware import, guest-agent installation, new tracing pipeline, automatic remediation, backup restore, host failure, server upgrade or external alert-delivery test was performed. Coriolis remained outside scope. Native UI dimensions, retained telemetry and source freshness still affect what a user sees. Raw identities, screenshots and detailed test output remain in the private validation folder.

## 2026-10-28 — Documentation and configuration examples

This was a documentation update, not another uninstall/reinstall round. Read-only Helm inspection confirmed the release versions, namespaces and selected non-secret settings described in [Configuration explained](configuration-guide.md#how-the-current-lab-is-organized). The existing cluster configuration was not changed.

- All 38 YAML blocks across the README and documentation parsed with duplicate-key checks. Local document links and anchors passed checks.
- The five minimal module examples and their applicable `content`/`telemetry` variants rendered successfully. The optional Imports performance example also rendered.
- The new separate application collector example rendered with official OpenTelemetry chart `0.178.0`. Its extracted configuration passed the official collector `0.163.2` validator; the downloaded binary matched the SHA-256 digest supplied by its GitHub release asset.
- The project's 69 automated tests and existing Helm checks passed. Dashboard chart packages remain at 1.6.0 and were not rebuilt.
- Official server, Agent, OTLP ingress, application telemetry and registry documentation was reviewed. The Harvester Agent chart `1.2.14` values were checked: they do not contain the newer `otel.telemetryGateway` setting.

The new application collector/SDK example was **not deployed** and no new application was instrumented. Server installation, new ingress creation, active imports, destructive failure tests and external notification delivery were not repeated. Rendered YAML and configuration validation do not establish connectivity, application metric compatibility or production readiness.

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

### 1.4.1 correction during visual acceptance

The first 1.4.0 native-query sweep did not treat expected-positive empty panels as a failure. Visual acceptance then caught SUSE ingestion's `pod` → `pod_name` normalization. The 1.4.1 dashboard selectors and legends were corrected. All seven performance panels were tested again through the native API with explicit nonempty assertions: one controller receive series, one transmit series, one CPU series, one memory series, two shared-image receive interfaces, two transmit interfaces and one healthy node target. The seven nonexistent-cluster controls returned no series. The full automated suite now contains 65 tests.

The final Harvester inventory contained 429 VM/PV/PVC objects with the same UIDs and specifications as the prior clean-install evidence. The Imports ServiceAccount authorization check allows `get nodes --subresource=metrics` and denies `get nodes --subresource=proxy`.

### 1.4.2 collector sizing correction

A later readiness check found repeated `OOMKilled` restarts in the optional performance collector. The initial successful scrape and nonempty queries had not proved continuous collection. The kubelet response was approximately 20 MiB, and the inventory-only 128 MiB container limit left insufficient parsing headroom even with streaming enabled.

The performance profile now automatically requests 128 MiB and allows 512 MiB, with 50m/500m CPU. The Harvester telemetry release was upgraded to 1.4.2. The same seven positive and seven negative native queries passed again; explicit freshness checks found `up=1`, four scrapes in the previous two minutes, and controller memory samples approximately 11 seconds old. Historic gaps from the earlier restarts remain visible; they were not filled or deleted. The CPU/memory and receive/transmit pairs were also checked in the native UI.

Fifteen readiness/resource snapshots over seven minutes showed both containers ready with zero restarts. The vmagent working set reported by the Metrics API ranged from 104 to 127 MiB against the new 512 MiB limit. This is a short idle-operation check, not a prolonged load or active-migration test. All 65 automated tests and Helm checks passed for 1.4.2.

## 1.5.0 — Navigation, actionable volumes and alert coverage

Validated on 2026-10-27 against the existing SUSE Observability 2.10.2 lab. Only the five **central content releases** were updated using Helm and their saved values. No source collector, application, VM or volume configuration was changed. This round did not repeat the 1.3.0 uninstall/reinstall exercise or install a new server/Agent.

### What was tested

- **67 automated tests** passed, including full-width gap-free grid rows, native threshold order, monitor catalog consistency, cleanup hooks for all five modules, module isolation and complete storage detail links. Helm checks passed.
- All 11 README YAML blocks parsed, and the five module examples rendered with their expected workloads. The examples now cover an additional module, individual/all removal, content/telemetry ownership and shared credentials. Platform setup still requires environment-specific DNS, TLS, credentials and instrumentation; rendering is not proof of a fresh installation in another environment.
- **847 native query/filter cases** passed without API errors or nonfinite values. The sweep used one discovered value per variable, Everything paths and a nonexistent cluster. There were 261 empty results requiring the usual applicability/collection interpretation; these were not replaced with healthy zeroes.
- All nine dashboards passed **open → refresh → return to catalog** without an unsaved-change warning. Traefik also passed a time-range change, cluster selection, empty selection, clearing the filter and returning. This is a bounded browser test, not every combination of browser size, filters and time ranges.
- The original Traefik definition was compared with the YAML exposed by the native editor. The UI compacted a layout gap and reversed a threshold list. Gap-free rows and descending threshold order prevent those automatic edits. Old tabs or drafts from before the update can still refer to replaced dashboard IDs: reopen the current dashboard from **Dashboards → All**. Preserve intentional personal edits in a separate copy.
- Storage detail queries were tested with positive and nonexistent-cluster controls. At the snapshot: **1 degraded volume**, **183 volumes without a recorded backup**, **1 volume with a backup older than seven days**. The health result's volume/PVC/namespace matched the Longhorn resource. The complete Metrics Explorer link opened successfully; Table view exposed the same state and identities in columns. A final correction pins all three lists to the selected end time so recovered resources cannot linger from earlier range samples; three positive/negative instant pairs and three one-hour range queries passed again.
- All **39 published monitors** were enabled and had successful execution timestamps, no reported errors and zero unmapped health states. The new Longhorn degraded rule reported **1 deviating and 183 clear** PVC health states, confirming the real degraded volume maps to its PVC. The faulted rule had no critical result. Import inventory and performance scrape checks were clear; the failed-import rule had no matching records because the retained imports were completed.

No failed import or faulted volume was deliberately created. No notification channel or delivery was configured/tested. No active VMware transfer, backup restore, failover or VM power operation was performed. Successful monitor execution and correct current associations do not prove every failure scenario or notification path.

## 1.6.0 — Readable names and VM Top 5

Validated on 2026-10-27 with SUSE Observability 2.10.2. Updated only the five central content releases using Helm. Applications, source collectors, VMs and volumes were not changed.

- Reproduced the tiny-label issue in VM Performance: one-row Stat cards rendered names at about **3.88px**. Increasing summary cards to two rows and bounding full-width action lists to five entries removed this behavior in the tested views.
- Inspected all **49 Stat panels across nine dashboards** in the native UI, including every pod/volume action list. Measured labels were at least **12.46px** in the five-entry previews and approximately **16.5px** in ordinary summary cards at the tested 1280px browser viewport. Long names can still be truncated; the full identity remains in the resource label and the complete Metrics Explorer query. This is not a guarantee for every viewport size or future cluster cardinality.
- Each VM Top 5 was compared with the corresponding unrestricted per-VM metric at the same timestamp. CPU usage, guest memory usage and CPU scheduling wait passed with Everything, one VM, two VMs and a nonexistent VM. All returned identities and values matched the independent series. Three one-hour range checks returned exactly five stable end-selected VM/value pairs; historical winners did not accumulate in the cards.
- **847 native query/filter cases** passed, with no API errors or nonfinite values. The bounded sweep uses one discovered value per filter, Everything paths and a nonexistent cluster. The 261 empty cases retain their normal applicability/collection meaning. Five further live queries checked the final name-first VM/Pod labels.
- Resource previews were compared with their uncapped detail queries: the memory review showed five of 15 affected pods, and the missing-memory-limit preview showed five of 183. Summary counts remain complete. No failing workload was created for testing.
- The renamed replica indicator reported zero unavailable replicas. Read-only Kubernetes checks agreed across **188 Deployments, StatefulSets and DaemonSets** in the three lab clusters. This validates the healthy snapshot; a failed rollout was not injected.
- All nine dashboards passed open, refresh and return to the catalog without an unsaved-change warning. VM Performance also passed an empty VM selection, one VM, Everything and a six-hour time range. These are bounded usage checks, not every possible filter/time/viewport combination.
- **69 automated tests** and Helm checks passed. The unchanged monitor definitions, installation/removal flow and collectors retain their previous validation boundaries. This update did not repeat uninstall/reinstall, active import, failover, restore or notification-delivery testing.
