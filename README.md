# SUSE Observability dashboards with Helm and Fleet

Five readable dashboards, 33 custom SUSE monitors, and the additional collectors needed for RKE2 and Harvester. Version 6 was tested against the live lab on **11 September 2026**. See [validation results and limits](tests/RESULTADOS.md).

This is a custom integration package. It requires an existing SUSE Observability server and the official Kubernetes Agent. It does not install the server, instrument arbitrary applications, or configure notification destinations.

## Download this version

This version is published on the [`helm-fleet-v6` branch](https://github.com/kaioneuhauss/suse-observability-dashboards/tree/helm-fleet-v6). Clone that branch before following this README:

```bash
git clone --branch helm-fleet-v6 --single-branch https://github.com/kaioneuhauss/suse-observability-dashboards.git
cd suse-observability-dashboards
```

Run local checks with `python -m pip install -r requirements-dev.txt`, `python -m unittest discover -s tests -v`, and `bash tests/helm-checks.sh`. These checks do not deploy to a cluster.

## What to install

| Chart | Where | What it does |
|---|---|---|
| `sre-platform-telemetry` | Once in each monitored cluster | Host, etcd, Traefik and read-only Pod configuration inventory; Prometheus remote write |
| `sre-kubevirt-telemetry` | Once in Harvester | KubeVirt and VM metrics; OTLP with verified TLS |
| `suse-observability-content` | Once in the central server cluster | All selected dashboards and monitors, using two separate publisher identities |

The central chart contains **Instrumented apps**, **Workload Resource Efficiency**, **Kubernetes Platform Health**, **Traefik Ingress Health**, and **Harvester VM & Host Health**. Keep these separate views: each answers a different operational question and uses different filters. They share one installation and one SUSE URL.

## 1. Prepare your environment

Use Helm 3 and kubectl. Run the commands from the extracted package root. Choose either manual Helm or Fleet for a release; do not use both to reconcile it.

```bash
export OBS_KCFG=/path/to/observability.yaml
export RAN_KCFG=/path/to/rancher.yaml
export HRV_KCFG=/path/to/harvester.yaml
```

The examples below use contexts `observability`, `rancher-kaio`, and `harvester`. Replace these with your real context names. Kubernetes context names and SUSE integration names are different concepts.

Before installing:

1. Install the official Agent in every cluster. Confirm its integration is receiving topology and metrics in SUSE. On Harvester, use the supported process for your version; the documented v1.8 add-on is Experimental. Do not install a second Agent over it.
2. Get each integration name from the Agent's `suse-observability-agent-cluster-name` ConfigMap. Use that exact `STS_CLUSTER_NAME` as `clusterName` in this package.
3. Confirm the intake Secret exists **in the collector namespace**: `suse-observability-agent-secrets`, key `STS_API_KEY`. Secret names can be customized.
4. Prepare the two publisher Service Tokens in the central namespace. [Exact role and Secret commands](docs/REFERENCIA-OPERACIONAL.md#1-cliente-novo-roles-e-secrets-dos-publicadores) are provided. These credentials are used by every Helm/Fleet publication, not just by an assistant. Dashboard ownership matters when updating existing objects.
5. Confirm outbound HTTPS, DNS, trusted CA chains, and access to the image registries. Private CAs and registry credentials belong in local Secrets/ConfigMaps, never in Git.

The lab uses `suse-observability-agent` for the Observability cluster's collectors, and `suse-observability` for the Rancher and Harvester collectors. The central publisher uses `suse-observability`. Adjust both commands and Fleet namespaces if your layout differs.

### RKE2 and Traefik

Only enable Traefik collection on clusters that actually run Traefik. Harvester in this lab uses NGINX, so its Traefik collector is disabled.

For a Rancher-provisioned RKE2 cluster, merge [the Rancher fragment](prerequisites/rancher-rke2-traefik.yaml) into `spec.rkeConfig.chartValues.rke2-traefik` in **Edit Config → Edit as YAML**. For a local/imported cluster, merge [the HelmChartConfig values](prerequisites/rke2-traefik-values.yaml) into the existing `rke2-traefik` HelmChartConfig in `kube-system`. Preserve the configuration's existing owner/source.

Required Traefik settings:

```yaml
metrics:
  prometheus:
    entryPoint: metrics
    addEntryPointsLabels: true
    addServicesLabels: true
ports:
  metrics:
    port: 9100
    expose:
      default: false
```

Do not publish port 9100 through an Internet-facing Service. If existing NetworkPolicies isolate Traefik, allow the collector to reach this port. The lab's Rancher profile enables a narrowly scoped policy after confirming existing web access rules. **Do not copy that opt-in blindly:** creating the first policy can isolate traffic that was previously allowed. [Detailed checks](docs/GUIA-HELM-FLEET.md#5-pré-requisito-rke2-configurar-o-traefik).

### RKE2 etcd

The collector runs on etcd nodes with host networking and reads `127.0.0.1:2381/metrics`. It does not connect to the client API on 2379. The tested clusters already provided this local endpoint. `etcd-expose-metrics` exposes metrics on the client interface and is not required by this local collection design. Confirm the actual endpoint and etcd node labels before enabling the collector; do not open the endpoint publicly. [Detailed procedure](docs/GUIA-HELM-FLEET.md#51-confirmar-as-métricas-locais-do-etcd).

### Harvester and KubeVirt

Prepare these before installing the KubeVirt chart:

- An authenticated TLS OTLP gRPC endpoint on the SUSE server. Merge [the OTLP fragment](prerequisites/otlp-ingress-values.yaml) into the **complete values of the existing server release**, if the endpoint is not already configured.
- The public KubeVirt CA, copied from the Harvester `kubevirt-ca` ConfigMap into `kubevirt-metrics-ca` in the collector namespace. Verify each component's certificate SAN; update the configured server names when required by your version.
- A valid registry pull Secret such as `application-collection` in that namespace.

The guide includes copyable commands for [OTLP, CA and registry preparation](docs/GUIA-HELM-FLEET.md#4-pré-requisitos-de-kubevirt-e-otlp). A copied CA does not rotate automatically: refresh it and increment `kubevirt.ca.revision` after rotation. Keep TLS verification enabled.

## 2. Edit five configuration files

Change the lab hostnames and cluster names before deploying to a customer.

| File | Change |
|---|---|
| `charts/sre-platform-telemetry/config/observability-cluster.yaml` | Integration name, remote-write URL/Secret, etcd and Traefik selection |
| `charts/sre-platform-telemetry/config/rancher-kaio.yaml` | Same fields; review the opt-in NetworkPolicy |
| `charts/sre-platform-telemetry/config/harvester.yaml` | Same fields; keep Traefik disabled when absent |
| `charts/sre-kubevirt-telemetry/config/values.yaml` | Harvester integration name, OTLP endpoint, CA and registry Secret |
| `charts/suse-observability-content/config/values.yaml` | SUSE URL, the two publisher Secrets, dashboards/monitors to include |

Defaults live in each chart's root `values.yaml`. Only environment-specific overrides belong in `config/`. There are no Python-generated Helm values and no separate configuration file for each dashboard.

```bash
bash tests/helm-checks.sh
```

This checks rendering and invalid settings. It does not prove that the target can pull images, authenticate, or deliver metrics. Apply a server dry-run of rendered resources where admission policies require it, then validate a canary installation.

## 3. Install the collectors with Helm

Start with the Observability cluster:

```bash
helm upgrade --install sre-platform-telemetry ./charts/sre-platform-telemetry \
  --kubeconfig "$OBS_KCFG" --kube-context observability \
  -n suse-observability-agent \
  -f charts/sre-platform-telemetry/config/observability-cluster.yaml \
  --wait --timeout 10m
helm test sre-platform-telemetry --kubeconfig "$OBS_KCFG" \
  --kube-context observability -n suse-observability-agent --logs --timeout 3m
```

After checking collection and ingestion, deploy the remaining profiles:

```bash
helm upgrade --install sre-platform-telemetry ./charts/sre-platform-telemetry \
  --kubeconfig "$RAN_KCFG" --kube-context rancher-kaio -n suse-observability \
  -f charts/sre-platform-telemetry/config/rancher-kaio.yaml --wait --timeout 10m
helm test sre-platform-telemetry --kubeconfig "$RAN_KCFG" \
  --kube-context rancher-kaio -n suse-observability --logs --timeout 3m
helm upgrade --install sre-platform-telemetry ./charts/sre-platform-telemetry \
  --kubeconfig "$HRV_KCFG" --kube-context harvester -n suse-observability \
  -f charts/sre-platform-telemetry/config/harvester.yaml --wait --timeout 10m
helm upgrade --install kubevirt-otel-collector ./charts/sre-kubevirt-telemetry \
  --kubeconfig "$HRV_KCFG" --kube-context harvester -n suse-observability \
  -f charts/sre-kubevirt-telemetry/config/values.yaml --wait --timeout 10m
```

Check ready Pods, logs, all expected targets, recent samples, and delivery queues. `helm test` verifies reachability of every Traefik metrics endpoint; it does not prove SUSE ingestion. In Metrics Explorer:

```promql
up{job=~"sre-node|sre-etcd|traefik"}
sre_pod_inventory_success
up{service_name="kubevirt-metrics"}
```

Compare the number of healthy targets with the actual inventory. One healthy sample is insufficient when three replicas should be collected.

## 4. Publish all dashboards and monitors

```bash
helm upgrade --install suse-observability-content ./charts/suse-observability-content \
  --kubeconfig "$OBS_KCFG" --kube-context observability -n suse-observability \
  -f charts/suse-observability-content/config/values.yaml --wait --timeout 15m
kubectl logs job/suse-observability-content-dashboards \
  --kubeconfig "$OBS_KCFG" --context observability -n suse-observability
kubectl logs job/suse-observability-content-monitors \
  --kubeconfig "$OBS_KCFG" --context observability -n suse-observability
```

Both Jobs must complete and report verified persisted content. Open the five shared dashboards. Select the cluster, then reset dependent namespace/application filters to Everything before choosing a new value. Ordinary filter changes should not ask you to save; editing a widget still does.

Set `dashboards.include` to select views. `monitors.include: []` includes all 33 rules; use slugs from [the catalog](charts/suse-observability-content/files/catalog.json) for a subset. Disabling a section prevents publication; it does not delete existing objects.

For a v5 migration, export existing SUSE objects and keep the owner token. Pause old Fleet reconciliation, install the consolidated content chart, verify it, then uninstall only the obsolete custom publisher releases. The guide explains [ownership, backup and deletion](docs/REFERENCIA-OPERACIONAL.md).

## 5. Use Fleet instead of manual Helm

Each chart is a self-contained Fleet bundle. It includes the chart, `fleet.yaml`, and `config/` files. `valuesFiles` explicitly loads root defaults first and profile overrides second. The same files are used by manual Helm.

1. Publish **this package's contents** at the root of your Git branch. The supplied GitRepos reference `helm-fleet-v6`; creating or extracting a ZIP does not publish that branch.
2. Edit `fleet/gitrepo-*.yaml`: repository URL, branch, paths and workspace namespaces.
3. On the management cluster, list `clusters.fleet.cattle.io -A`. Label only the intended Fleet Cluster objects with `observability.example.com/enabled=true` and `observability.example.com/cluster=<integration-name>`. Do not label Kubernetes Nodes for this selection. Align those labels with `targetCustomizations` in the chart's `fleet.yaml`.
4. Put downstream GitRepos in their Fleet workspace, usually `fleet-default`. The management/local cluster may be in `fleet-local`, requiring its separate GitRepo.
5. Apply collectors first. After metric acceptance, apply content:

```bash
kubectl apply -f fleet/gitrepo-collectors.yaml \
  --kubeconfig "$RAN_KCFG" --context rancher-kaio
kubectl apply -f fleet/gitrepo-management.yaml \
  --kubeconfig "$RAN_KCFG" --context rancher-kaio
# After collector acceptance:
kubectl apply -f fleet/gitrepo-content.yaml \
  --kubeconfig "$RAN_KCFG" --context rancher-kaio
```

Unmatched clusters are excluded. Content targets the central cluster; KubeVirt targets Harvester; platform uses a profile per matching cluster. For another cluster, add one platform profile and one matching target customization.

Do not enable `force` or `takeOwnership` to bypass conflicts with an existing manually managed release. Plan the transition and preserve Secrets/CA. Fleet reconciles Kubernetes resources, not continuous drift in the external SUSE API. Increment `lifecycle.revision` to rerun publication. See [the full Fleet procedure](docs/GUIA-HELM-FLEET.md#9-usar-os-mesmos-charts-no-fleet).

## 6. Configure notifications and operational acceptance

Monitors and notification delivery are separate. Configure a SUSE notification with the required project monitors, severity, component scope, and an approved destination. Test channel connectivity, then opening and recovery, and confirm cluster, resource, observed value, threshold and investigation link in the delivered message. This package does not contain your Slack, Teams, email or webhook credentials.

The publisher role can import/status-check monitors. A 403 from `sts monitor run` with that role does not mean scheduled evaluations are failing. Use an authorized operator for runtime test actions; do not grant administrator privileges to the publisher.

In this lab, both the built-in email test and real HTTP monitor opening emails were received and confirmed by the recipient. The recipient also confirmed the recovery emails. Configure SMTP globally on the SUSE server and create notification rules manually; this is the agreed operating model, and no notification publisher credentials are required.

## Reading the charts correctly

- **Requests/s, five-minute average:** requests divided over a moving 300-second window. A short load test has a higher rate while it is running.
- **Benchmark comparison:** allow collection and ingestion, then click Refresh. A 3-second browser test cannot be directly compared with a five-minute rate.
- **Average response time:** add all response times and divide by request count. Three requests taking 50, 100 and 150 ms average 100 ms.
- **p95:** approximately 95 of 100 requests completed within this time; histogram bucket precision applies.
- **Pod usage:** sum of measured regular containers. Requests and limits are configuration, not consumption. Counts of missing settings count each running Pod once.
- **VM memory:** guest available/used memory differs from virt-launcher working set and the VM's configured memory. Some guest metrics require working balloon/guest-agent support.
- **VM scheduler delay:** time waiting for a host CPU, averaged per vCPU; it is not automatically equivalent to VMware CPU Ready.
- **Virtual disk response time:** accumulated I/O time divided by completed operations. Idle disks have no defined average; cloud-init disks are excluded.
- **No data:** check applicability and collection health. A single-member etcd has no peer RTT. Block PVCs do not have filesystem usage. An idle disk has no measured latency. Do not turn every missing series into zero.

HTTP error charts identify code, route/application, and time window. Root cause and individual request IDs require logs/traces; arbitrary request IDs and full URLs must not become metric labels.

A newly created counter series needs a baseline scrape. If its first sample is already 100 after a short test, `increase()` cannot reconstruct those initial 100 events. Warm the route/status series, wait for a successful scrape, then start the measured test.

## Repository layout

```text
charts/          Three charts, their Fleet definitions and environment profiles
fleet/           Three GitRepo manifests for phased rollout and workspace separation
prerequisites/   Fragments to merge into existing Agent, Traefik and server configuration
docs/            Portuguese customer procedure, study guide, PDFs and impact analysis
examples/        Optional private CA, image and metric allowlist overrides
tests/           Regression checks and the recorded acceptance results
scripts/         Read-only live query/filter audit
images/          Optional publisher image for restricted networks
```

For production, review image digests, resource limits, CA/token rotation, admission policy, telemetry loss/backlog monitoring and receiver availability. The defaults use bounded collection and TLS validation, but this custom package is not a vendor certification or a complete SRE program. SLOs, external availability probes, backups/restore tests and notification ownership remain environment-specific.

See [alert thresholds and all panel mappings](docs/ALERT-COVERAGE.md) for investigation guidance and notification boundaries.

Estimated request totals and breakdowns follow the toolbar time period. Five-minute traffic and response-time windows remain explicitly labelled. See [implementation and compatibility](docs/REFERENCIA-OPERACIONAL.md#totals-that-follow-the-selected-time-period).

## Guides and resource budgets

- [Customer deployment procedure (PDF)](docs/Guia-SUSE-Observability-Helm-Fleet-v6.pdf) and [copyable Markdown](docs/GUIA-HELM-FLEET.md): prerequisites, editable files, Helm/Fleet commands and acceptance.
- [Study guide (PDF)](docs/Guia-Estudo-SUSE-Observability-v6.pdf) and [Markdown](docs/GUIA-ESTUDO.md): how the charts, queries, dashboards and monitors work.
- [CPU, memory, storage and security assessment](docs/IMPACTO-E-SEGURANCA.md): measured collector overhead, server history, storage scenarios and limitations.
- [Request-by-request acceptance matrix](tests/MATRIZ-SOLICITACOES.md).

Every chart component has CPU and memory requests and limits, including publisher and test Jobs. Helm schemas reject missing or zero budgets. Keep headroom for bursts; measured idle usage is not a safe limit. SMTP and notification rules remain manual. Use `sre-dashboards` for all project monitors or a `dashboard-*` tag for a specific dashboard, as listed in [alert coverage](docs/ALERT-COVERAGE.md).

