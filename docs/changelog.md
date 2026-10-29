# Changelog

## 1.8.0 — Balanced cards and VM storage references

- Use a consistent 56px numeric value size and reduce action-list height by one third. At the validated desktop width, five results share a single row instead of wrapping 4 + 1. Storage health and old-backup previews share a row and show up to three entries each; the full table retains all matches.
- Show VM names for volumes associated with a running VM through KubeVirt’s explicit `vmi_pod` mapping. Keep Pod, PVC and volume labels in the full table; unmatched volumes stay visible.
- Add native Pod/PVC investigation shortcuts and document the distinction between a panel link and an individual resource link.
- Existing monitor definitions, collectors, permissions and dashboard IDs are preserved.

## 1.7.0 — Resource identity and filter guidance

- Patch existing dashboards by default, preserving their IDs and saved links during updates.
- Match Longhorn volumes to current Pod PVC references already collected by the official Agent. Keep unmatched volumes and all consumers in the complete table; avoid ambiguous joins.
- Use larger values and compact resource labels in VM, Pod and storage detail cards. Preserve full identities in the query and the **Full names and values** link.
- Explain Everything versus None, dependent filters, Traefik namespace discovery and the boundary between VM infrastructure, guest telemetry and application traces.
- See the dated validation record for tested cases and limitations.

## 2026-10-28 — Documentation walkthrough; chart packages unchanged

- Added a detailed configuration guide with architecture, verified lab release placement, step explanations, chart parameter reference and the dashboard publication/removal lifecycle.
- Expanded README prerequisites with server setup links, Agent placement, registry credential preparation, version boundaries and expected results.
- Added an optional application OpenTelemetry walkthrough with a separate official Helm collector, SDK configuration, metric-contract checks and removal. This example passed Helm rendering and collector configuration validation; it was not deployed during this update.
- Kept the existing 1.6.0 packages, dashboard definitions and live cluster configuration unchanged.

## 1.6.0 — Readable resource names and separate VM Top 5 lists

- Increased short summary cards across all nine dashboards: the native component reduced labels to about 4px in one-row cards.
- Replaced the three single-VM performance summaries with separate Top 5 lists for CPU use, guest memory use and CPU scheduling wait. Rankings retain full VM identity, include running VMs and use the selected end time.
- Limited action-list previews to five entries, including pods above the 80% review threshold. Counts still cover all matches and the Metrics Explorer links open the complete lists.
- Renamed “Missing application copies” to “Unavailable application replicas”, added a concrete explanation and a current list of affected applications with their unavailable counts.
- Installation, collectors, credentials, monitor definitions and removal behavior are unchanged.

## 1.5.0 — Resource names, stable navigation and clearer module steps

- Added named PVC/volume lists for degraded/faulted volumes, missing backup records and old backups, with full Metrics Explorer links.
- Filled native dashboard grid gaps and normalized threshold ordering to prevent automatic edits when opening dashboards.
- Added two Longhorn health monitors and three import/collection monitors; 39 monitors total. Notification routing remains separate.
- Expanded the README with prerequisites, each module, a worked second-module example, collector ownership, updates and individual/full removal.
- Added explicit alert coverage and validation limits.

## 1.4.2 — Size the optional Imports collector for cAdvisor

The inventory-only memory limit could trigger OOMKilled when performance collection parsed the kubelet response. Enabling `imports.performance.enabled` now automatically selects a separate 128 MiB request / 512 MiB limit and 50m / 500m CPU budget. Customize `imports.performance.resources` for larger environments. Collection remains opt-in with the same read-only permissions and TLS verification.

## 1.4.1 — Match SUSE's stored Pod label

SUSE normalizes the cAdvisor `pod` label to `pod_name`. Import performance selectors and legends now use the stored label; 1.4.0 could collect the data while showing empty performance panels. Seven positive native queries and seven nonexistent-cluster queries were checked explicitly after correction. The selector correction first shipped in 1.4.1; existing immutable packages remain available.

