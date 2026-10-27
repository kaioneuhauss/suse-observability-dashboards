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

**Installing only SUSE Virtualization from zero? Start with [this complete walkthrough](docs/virtualization.md).** It covers the Agent, credentials, OTLP, the three settings to fill in, installation checks and removal. If your SUSE server already has these dashboards, add only collectors to the new cluster.

## 1. Prepare once

You need:

- A working SUSE Observability instance and its HTTPS URL.
- The official SUSE Observability Agent on the cluster you want to monitor.
- kubectl, Helm 3 or 4, and a kubeconfig for that cluster.
- A publishing Service Token, provided by your SUSE Observability administrator.
- The extra requirements for your module, listed in its guide above.

**First time doing this?** Follow [Prepare your environment](docs/prerequisites.md). It explains how to find the cluster name, check the Agent and create the required Secret. The charts add dashboards and collectors to an existing environment; they do not install the SUSE server or instrument your applications.

## 2. Fill in your settings — Harvester example

This example installs the four Virtualization dashboards and their collectors. Use the namespace where the Agent is already installed. The examples use `suse-observability`; replace it if yours is different.

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

## 3. Install

### Add the repository

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

**Expected result:** Helm confirms that the repository was added and updated. You only do this once on your computer.

Replace `/path/to/harvester.yaml` and the context `harvester` with your own kubeconfig details:

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.4.0 --values virtualization.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports `STATUS: deployed`. It waits for the collectors and publishing Jobs.

Keep this values file. Use the same command to apply changes later. If you already have this module installed, use its existing release name, namespace and values file.

## 4. Open your dashboards

```sh
kubectl get deployment/obs-virtualization deployment/obs-virtualization-pods daemonset/obs-virtualization-node --kubeconfig /path/to/harvester.yaml --context harvester \
  --namespace suse-observability
```

**Expected result:** collector workloads are ready. Successful publishing Jobs disappear automatically. Then open **Dashboards → Virtualization · VM & Host Overview** in SUSE Observability and select your cluster. Compare **Running VMs** with Harvester. Allow a few minutes for the first samples.

If a panel shows **No data**, check the [validation guide](docs/validation.md). It does not automatically mean zero or healthy.

## Add another module

The same pattern applies: add the repository once, save a values file and run `helm upgrade --install`. Each module guide contains a complete example. Most only need `clusterName` and `observability.url`; applications only needs the URL.

For more than one cluster, publish each module's dashboards **once** and add collectors to the other clusters with `mode: telemetry`. See [Multiple clusters](docs/multiple-clusters.md). If Virtualization already collects Harvester host metrics, install Kubernetes with `mode: content` to reuse them.

## 5. Remove when you no longer need it

With version **1.3.0 or later**, one command removes this module's collectors, dashboards and monitors. Keep the publishing Secret available until removal finishes:

```sh
helm uninstall obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports the release was uninstalled and the four Virtualization dashboards disappear from SUSE. Applications, VMs, volumes, official Agents, SUSE Observability and its metric history stay in place. Shared Secrets also stay in place. Do not delete the namespace.

To install again, repeat step 3 with the same values file. For backups, older chart versions, removal errors or multiple clusters, follow [Update, remove and reinstall](docs/lifecycle.md).

## Where to find things

| Folder | Use it for |
|---|---|
| `docs/` | Step-by-step guides and troubleshooting |
| `examples/` | Small values files to fill in |
| `charts/` | Chart source, if you want to inspect the templates |
| `helm/` | Packaged charts downloaded automatically by Helm |
| `dev/` | Maintainer tools and tests; not needed for installation |

## More details

- [Prepare your environment](docs/prerequisites.md) · [Check the installation](docs/validation.md)
- [Understand the dashboards](docs/panel-guide.md) · [Virtualization dashboard guide](docs/virtualization-dashboards.md)
- [Metric definitions and limits](docs/metric-contracts.md) · [Lab results and test boundaries](docs/lab-validation.md)
- [Development](dev/README.md) · [Changelog](docs/changelog.md)

The Virtualization topics were inspired by [doccaz/harvester-extra-dashboards](https://github.com/doccaz/harvester-extra-dashboards). These charts use native SUSE dashboards. The 34 included monitors need thresholds and notification rules that fit your environment; installing them does not prove that alerts reach your team.
