# SUSE Observability dashboards

Dashboards to help you understand your VMs, storage, Kubernetes clusters and applications. Pick the module you need, fill in a small values file and install it with Helm.

> [!WARNING]
> This is a community project for labs and learning. **It is not recommended for production** and is not an officially supported SUSE integration. Test it in your own environment before relying on the data or alerts.

Installation uses **kubectl and Helm only**. You do not need to clone this repository, run Bash or Python scripts, build charts, or install Grafana. Helm runs the collectors and publishing Jobs inside Kubernetes.

## Choose your module

| What do you have? | Module | What you get |
|---|---|---|
| SUSE Virtualization / Harvester | [virtualization](docs/virtualization.md) | VM & Host Overview, VM Performance, Capacity Planning, Storage & Backups |
| VMware imports with VM Import Controller | [imports](docs/imports.md) | VMware Import Progress |
| Traefik | [traefik](docs/traefik.md) | Incoming Traffic & Errors |
| Applications already sending HTTP metrics | [applications](docs/applications.md) | Traffic, Errors & Speed |
| Kubernetes / RKE2 | [kubernetes](docs/kubernetes.md) | Cluster Health, Application Resource Usage |

Each module has its own chart. If you only have Harvester, install `virtualization`. You do not need Traefik or the applications module. Add `imports` to follow VMware imports. Coriolis is not included.

## Before you start

You need:

- A working SUSE Observability instance and its HTTPS URL.
- The official SUSE Observability Agent on the cluster you want to monitor.
- kubectl, Helm 3 or 4, and a kubeconfig for that cluster.
- A publishing Service Token, provided by your SUSE Observability administrator.
- The extra requirements for your module, listed in its guide above.

**First time doing this?** Follow [Prepare your environment](docs/prerequisites.md). It explains how to find the cluster name, check the Agent and create the required Secret. The charts add dashboards and collectors to an existing environment; they do not install the SUSE server or instrument your applications.

## Install — Harvester example

This example installs the four Virtualization dashboards and their collectors. Use the namespace where the Agent is already installed. The examples use `suse-observability`; replace it if yours is different.

### 1. Add the Helm repository

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

### 2. Create your values file

Save this as `virtualization.yaml` in your text editor:

```yaml
clusterName: my-harvester
observability:
  url: https://observability.example.com
  otlpEndpoint: otlp-observability.example.com:443
```

Replace the three values:

| Value | Where it comes from |
|---|---|
| `clusterName` | The exact name of this cluster's Kubernetes integration in SUSE Observability. It may differ from your kubeconfig context. |
| `url` | The HTTPS address you use to open SUSE Observability. |
| `otlpEndpoint` | The OTLP gRPC address configured on your SUSE server, without `https://`. Only Virtualization needs this field. |

Before installing, finish the [Virtualization prerequisites](docs/virtualization.md#before-installing): OTLP, registry access and access to Longhorn metrics. The default Secret names are already set in the chart.

### 3. Install

Replace `/path/to/harvester.yaml` and the context `harvester` with your own kubeconfig details:

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.2.1 --values virtualization.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

Keep this values file. Use the same command to apply changes later. If you already have this module installed, use its existing release name, namespace and values file.

### 4. Check the result

```sh
kubectl get pods,jobs --kubeconfig /path/to/harvester.yaml --context harvester \
  --namespace suse-observability --selector app.kubernetes.io/instance=obs-virtualization
```

Collectors should be ready and publishing Jobs should show `Complete`. Then open **Dashboards → Virtualization · VM & Host Overview** in SUSE Observability and select your cluster. Compare **Running VMs** with Harvester. Allow a few minutes for the first samples.

If a panel shows **No data**, check the [validation guide](docs/validation.md). It does not automatically mean zero or healthy.

## Install another module

The same pattern applies: add the repository once, save a values file and run `helm upgrade --install`. Each module guide contains a complete example. Most only need `clusterName` and `observability.url`; applications only needs the URL.

For more than one cluster, publish each module's dashboards **once** and add collectors to the other clusters with `mode: telemetry`. See [Multiple clusters](docs/multiple-clusters.md). If Virtualization already collects Harvester host metrics, install Kubernetes with `mode: content` to reuse them.

## Remove a module

For the Virtualization example, first delete its dashboards and monitors while the publishing token still works:

```sh
helm upgrade obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.2.1 --reuse-values \
  --set lifecycle.action=delete --set lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Only continue if that command succeeds.** Then remove the release and its publishing Jobs:

```sh
helm uninstall obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 10m
kubectl delete job obs-virtualization-dashboards obs-virtualization-monitors --ignore-not-found \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

Use the **same chart version as the installed release** for deletion. The commands above assume 1.2.1. A `telemetry` release only needs `helm uninstall`. SUSE Observability, its history, official Agents, applications, VMs, volumes and shared Secrets stay in place. See [Update, remove and reinstall](docs/lifecycle.md) for other modules and older versions.

## More details

- [Prepare your environment](docs/prerequisites.md) · [Check the installation](docs/validation.md)
- [Understand the dashboards](docs/panel-guide.md) · [Virtualization dashboard guide](docs/virtualization-dashboards.md)
- [Metric definitions and limits](docs/metric-contracts.md) · [Lab results and test boundaries](docs/lab-validation.md)
- [Development](docs/development.md) · [Changelog](CHANGELOG.md)

The Virtualization topics were inspired by [doccaz/harvester-extra-dashboards](https://github.com/doccaz/harvester-extra-dashboards). These charts use native SUSE dashboards. The 34 included monitors need thresholds and notification rules that fit your environment; installing them does not prove that alerts reach your team.
