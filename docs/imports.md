# VMware imports with VM Import Controller

Follow VMware imports into Harvester: which imports are active, completed or failed, which disks are ready, and whether the inventory is up to date. This module installs one dashboard and a read-only collector. It does not start imports, contact vCenter or change VMs. Coriolis is not included.

This is a community lab integration, **not recommended for production**.

<a id="before-installing"></a>

## 1. Check the requirements

Complete the [common setup](prerequisites.md). VM Import Controller must already be enabled on Harvester. Check its CRD:

```sh
kubectl get crd virtualmachineimports.migration.harvesterhci.io \
  --kubeconfig /path/to/harvester.yaml --context harvester
kubectl get virtualmachineimports.migration.harvesterhci.io --all-namespaces \
  --kubeconfig /path/to/harvester.yaml --context harvester
```

If the add-on is present but disabled, edit it and set `spec.enabled: true`, preserving its other settings:

```sh
kubectl edit addons.harvesterhci.io vm-import-controller --namespace harvester-system \
  --kubeconfig /path/to/harvester.yaml --context harvester
```

Confirm the namespace with `kubectl get addons.harvesterhci.io --all-namespaces` using your kubeconfig and context if it differs. Follow the [Harvester VM Import guide](https://docs.harvesterhci.io/v1.8/advanced/addons/vmimport/) to configure the controller and prepare actual migrations. Enabling the add-on does not start an import.

By default, the collector needs only permission to list `virtualmachineimports`; the chart supplies that RBAC. It does not read VMware credentials. It uses HTTPS remote write, so it does not need an OTLP endpoint or the Application Collection image Secret.

## 2. Add the repository

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

**Expected result:** Helm confirms the repository is available.

## 3. Fill in your settings

Save as `imports.yaml`:

```yaml
clusterName: my-harvester
observability:
  url: https://observability.example.com
```

Replace the values, kubeconfig and context with your own:

## 4. Install the module

This command installs the module and waits for it to finish. Keep the values file for updates and reinstalls.

```sh
helm upgrade --install obs-imports obs-dashboards/suse-observability-imports \
  --version 1.8.0 --values imports.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports `STATUS: deployed`. Successful publishing Jobs are removed automatically.

## 5. Check the result

```sh
kubectl get deployment/obs-imports-imports \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl logs deployment/obs-imports-imports --container import-inventory --since=5m \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

**Expected result:** collector workloads are ready. Deployments should have all replicas ready, and DaemonSets should be ready on every expected node. Successful publishing Jobs are removed automatically.

Open **Virtualization · VMware Import Progress**. Compare import names, phases and disk counts with the objects returned by kubectl. Zero imports is valid when the inventory is healthy. Missing CRDs, denied access and stale collection are not a healthy zero.

## What the numbers mean

| Panel | Meaning |
|---|---|
| Import counts and phases | Import objects still retained in Kubernetes |
| Active import age | Time since the object was created, including time waiting |
| Ready and failed disks | Disk objects, not transfer percentage |
| Disk capacity | Logical bytes reported by the controller, not bytes already copied |
| Recorded intervals | Specific controller timestamps; not full migration duration |
| Inventory health and age | Whether the collector can still read recent data |

There is no reliable global completion percentage or ETA in this contract. `virtualMachineRunning` is controller success; still check the guest OS, networking and application. Deleting an import object removes it from current inventory, while old metrics follow SUSE retention.

Validated with VM Import Controller **1.8.2**, API `migration.harvesterhci.io/v1beta1`. Existing completed imports were checked live; no new migration was started. Three monitors cover failed/invalid imports, inventory failure and optional performance scrape failure. See [alert coverage](alerts.md). See [metric limits](metric-contracts.md), [multiple clusters](multiple-clusters.md) and [removal](lifecycle.md).

## 6. Remove this module

Keep the publishing Secret available. The following command removes this release and, in the default mode, its managed dashboards and monitors:

```sh
helm uninstall obs-imports \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports the release was uninstalled. Your applications, VMs, volumes, SUSE server, official Agent and shared Secrets remain. Do not delete the namespace. A `telemetry` release only removes its collectors.

To reinstall, repeat step 4 with the same values file. If removal fails, follow [the removal guide](lifecycle.md#3-if-removal-fails) before retrying. Older versions need the [upgrade step](lifecycle.md#moving-from-120-or-121) first.

## Optional: CPU, memory and network during imports

To investigate slow imports, add this to `imports.yaml`, then repeat the Helm install command:

```yaml
imports:
  performance:
    enabled: true
```

This is disabled by default because it grants the collector extra cluster permissions: `get/list/watch` on Nodes and `get` on `nodes/metrics`. The kubelet permission can read metrics for other Pods too; the collector discards them before sending data. It does not grant `nodes/proxy`, Pod exec, Secret access or write access. The Harvester administrator must approve this access.

The collector connects directly to each node's InternalIP on TCP/10250, with its ServiceAccount token and TLS certificate verification. The kubelet certificate must be trusted by the cluster CA and cover the node IP. Do not disable TLS verification to work around a certificate error. IPv4 InternalIP endpoints were validated; IPv6-only nodes need a reviewed discovery configuration.

Enabling performance also selects a larger collector budget automatically: 128 MiB requested and 512 MiB maximum memory, with 50m requested and 500m maximum CPU. The inventory-only profile stays smaller. Override `imports.performance.resources` if the size or number of your nodes requires it. The kubelet sends its full response before Pod filtering, so retaining only a few series does not eliminate parsing costs. See [vmagent memory usage](https://docs.victoriametrics.com/vmagent/#troubleshooting) for tuning.

The chart retains only CPU, working-set memory and network byte counters for the default `harvester-vm-import-controller-*` Pods in `harvester-system`, and `bim-*`, `backing-image-manager-*`, `backing-image-ds-*` Pods in `longhorn-system`. Custom namespaces/names and host-networked replacements are outside this contract. It parses the kubelet response as a stream, with a 64 MiB response limit. Large clusters may need a separate capacity review.

| New panels | How to use them |
|---|---|
| Import controller: incoming/outgoing network traffic | Bytes/s per Pod interface, averaged over five minutes. Compare drops in traffic with import stages and controller logs. |
| Import controller: CPU and memory | Compare resource use with slowdowns while exporting disks or serving images. CPU is mCPU (1000 = one core), memory is working-set bytes. Use limits, throttling and logs to confirm resource pressure. |
| Shared image services: incoming/outgoing network traffic | Longhorn image infrastructure activity. Includes other image operations; do not attribute it exclusively to one import. |
| Can we collect import performance metrics? | Each expected node should report `1`. No series means no discovered target or missing delivery; `0` means a failed scrape. |

These panels follow the **Cluster** filter only. Import name and namespace filters apply to the import inventory, not shared infrastructure. Receive and transmit describe different directions and must not be added as unique bytes migrated. No per-import bandwidth, transfer percentage, link utilization percentage or ETA is claimed.

Check the collector after enabling it:

```sh
kubectl logs deployment/obs-imports-imports --container vmagent --since=5m \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl auth can-i get nodes --subresource=metrics \
  --as=system:serviceaccount:suse-observability:obs-imports-imports \
  --kubeconfig /path/to/harvester.yaml --context harvester
```

The authorization check requires impersonation permission on your own account. Confirm fresh values in SUSE as well. The collector being Ready alone does not validate its scrape. Disabling `imports.performance.enabled` with the same Helm command removes these extra RBAC rules and stops performance collection; import progress remains available.
