# Changelog

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