CPU is shown in mCPU so small values remain readable. Unpaired Imports panels use the full row, keeping paired CPU/memory and receive/transmit charts aligned.

## 1.4.0 — Actionable dashboards and a complete Virtualization walkthrough

- Removed full-width section text panels that looked like empty charts. Kept one introduction and the panel descriptions; made summary counts more compact.
- Added per-Pod threshold values and top-ten usage details for missing resource settings, with links to complete Metrics Explorer tables. Corrected URL encoding and percentage scaling in those links.
- Added opt-in VM Import Controller CPU, memory and network collection, plus explicitly shared Longhorn image-service network views. Uses TLS and `nodes/metrics`; no `nodes/proxy`, exec or write permissions.
- Rewrote the Virtualization walkthrough from prerequisites through removal, including a new Agent installation, exact input fields and expected results. Installation remains Helm/kubectl only.
- Retained all prior chart packages; cleanup behavior introduced in 1.3.0 is unchanged.

## 1.3.0 — Simpler installation and removal

- Numbered English guides explain what to fill in, what to run and what to expect.
- `helm uninstall` now removes the module's managed SUSE dashboards and monitors before removing Kubernetes resources. Keep the publisher token available.
- Successful publishing and cleanup Jobs are removed automatically; failed Jobs remain for inspection.
- Plan-only and telemetry releases never delete external content; `lifecycle.deleteOnUninstall: false` explicitly retains it.
- Development sources, tests and tooling are grouped under `dev/`. Redundant prerequisite fragments were removed; the active guides contain the required settings.
- Dashboard queries, metric contracts and collector behavior are unchanged from 1.2.1.

## 1.2.1 — Direct Helm installation

- Public Helm repository with a package for each module; no repository clone or local build needed.
- English README and tutorials using only kubectl and Helm for installation, configuration and removal.
- Smaller values examples and a consistent workflow across all five modules.
- Removed the user-facing Bash installer helper and its helper-only tests. Build and audit tools remain for maintainers.
- Separate guides for common prerequisites, OTLP setup, multiple clusters and cleanup.
- Clear lab-only warning: not recommended for production and not an officially supported SUSE integration.
- Dashboard definitions, metric queries, collection settings and publisher behavior are unchanged from 1.2.0.

## 1.2.0 — Readability and installation review

- Nine English dashboards organized around practical questions.
- Reviewed 161 panels: titles, descriptions, units, precision and diagnostic purpose.
- Integer counts; appropriate precision for rates and percentages without rounding source data.
- Dedicated performance, capacity and storage views; readable volume states, backup codes and import phases.
- HTTP queries compatible with the SUSE parser, checked through its native API at three resolutions.
- Corrected inherited panel links and simplified the VM overview.
- Added the previous installer helper and documented clean installation, verification and removal.
- Recorded source comparisons, versions and validation limits in `docs/lab-validation.md`.

## Virtualization 1.1 / Imports 1.0

- Three additional Virtualization views and an independent VM Import Controller module.
- Verified Longhorn/KubeVirt units and HTTP totals across query resolutions.
- Coriolis excluded from this delivery.

## 1.0.0 — October 26, 2026

- Four independent charts: Virtualization, Traefik, Applications and Kubernetes.
- Minimal values, all/telemetry/content modes and disjoint content catalogs.
- Automatic public KubeVirt CA synchronization with restricted RBAC.
- Optional Longhorn collection and explicitly enabled, narrowly scoped NetworkPolicy.
- p99, connections, request availability, error budget usage and collection freshness panels.
- Configurable HTTP metric names and 34 monitors.
- Clean installation in three clusters, regression checks and live queries; boundaries recorded in the lab report.

## Earlier combined package

The version 6 procedures were replaced. Git revision `c059f58` preserves the previous package and its historical evidence.
