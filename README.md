# SUSE Observability Dashboards

Five dashboards and 24 native monitors for Kubernetes, RKE2, Traefik and SUSE Virtualization (Harvester), installed with Helm. Explore application traffic, response times, resource usage, storage, etcd health and virtual machine usage through 117 panels with clear English explanations.

**Start here:** configure the [prerequisites](docs/PREREQUISITES.md), then follow [Install via Helm](#install-via-helm-recommended). This project extends an existing SUSE Observability installation. It does not install the Observability server or automatically instrument applications.

## What you get

| Dashboard | Questions it helps answer |
| --- | --- |
| Instrumented apps | How many calls reached the application? Which routes return errors or respond slowly? |
| Workload Resource Efficiency | Which pods lack resource settings? How does usage compare with CPU and memory requests and limits? |
| Kubernetes Platform Health | Are nodes and workloads available? Are disks, PVC filesystems, etcd and metric collectors healthy? |
| Traefik Ingress Health | Which applications receive traffic? How fast do they respond? Which HTTP codes and certificates need attention? |
| Harvester VM & Host Health | What does each running VM use? How does that differ from its configuration and the physical host? |

The [monitor catalog](alerts/catalog.json) covers etcd, disk space, inodes, memory, PVC growth, certificates and collection failures. Review its starting thresholds for your environment; this is not a complete SLO, hardware or backup-monitoring solution.

## Where each component runs

| Component | Install location | Frequency |
| --- | --- | --- |
| Official SUSE Observability Agent | Every monitored Kubernetes cluster, including Harvester | Once per cluster, using the official integration |
| [`sre-platform-telemetry`](charts/sre-platform-telemetry/README.md) | Each monitored cluster | Once per cluster; enable applicable collectors |
| [KubeVirt OpenTelemetry collector](docs/KUBEVIRT.md) | Harvester Kubernetes cluster | Once per Harvester cluster, using an upstream Helm chart |
| [`suse-observability-dashboards`](charts/suse-observability-dashboards/README.md) | Management namespace with access to the SUSE API | Once per SUSE Observability instance |
| [`suse-observability-monitors`](charts/suse-observability-monitors/README.md) | Same management namespace | Once per SUSE Observability instance |

A Harvester host and an RKE2 node inside a VM are different layers. Each Kubernetes cluster has its own etcd. Do not install the KubeVirt collector in each guest VM or publish another copy of the dashboards for each cluster.

## Prerequisites

- A working SUSE Observability instance and an official Kubernetes integration for every monitored cluster.
- Helm 3, `kubectl`, Bash and cluster access. Python 3 with PyYAML is needed for validation and customization.
- Linux nodes. Host collectors use host networking and read-only host mounts, which your admission policy must allow.
- An **ingestion API key** for telemetry and separate **SUSE service tokens** for dashboard and monitor publishing.
- HTTPS access to SUSE endpoints, container registries and the pinned CLI download. Default publishing Jobs use a Linux x86-64 CLI binary.
- Traefik Prometheus metrics configured persistently in RKE2/Rancher. For VMs, complete the [KubeVirt prerequisites](docs/KUBEVIRT.md).

Follow [Prerequisites and credentials](docs/PREREQUISITES.md) for the exact commands, Rancher YAML, TLS configuration and etcd checks. **Installing the dashboard chart alone does not produce metrics.**

Validated baseline: SUSE Observability **2.10.2**, `sts` CLI **3.3.6**, and RKE2 Traefik chart versions **39.0.703 / 40.1.003**. Validate metric names, labels, certificates and API behavior when using other versions. See [validation limits](docs/OPERATIONS.md#validation-and-limitations).

## Install via Helm (recommended)

### 1. Download and prepare values

```bash
git clone https://github.com/kaioneuhauss/suse-observability-dashboards.git
cd suse-observability-dashboards

mkdir -p config/local
cp config/cluster.values.yaml config/local/production.values.yaml
cp config/harvester.values.yaml config/local/harvester.values.yaml
cp config/dashboards.values.yaml config/local/dashboards.values.yaml
cp config/monitors.values.yaml config/local/monitors.values.yaml
```

`config/local/` is ignored by Git. Store credentials in a secret manager and Kubernetes Secrets, not in values files. Checked-in templates contain placeholders only.

Replace these example paths, contexts and namespaces:

```bash
export SRE_CLUSTER_KCFG="$HOME/.kube/production.yaml"
export SRE_CLUSTER_CTX="production"
export SRE_AGENT_NS="suse-observability"
export SRE_HRV_KCFG="$HOME/.kube/harvester.yaml"
export SRE_HRV_CTX="harvester"
export SRE_HRV_AGENT_NS="suse-observability"
export SRE_CENTRAL_KCFG="$HOME/.kube/observability.yaml"
export SRE_CENTRAL_CTX="observability"
export SRE_CENTRAL_NS="suse-observability"
```

Use the namespace containing the actual Agent Secret. Skip Harvester variables and steps if you do not use Harvester.

### 2. Install telemetry in each cluster

First complete [Agent, Traefik and etcd preparation](docs/PREREQUISITES.md). Edit `config/local/production.values.yaml`:

```yaml
clusterName: production
remoteWrite:
  url: https://observability.example.com/receiver/prometheus/api/v1/write
  existingSecret: suse-observability-agent-secrets
  secretKey: STS_API_KEY
nodeExporter:
  pressureEnabled: false
etcd:
  enabled: true
traefik:
  enabled: true
  allowMetricsNetworkPolicy: false
```

`clusterName` must match the SUSE Kubernetes integration name, which need not equal the kubeconfig context. Disable etcd or Traefik collection when not applicable. Enable PSI only after checking kernel support on the selected nodes.

```bash
helm upgrade --install sre-platform-telemetry ./charts/sre-platform-telemetry \
  --kubeconfig "$SRE_CLUSTER_KCFG" --kube-context "$SRE_CLUSTER_CTX" \
  --namespace "$SRE_AGENT_NS" --values config/local/production.values.yaml \
  --wait --timeout 5m
```

Repeat with a separate file and context for each monitored cluster, including the cluster hosting SUSE. Avoid duplicate collectors for the same targets.

For Harvester, edit `config/local/harvester.values.yaml` with its integration name, receiver URL and Secret. Keep Traefik disabled if the Harvester cluster does not use it:

```bash
helm upgrade --install sre-platform-telemetry ./charts/sre-platform-telemetry \
  --kubeconfig "$SRE_HRV_KCFG" --kube-context "$SRE_HRV_CTX" \
  --namespace "$SRE_HRV_AGENT_NS" --values config/local/harvester.values.yaml \
  --wait --timeout 5m
```

### 3. Install KubeVirt collection on Harvester

Follow [KubeVirt installation](docs/KUBEVIRT.md): copy its values template, set the OTLP endpoint and integration name, prepare ingestion and registry Secrets, verify the four TLS identities, then install the upstream OpenTelemetry chart with the public CA bundle. The guide includes the complete Helm command.

Guest memory needs balloon statistics; guest filesystems need QEMU Guest Agent. Powered-off VMs have no current usage. Skip this step without Harvester.

### 4. Publish the dashboards once

Create the publishing Secret using [the credential procedure](docs/PREREQUISITES.md#publishing-credentials). Edit `config/local/dashboards.values.yaml`:

```yaml
observability:
  url: https://observability.example.com
auth:
  existingSecret: suse-observability-dashboard-token
  serviceTokenKey: serviceToken
```

```bash
helm upgrade --install suse-observability-dashboards ./charts/suse-observability-dashboards \
  --kubeconfig "$SRE_CENTRAL_KCFG" --kube-context "$SRE_CENTRAL_CTX" \
  --namespace "$SRE_CENTRAL_NS" --values config/local/dashboards.values.yaml \
  --wait --timeout 5m
```

The finite Job publishes native definitions through the SUSE API; `Completed` is its expected state. It does not install Grafana or a separate Perses server.

**Upgrade behavior:** managed dashboards are recreated by name to ensure their full definitions are updated with the validated CLI version. IDs can change, and manual edits to managed dashboards are replaced. See [Updates and removal](docs/OPERATIONS.md#updates-and-removal).

### 5. Publish the monitors once

Prepare the separate monitor role and Secret using [the credential procedure](docs/PREREQUISITES.md#publishing-credentials). Edit `config/local/monitors.values.yaml`:

```yaml
observability:
  url: https://observability.example.com
auth:
  existingSecret: suse-observability-monitor-token
  serviceTokenKey: serviceToken
```

```bash
helm upgrade --install suse-observability-monitors ./charts/suse-observability-monitors \
  --kubeconfig "$SRE_CENTRAL_KCFG" --kube-context "$SRE_CENTRAL_CTX" \
  --namespace "$SRE_CENTRAL_NS" --values config/local/monitors.values.yaml \
  --wait --timeout 10m
```

The publisher preserves monitor identifiers by name and verifies persisted definitions. Expect `persisted_monitors: 24` in the output. Confirm Enabled state and component mapping in SUSE. **Configure notification channels and routing separately**; publication does not prove notification delivery.

## Use the dashboards

1. Open **SUSE Observability → Dashboards** and select a dashboard.
2. Start with **Everything**, then select the cluster and applicable namespace, application or VM.
3. After changing the cluster, reset dependent filters to **Everything**. Disabling “Include everything” without selecting a value means **None**.
4. Choose the time window and refresh before comparing a new test. A 24-hour panel has partial history until a full day is collected.
5. Open `?` for explanations. Expand `+N more` to see all rows in a compact legend.

Viewer filter changes are not saved into the managed definition. Gauges show the **highest selected utilization**, not an average. `1000 mCPU = 1 vCPU`; `1 GiB = 1024 MiB`.

The five-minute request rate smooths short bursts. The recent rate averages the latest scrape interval, normally 30 seconds; it is not a true one-second measurement. Average response time is the sum of durations divided by completed requests. A p95 of 200 ms means about 95 of 100 calls finished within 200 ms.

Counts have no `K`/`M` abbreviation, but rolling-window increases remain estimates from sampled counters. Metrics show error codes, periods and routes where available. Individual exceptions or failure reasons need [logs or traces](docs/APPLICATION_METRICS.md).

## Validate the installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
bash scripts/validate.sh

kubectl get daemonset,deployment,pods \
  --kubeconfig "$SRE_CLUSTER_KCFG" --context "$SRE_CLUSTER_CTX" \
  --namespace "$SRE_AGENT_NS" \
  --selector app.kubernetes.io/name=sre-platform-telemetry

python scripts/audit-collector-logs.py \
  --kubeconfig "$SRE_CLUSTER_KCFG" --context "$SRE_CLUSTER_CTX" \
  --namespace "$SRE_AGENT_NS" --since 10m --output /tmp/collector-check.json

kubectl get jobs \
  --kubeconfig "$SRE_CENTRAL_KCFG" --context "$SRE_CENTRAL_CTX" \
  --namespace "$SRE_CENTRAL_NS"
```

In Metrics Explorer, inspect `up{job="sre-node"}`, `up{job="sre-etcd"}` and `up{job="traefik"}` for enabled targets and verify sample timestamps. Allow two scrapes and ingestion time before testing rates. [Operations and troubleshooting](docs/OPERATIONS.md) includes per-panel API tests and visual acceptance.

`No data` can mean no traffic, no matching resource, a stopped VM, an unsupported metric or broken collection. It is not automatically an error or proof of health.

## Customize

| Change | Edit |
| --- | --- |
| Environment, endpoints, Secrets and collector settings | Your ignored `config/local/*.values.yaml` files |
| Dashboard titles and explanations | `charts/suse-observability-dashboards/tools/presentation-en.yaml` |
| Queries, units and layout | `charts/suse-observability-dashboards/tools/generate_dashboards.py` |
| Monitor queries, thresholds and runbooks | `scripts/generate-alerts.py` |
| Application instrumentation | Follow [the metric contract](docs/APPLICATION_METRICS.md) |

Generated YAML and STY files are included, so initial installation does not require generators. After changing their sources:

```bash
python3 charts/suse-observability-dashboards/tools/generate_dashboards.py
python3 scripts/generate-alerts.py
bash scripts/validate.sh
```

Review the diff, increment the affected chart version and upgrade that release. Each chart README explains its values and lifecycle.

## Repository contents

```text
charts/          Three Helm charts and their generated definitions
config/          Generic templates; copy into ignored config/local/
integrations/    RKE2 Traefik, Agent coverage and access-log fragments
alerts/          Catalog of 24 native monitors
scripts/         Generators, validators and configuration helpers
docs/            Prerequisites, KubeVirt, application metrics and operations
.github/         Automated repository validation
```

Private environment values, kubeconfigs, credentials, raw telemetry, laboratory reports and generated Word files are excluded from this public repository.

## References

- [SUSE Observability documentation](https://documentation.suse.com/suse-observability/latest/)
- [RKE2 Helm and HelmChartConfig](https://docs.rke2.io/helm/)
- [Traefik metrics](https://doc.traefik.io/traefik/reference/install-configuration/observability/metrics/)
- [etcd metrics](https://etcd.io/docs/v3.6/metrics/)
- [OpenTelemetry Collector Helm chart](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-collector)
- [SUSE Observability GenAI dashboards](https://github.com/doccaz/suse-observability-genai-dashboards) — reference for the installation-first documentation structure.

This community project is not an official SUSE product or support commitment.
