# SUSE Observability dashboards: install, use, remove

Add **five dashboards and 33 monitors** to an existing SUSE Observability installation. Three Helm charts provide the content and extra RKE2/Harvester metrics. Dashboards are in English; the [customer guide](docs/GUIA-HELM-FLEET.md) and [study guide](docs/GUIA-ESTUDO.md) are in Portuguese.

## 1. Download

Use the `helm-fleet-v6` branch. [Download the ZIP](https://github.com/kaioneuhauss/suse-observability-dashboards/archive/refs/heads/helm-fleet-v6.zip), extract it and open its directory, or use Git:

```bash
git clone --branch helm-fleet-v6 --single-branch \
  https://github.com/kaioneuhauss/suse-observability-dashboards.git
cd suse-observability-dashboards
```

The charts are already in `charts/`. You do not need to build them, run Python, or add a Helm repository.

## 2. Complete the prerequisites

| Where | Prepare once |
|---|---|
| Your workstation | Helm 3 or 4, kubectl, and a kubeconfig/context for each target |
| SUSE Observability server | Working server, Kubernetes integrations, publisher Secret; OTLP TLS endpoint if collecting KubeVirt |
| Every monitored cluster | Official SUSE Agent, its integration name and intake Secret, outbound access to SUSE |
| RKE2 clusters with Traefik | Enable internal Prometheus metrics in the existing Rancher/RKE2 Traefik configuration |
| RKE2/Harvester etcd nodes | Confirm the local metrics endpoint before enabling the etcd collector |
| Harvester | Agent, KubeVirt metrics CA and registry pull Secret; no Traefik collection when it uses NGINX |

Follow the [prerequisites, with commands and official links](prerequisites/README.md). SMTP stays in the server configuration; create notification rules manually in SUSE after publishing monitors.

**Do I need `sts`?** Only for initial publisher-token preparation if your administrator has not provided one. The chart runs the publishing commands itself. A new installation can use the default `stackstate-k8s-troubleshooter` role and one Secret for both Jobs. This role is broader than a dedicated publisher role; custom roles remain an optional least-privilege choice. [Token preparation and existing-installation rules](prerequisites/PUBLISHER.md).

## 3. Install the charts

Use one terminal per target. Set these four values for the cluster you are working on:

```bash
export KCFG=/path/to/cluster.yaml
export CTX=your-kubectl-context
export AGENT_NS=suse-observability
export CONTENT_NS=suse-observability
kubectl get nodes --kubeconfig "$KCFG" --context "$CTX"
mkdir -p local
```

`AGENT_NS` is where the official Agent and its intake Secret already exist. `CONTENT_NS` is where you place the publisher Secret. They may differ. Before upgrading an existing installation, keep its release names, namespaces and owner tokens.

### A. Platform metrics: once in each cluster

```bash
mkdir -p local/cluster
cp deploy/cluster/values.yaml local/cluster/values.yaml
```

Edit `local/cluster/values.yaml`: set `clusterName`, `remoteWrite.url`, and enable etcd/Traefik only after their prerequisites. For Harvester, copy `deploy/harvester/values.yaml` instead. For several clusters, keep separate local directories and change `-f` below accordingly.

```bash
helm upgrade --install sre-platform-telemetry \
  ./charts/sre-platform-telemetry \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$AGENT_NS" \
  -f local/cluster/values.yaml --wait --timeout 10m
```

Repeat A for each monitored cluster, including the central cluster's nodes. Use one platform release per cluster.

### B. VM metrics: once on Harvester

Switch `KCFG`, `CTX` and `AGENT_NS` to Harvester. Complete the CA, registry and OTLP prerequisites first.

```bash
mkdir -p local/virtual-machines
cp deploy/virtual-machines/values.yaml local/virtual-machines/values.yaml
```

Edit `clusterName` and `otlp.endpoint`; confirm the CA ConfigMap and Secret names. Then install:

```bash
helm upgrade --install kubevirt-otel-collector \
  ./charts/sre-kubevirt-telemetry \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$AGENT_NS" \
  -f local/virtual-machines/values.yaml --wait --timeout 10m
```

### C. Dashboards and monitors: once in the central cluster

Switch `KCFG` and `CTX` to the SUSE server cluster. Confirm the publisher Secret exists in `CONTENT_NS`.

```bash
mkdir -p local/central
cp deploy/central/values.yaml local/central/values.yaml
```

Edit `observability.url` and the Secret names if different. `dashboards.include` selects views; `monitors.include: []` includes all 33 rules. Select [monitor slugs](charts/suse-observability-content/files/catalog.json) when deploying only part of the collection.

```bash
helm upgrade --install suse-observability-content \
  ./charts/suse-observability-content \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$CONTENT_NS" \
  -f local/central/values.yaml --wait --timeout 15m
kubectl logs job/suse-observability-content-dashboards \
  --kubeconfig "$KCFG" --context "$CTX" -n "$CONTENT_NS"
kubectl logs job/suse-observability-content-monitors \
  --kubeconfig "$KCFG" --context "$CTX" -n "$CONTENT_NS"
```

For later upgrades, edit your existing local file and rerun its Helm command. Do not copy the example over your saved customer values.

## 4. Check and use

1. Confirm collector Pods are Ready and both publisher Jobs completed successfully. Follow the [acceptance checklist](docs/VALIDATION.md), including metrics from every expected target.
2. Open **Dashboards** in SUSE. Choose a cluster, then namespace/application. After changing a cluster, reset dependent filters to **Everything** before selecting another value.
3. Use the question-mark descriptions for units, time windows, thresholds and investigation steps. Five-minute request rates smooth short tests; selected-period totals follow the toolbar range.
4. Open **Monitors**, find the project's SRE monitors, and create your notification rule. Test a real opening and recovery before relying on email.

Helm success alone does not prove correct ingestion, filters or notification delivery. The lab's [validation summary](docs/VALIDATION.md) distinguishes observed results from customer acceptance still required.

## 5. Uninstall

Follow [the removal steps](docs/UNINSTALL.md). First remove the selected SUSE dashboards/monitors using the content chart's explicit delete action; then uninstall the three releases from their respective clusters. `helm uninstall` alone leaves the external SUSE content in place. Preserve the server, official Agent and shared Secrets.

## More detail, only when needed

| I want to... | Open |
|---|---|
| Deploy in a customer environment, in Portuguese | [Simple customer procedure](docs/GUIA-HELM-FLEET.md) / [PDF](docs/Guia-SUSE-Observability-Helm-Fleet-v6.pdf) |
| Understand charts, metrics and design | [Simple study guide](docs/GUIA-ESTUDO.md) / [PDF](docs/Guia-Estudo-SUSE-Observability-v6.pdf) |
| Deploy the same charts through Fleet | [Fleet procedure](docs/FLEET.md) |
| Estimate additional resources | [Short impact report](docs/IMPACTO-E-SEGURANCA.md) |
| Customize permissions, collectors, queries or thresholds | [Technical details directory](docs/details/README.md) |
| Audit every original requirement and test | [Request matrix](tests/MATRIZ-SOLICITACOES.md) / [detailed results](tests/RESULTADOS.md) |

This is a custom integration package. Tested lab baseline: SUSE Observability 2.10.2, CLI 3.3.6, Fleet 0.15.4, Helm 3.19/4.1. It does not install the SUSE server or automatically instrument applications. Confirm the supported configuration and perform acceptance tests in each customer environment.
