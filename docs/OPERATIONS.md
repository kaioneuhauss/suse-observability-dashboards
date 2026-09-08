# Operations and troubleshooting

[Back to README](../README.md)

## Validate collection and publishing

Run `bash scripts/validate.sh` before deployment. It checks Helm rendering, Python syntax, generated monitor consistency, panel references, filter defaults and invalid queue settings. It does not contact a live cluster.

After deployment, inspect each cluster's collector pods and recent logs:

```bash
python3 scripts/audit-collector-logs.py \
  --kubeconfig "$SRE_CLUSTER_KCFG" --context "$SRE_CLUSTER_CTX" \
  --namespace "$SRE_AGENT_NS" --since 10m --output /tmp/collector-check.json
```

The check fails for missing pods, unready containers, unreadable logs and detected error/warning messages. Read the output to determine the cause; a keyword match alone is not a root-cause diagnosis.

Publishing Jobs finish rather than running continuously:

```bash
kubectl logs job/suse-observability-dashboards-suse-observability-dashboards \
  --kubeconfig "$SRE_CENTRAL_KCFG" --context "$SRE_CENTRAL_CTX" \
  --namespace "$SRE_CENTRAL_NS"
kubectl logs job/suse-observability-monitors-apply \
  --kubeconfig "$SRE_CENTRAL_KCFG" --context "$SRE_CENTRAL_CTX" \
  --namespace "$SRE_CENTRAL_NS"
sts dashboard list --output json
sts monitor list --output json
```

Those Job names correspond to the release names in the README. Completed hooks have a one-day TTL by default, so their Kubernetes logs may no longer exist later. Use a separately configured `sts` context for the intended SUSE instance.

Export each dashboard after publishing, using its returned ID, and compare the definition with the corresponding source file:

```bash
sts dashboard describe --id DASHBOARD_ID --file /tmp/persisted-dashboard.yaml
```

The monitor Job performs its own post-publication comparison and prints `persisted_monitors: 24`. Check Enabled state and topology association in the UI. Test notification delivery separately with the actual recipients and routing rules.

## Test every panel query

For administrators with access to the metrics backend, use a local tunnel to the appropriate Prometheus-compatible endpoint. Determine the actual Service name and port in your installation first. A common single-backend example is:

```bash
kubectl port-forward service/suse-observability-victoria-metrics-0 \
  --kubeconfig "$SRE_CENTRAL_KCFG" --context "$SRE_CENTRAL_CTX" \
  --namespace "$SRE_CENTRAL_NS" 18428:8428
```

In a second terminal, run from the repository root:

```bash
mkdir -p /tmp/suse-panel-audit
python3 scripts/audit-queries.py --url http://127.0.0.1:18428 \
  --output /tmp/suse-panel-audit/queries-instant.json
python3 scripts/audit-queries.py --range --url http://127.0.0.1:18428 \
  --output /tmp/suse-panel-audit/queries-range.json
python3 scripts/audit-display-identities.py --url http://127.0.0.1:18428 \
  --output /tmp/suse-panel-audit/display-identities.json
python3 scripts/build-panel-review.py --audit-dir /tmp/suse-panel-audit
```

The report has one row per panel. Tests discover current single-value filter paths, representative multiple selections, Everything and an invalid-cluster control. Range testing is bounded to avoid excessive load. These checks are not exhaustive tests of every possible subset and time window.

Do not expose the backend publicly for this test. Stop the tunnel with Ctrl+C. Audit outputs contain environment data and must stay outside the public repository.

## Visual and source-data acceptance

Open all five dashboards. Test Everything, then each cluster and applicable namespace, application and VM. Reset dependent filters after changing a parent. Check recent and historical windows, units, names, expanded lists and error states.

Compare the same resource and time period at the source:

| Metric | Compare with |
| --- | --- |
| Host filesystem size and usage | `df` on the same node, mount and device |
| Host and guest OS memory | `MemTotal` and `MemAvailable` in that OS's `/proc/meminfo` |
| Container usage | Kubelet/cAdvisor for the same container; account for sample timing |
| Pod resource settings | Sum regular-container requests/limits within the same pod |
| PVC filesystem usage | Kubelet/CSI filesystem statistics; distinguish Block volumes |
| Guest filesystem usage | QEMU Guest Agent / `df` inside the VM |
| HTTP counts | A controlled request batch and before/after counters for the same service and status codes |

