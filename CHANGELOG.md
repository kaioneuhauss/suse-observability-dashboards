# Version 6 — 11 September 2026

- Simplify installation to short `deploy/*/values.yaml` profiles, one central publisher Secret for approved new installations, and separate prerequisites/uninstall steps.
- Add concise customer/study guides, a short impact report, Fleet instructions and a technical-details directory; preserve the existing lab's restricted credentials.
- Verify short profiles and shared-Secret apply/delete rendering with Helm 3/4; default-role permissions are documentation-verified, not a new live credential rollout.

- Consolidate five dashboard publishers and monitor definitions into one content chart; keep platform and KubeVirt collection in two separate charts.
- Preserve raw JSON layout coordinates, verify persisted definitions, and avoid saving temporary filter selections.
- Use self-contained Fleet paths with explicit default/profile values; validate packaged targets and a live plan canary.
- Fix Rancher Traefik collection through a scoped metrics NetworkPolicy; show only clusters with Traefik.
- Add a read-only Pod resource inventory to cover hotplug Pods missing from the original resource metrics.
- Add VM scheduler delay, paging, swap and disk response; deduplicate guest and host bind mounts.
- Improve readable cards, affected-Pod/workload lists, operational disk selection, and separate 4xx/5xx timelines.
- Expand to 33 custom monitors and document investigation guidance for all 125 metric panels.
- Record real request-counter, OS, Kubernetes, PVC, filter and publisher checks, with explicit remaining acceptance limits.

The original v5 ZIP and PDF are preserved outside this package. See tests/RESULTADOS.md for the tested environment and evidence boundaries.

- Require positive CPU and memory requests/limits in chart schemas and validate every rendered container.
- Separate counts and lists of Pods above 80% of CPU or memory limits from the top-five absolute usage charts. Add compact status lists and links to Metrics Explorer table view.
- Simplify Traefik to 21 panels with clearly separated selected-period totals and five-minute traffic/latency; remove recent-rate and bounded-history cards.
- Tag monitors per dashboard and document measured collector/server/storage impact.
- Remove the misattributed Last legend column in SUSE Observability 2.10.2.
