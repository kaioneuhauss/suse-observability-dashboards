# Install across multiple clusters

Publish each module **once per SUSE instance**. Its existing cluster filter will show the source clusters as their data arrives.

| Mode | What Helm installs | Publishing Secret needed? |
|---|---|---|
| `all` (default) | Collectors, dashboards and monitors | Yes |
| `telemetry` | Collectors only | No |
| `content` | Dashboards and monitors only | Yes |

Applications always uses `content`. Do not install two publishers for the same module and SUSE instance.

## 1. Add a second source to an existing installation

If your first cluster already publishes a module, keep that release. Prepare the second cluster's [prerequisites](prerequisites.md), save its own module file, and add `mode: telemetry` at the top:

```yaml
mode: telemetry
clusterName: second-cluster
observability:
  url: https://observability.example.com
```

For example, save this as `traefik-second.yaml`, then run:

```sh
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.8.0 --values traefik-second.yaml \
  --kubeconfig /path/to/second-cluster.yaml --kube-context second-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Expected:** collectors run on the second cluster, no publishing Jobs run there, and its name appears in the existing dashboard after data arrives. For Virtualization, also set the OTLP endpoint and prepare its registry/network requirements.

## 2. Keep publishers on the Observability cluster

This is the arrangement used in the lab reinstall. Use this procedure **instead of** the README's default `all` installation. All installation and removal commands below use Helm and kubectl.

### A. Record where each release belongs

Example with three clusters:

| Destination | Namespace | Releases | Mode |
|---|---|---|---|
| Harvester | Its Agent namespace | `obs-virtualization`, optional `obs-imports` | `telemetry` |
| Rancher/RKE2 | Its Agent namespace | `obs-kubernetes`, optional `obs-traefik` | `telemetry` |
| Observability cluster, monitoring its own workloads | Its Agent namespace | `obs-kubernetes`, optional `obs-traefik` | `telemetry` |
| Observability cluster, publishing content | `suse-observability` | One release per selected module | `content` |

Replace the kubeconfig paths, contexts, namespace and integration names in the examples. A Helm release is identified by **cluster + namespace + release name**. In the lab, the Observability Agent uses `suse-observability-agent`, so collectors and publishers can use the same release names in different namespaces. If your Agent and publishers share a namespace, use a separate publishing namespace or distinct release names; do not overwrite a telemetry release with content mode accidentally.

Prepare the [prerequisites](prerequisites.md) first. Keep the publishing credential on the central cluster only. Add the chart repository once:

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

### B. Install the Harvester collectors

Save **`harvester-virtualization.yaml`**:

```yaml
mode: telemetry
clusterName: harvester
observability:
  url: https://observability.example.com
  otlpEndpoint: otlp-observability.example.com:443
```

If [the network check](network-access.md) confirms existing Longhorn isolation, add:

```yaml
virtualization:
  longhorn:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

If the local etcd metrics endpoint was checked and you want to collect it, also add:

```yaml
telemetry:
  etcd:
    enabled: true
```

Install:

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.8.0 --values harvester-virtualization.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

For optional Imports, save **`harvester-imports.yaml`**:

```yaml
mode: telemetry
clusterName: harvester
observability:
  url: https://observability.example.com
imports:
  performance:
    enabled: true
```

```sh
helm upgrade --install obs-imports obs-dashboards/suse-observability-imports \
  --version 1.8.0 --values harvester-imports.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected:** collector workloads are ready. There are no newly published dashboards yet. Imports performance requires the read-only kubelet access explained in the README.

### C. Install Kubernetes and Traefik collectors on RKE2

Save **`rancher-kubernetes.yaml`**:

```yaml
mode: telemetry
clusterName: rancher-cluster
observability:
  url: https://observability.example.com
```

Add `telemetry.etcd.enabled: true` as nested YAML only after checking the local endpoint, as shown above. Save a separate **`rancher-traefik.yaml`** with the same three base settings. Add the Traefik [selector or policy overrides](network-access.md#4-traefik-and-other-restrictions) only if your installation needs them.

```sh
helm upgrade --install obs-kubernetes obs-dashboards/suse-observability-kubernetes \
  --version 1.8.0 --values rancher-kubernetes.yaml \
  --kubeconfig /path/to/rancher.yaml --kube-context rancher \
  --namespace suse-observability --wait --timeout 15m
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.8.0 --values rancher-traefik.yaml \
  --kubeconfig /path/to/rancher.yaml --kube-context rancher \
  --namespace suse-observability --wait --timeout 15m