Full numeric display is not an event ledger: `increase()` estimates a window from sampled counters and cannot recover traffic before the first sample. Do not add proxy and application request counts together; the same request can be observed at both layers.

Filesystem utilization uses `used / (used + available)` to match `df` semantics. Reserved blocks can make it differ from `used / total`. Loop devices, temporary filesystems and pod mounts are excluded from host capacity signals. Repeated bind mounts are not additional physical disks.

## Understand No data

| Situation | Interpretation and next check |
| --- | --- |
| Filter says None | Select a value or enable Everything |
| No completed requests | Latency and success percentages are undefined; check traffic and collection freshness |
| No restart increase | An affected-container list can be empty; confirm inventory and collection are healthy |
| Single-member etcd | No peer exists for a network round-trip measurement |
| Unsupported Linux PSI | Disable the optional collector; ordinary host metrics remain available |
| Raw Block PVC | Kubernetes allocation is known, but filesystem usage requires measurement inside its consumer |
| Unmounted PVC | Kubelet may have no filesystem statistics for it |
| Stopped VM | No current guest consumption is expected |
| Pod without complete limits | A utilization-to-limit denominator cannot be calculated reliably |
| Expected metric disappears | Check `up`, sample age, discovery, permissions, credentials, network and delivery queue |

Do not fill every missing result with zero. That can hide broken collection. Expanding the dashboard time range also does not change a panel's explicitly documented calculation window, such as “last five minutes”.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Publishing returns 401/403 | Correct SUSE service token and role; an ingestion key or Kubernetes token is not a substitute |
| Monitor listing works, import fails | The tested server requires create, update and delete monitor permissions together |
| Telemetry returns 401/403 | Receiver URL, ingestion key, Secret field and namespace |
| Traefik has no service metrics | Persistent Traefik metrics settings, recent traffic, labels, port and NetworkPolicies |
| Ingress namespace filter is wrong | Inventory sidecar health and supported Ingress provider; do not confuse collector namespace with application namespace |
| KubeVirt TLS failure | Target CA, each component SAN and actual endpoints; do not use insecure TLS as a repair |
| Node exporter logs broken pipe from probes | Keep the short `/` health endpoint; `/metrics` is too large for a kubelet HTTP probe |
| Numbers change with graph resolution | Inspect explicit lookback in endpoint queries; current-value panels should not reuse old hourly values |
| UI reports Service Unavailable | Retry and inspect server/router/backend health; this differs from an empty metric query |
| Chart appears unchanged after apply | Export persisted definitions; CLI success alone is insufficient |
| Long names or only four legend rows | Expand the panel or `+N more`; the native UI may need horizontal scrolling |

## Updates and removal

Keep your private values separate from the source repository. Before upgrading, export managed dashboards and record chart versions. Check that collector queues are drained before replacing pods.

Re-run the same `helm upgrade --install` command with the updated chart and values. Dashboard definitions are recreated by name in the validated implementation; links containing old IDs can become stale. Monitor identifiers are preserved by name, and duplicate names stop publication for review.

For collectors, Helm rollback restores the selected Kubernetes release. For dashboard and monitor publication, **Helm rollback alone does not restore the objects already stored in SUSE**: the publishing hooks run on install/upgrade. Reinstall the earlier chart source with `helm upgrade`, or restore the previously exported SUSE definitions.

`helm uninstall` removes chart-owned Kubernetes resources, but does not automatically delete SUSE dashboards or monitors. Hooks may remain until their TTL. Remove SUSE objects separately by reviewed IDs/identifiers, never through a broad delete.

## Validation and limitations

The baseline was validated on SUSE Observability 2.10.2 with five dashboards and 24 monitors. Checks covered Helm rendering, persisted definitions, live queries, UI filters, OS/VM/PVC comparisons and controlled application traffic. Private telemetry and machine inventories are deliberately excluded from this repository.

Every new installation needs its own acceptance. Metric contracts, topology mappings, workload type, kernel support, certificates and network policy differ between environments. Default resource requests are a starting point, not production sizing. Queue `emptyDir` survives a container restart but not pod replacement or node loss.

Monitors use initial thresholds and sampled-window conditions. They do not guarantee continuity during collection gaps or replace business SLOs, backup restore tests, hardware monitoring, traces or storage-product-specific analysis. TLS and Ingress monitors use a Traefik DaemonSet mapping by default; adapt the topology mapping for a Deployment or multiple ingress controllers.
