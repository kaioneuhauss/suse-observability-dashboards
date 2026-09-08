# sre-platform-telemetry

Collect Linux host, local etcd and optional Traefik metrics, then send them to an existing SUSE Observability receiver. Install once per monitored Kubernetes cluster, alongside the official Agent.

Start with the [complete installation procedure](../../README.md#2-install-telemetry-in-each-cluster) and [prerequisites](../../docs/PREREQUISITES.md). Copy the [cluster template](../../config/cluster.values.yaml) or [Harvester template](../../config/harvester.values.yaml) into an ignored local values file.

## Main values

| Value | Default | Meaning |
| --- | --- | --- |
| `clusterName` | Required | Exact SUSE integration name |
| `remoteWrite.url` | Required | Full HTTPS Prometheus remote-write endpoint |
| `remoteWrite.existingSecret` | `suse-observability-agent-secrets` | Ingestion Secret in release namespace |
| `remoteWrite.secretKey` | `STS_API_KEY` | Field containing the ingestion API key |
| `remoteWrite.username` | `apikey` | Receiver Basic Auth username |
| `remoteWrite.caSecret` / `caKey` | Empty / `ca.crt` | Optional private receiver CA |
| `scrapeInterval` | `30s` | Collection interval |
| `nodeExporter.enabled` | `true` | Host OS metrics |
| `nodeExporter.pressureEnabled` | `true` in chart; `false` in templates | Requires Linux PSI on all selected nodes |
| `etcd.enabled` | `false` | Local member metrics on matching etcd nodes |
| `etcd.endpoint` | `http://127.0.0.1:2381/metrics` | Host-network local scrape target |
| `etcd.nodeSelector` | etcd role `true` | Nodes running etcd |
| `traefik.enabled` | `false` | Traefik scrape and Ingress backend inventory |
| `traefik.namespace` | `kube-system` | Traefik workload namespace |
| `traefik.selector` | `app.kubernetes.io/name: rke2-traefik` | Actual pod selector |
| `traefik.port` / `targetPort` | `9100` / `metrics` | Internal metrics Service and pod port |
| `traefik.allowMetricsNetworkPolicy` | `false` | Restricted allowance only for already isolated Traefik pods |
| `vmagent.queueMaxDiskMiB` | `1024` | Per-collector disk queue; volume adds 256 MiB headroom |
| `vmagent.selfMonitoring` | `true` | Queue, retry and drop metrics |

See [values.yaml](values.yaml) for image versions, resources, node selectors, ports and tolerations. Defaults are not production sizing. The schema rejects queues below 513 MiB because of the collector's effective minimum buffer size.

## Resources and lifecycle

The chart creates a node DaemonSet and, when enabled, a separate etcd DaemonSet and a single-replica Traefik collection Deployment. Host mounts are read-only. The Ingress inventory sidecar gets only Kubernetes read permissions required for discovery; it does not receive permission to read Secrets or modify Ingresses.

Queue storage is `emptyDir`: it survives a container restart, but not pod replacement or node loss. Traefik collection uses Recreate to avoid overlapping collectors during upgrade, so expect a short collection gap. Check queues before replacing pods.

Uninstall removes the collectors, not metrics already retained by SUSE. This chart does not install or configure Traefik itself and does not copy etcd private keys.