```

**Expected:** the selected collectors are ready. Skip Traefik if this cluster does not use it.

To monitor the Observability cluster's own workloads, save **`observability-kubernetes.yaml`** and **`observability-traefik.yaml`** the same way, changing `clusterName` to that Agent's actual integration name. In the lab this is `observability-cluster`, not the kubeconfig context `observability`:

```sh
helm upgrade --install obs-kubernetes obs-dashboards/suse-observability-kubernetes \
  --version 1.8.0 --values observability-kubernetes.yaml \
  --kubeconfig /path/to/observability.yaml --kube-context observability \
  --namespace suse-observability-agent --wait --timeout 15m
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.8.0 --values observability-traefik.yaml \
  --kubeconfig /path/to/observability.yaml --kube-context observability \
  --namespace suse-observability-agent --wait --timeout 15m
```

Do not add another host collector on Harvester: Virtualization already includes it. A central Kubernetes content release can use those metrics without duplicate collection.

### D. Publish the selected modules once

Create the publishing Secret in the central namespace using [prerequisite step 5](prerequisites.md#5-prepare-the-publishing-credential). Save **`content.yaml`**:

```yaml
mode: content
observability:
  url: https://observability.example.com
```

One file is enough for all five publishers when their common settings are the same. If you already use separate dashboard and monitor Secrets, add the overrides from [prerequisite step 7](prerequisites.md#7-custom-secret-names-or-private-certificates). Do not rotate identities during a reinstall.

Run only the module commands you need:

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.8.0 --values content.yaml \
  --kubeconfig /path/to/observability.yaml --kube-context observability \
  --namespace suse-observability --wait --timeout 15m
helm upgrade --install obs-imports obs-dashboards/suse-observability-imports \
  --version 1.8.0 --values content.yaml \
  --kubeconfig /path/to/observability.yaml --kube-context observability \
  --namespace suse-observability --wait --timeout 15m
helm upgrade --install obs-kubernetes obs-dashboards/suse-observability-kubernetes \
  --version 1.8.0 --values content.yaml \
  --kubeconfig /path/to/observability.yaml --kube-context observability \
  --namespace suse-observability --wait --timeout 15m
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.8.0 --values content.yaml \
  --kubeconfig /path/to/observability.yaml --kube-context observability \
  --namespace suse-observability --wait --timeout 15m
helm upgrade --install obs-applications obs-dashboards/suse-observability-applications \
  --version 1.8.0 --values content.yaml \
  --kubeconfig /path/to/observability.yaml --kube-context observability \
  --namespace suse-observability --wait --timeout 15m
```

**Expected:** all selected releases are deployed. Installing all five publishes nine dashboards and 39 monitors. No collectors run in the central content releases. Applications still needs compatible metrics arriving from your instrumented applications.

### E. Validate each destination

Run the [README checks](../README.md#5-check-that-it-works) with each cluster and namespace from the placement table. Confirm the expected workloads, fresh collection and cluster filters. Test a known resource in each source cluster. A central publishing Job succeeding does not prove that all remote collectors work.

## 3. Remove a module or start again

Keep the SUSE server and publishing credentials available until cleanup succeeds. Remove only the releases you installed.

### Remove only Imports

First remove its source collector, then its central content:

```sh
helm uninstall obs-imports --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability --wait --timeout 15m
helm uninstall obs-imports --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability --wait --timeout 15m
```

**Expected:** its collectors, dashboard and three monitors are gone. Other modules, VM Import Controller and import records remain.

### Remove the complete example

Run the Imports commands above, then remove the remaining source collectors:

```sh
helm uninstall obs-virtualization --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability --wait --timeout 15m
helm uninstall obs-kubernetes --kubeconfig /path/to/rancher.yaml --kube-context rancher --namespace suse-observability --wait --timeout 15m
helm uninstall obs-traefik --kubeconfig /path/to/rancher.yaml --kube-context rancher --namespace suse-observability --wait --timeout 15m
helm uninstall obs-kubernetes --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability-agent --wait --timeout 15m
helm uninstall obs-traefik --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability-agent --wait --timeout 15m
```

Remove the remaining central publishers:

```sh
helm uninstall obs-applications --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability --wait --timeout 15m
helm uninstall obs-traefik --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability --wait --timeout 15m
helm uninstall obs-kubernetes --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability --wait --timeout 15m
helm uninstall obs-virtualization --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability --wait --timeout 15m
```

**Expected:** no project releases/collectors remain, and its nine dashboards and 39 monitors are absent. The native dashboard, unrelated content, platforms, Agents, applications, VMs, volumes and metric history remain. Chart-owned cross-namespace policies are removed; existing platform policies remain.

Check `helm list` and `kubectl get deployment,daemonset,pods` in every destination, then refresh the SUSE dashboard/monitor lists. Do not remove namespaces or disable cleanup hooks. See [cleanup failure handling](lifecycle.md).

**Reinstall:** keep the prerequisites and seven saved values files. Repeat steps B–D, then E. The releases start again at revision 1 and managed dashboards receive new IDs. Update old bookmarks. No local installer script is needed.

## Already using Fleet?

Keep each release under one owner. These commands validate direct Helm management, not Fleet reconciliation. If Fleet owns a release, update its source instead of running a competing manual install.
