# VMware imports with VM Import Controller

Follow VMware imports into Harvester: which imports are active, completed or failed, which disks are ready, and whether the inventory is up to date. This module installs one dashboard and a read-only collector. It does not start imports, contact vCenter or change VMs. Coriolis is not included.

This is a community lab integration, **not recommended for production**.

## Before installing

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

The collector needs only permission to list `virtualmachineimports`; the chart supplies that RBAC. It does not read VMware credentials. It uses HTTPS remote write, so it does not need an OTLP endpoint or the Application Collection image Secret.

## Install

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

Save as `imports.yaml`:

```yaml
clusterName: my-harvester
observability:
  url: https://observability.example.com
```

Replace the values, kubeconfig and context with your own:

```sh
helm upgrade --install obs-imports obs-dashboards/suse-observability-imports \
  --version 1.2.1 --values imports.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

## Check it

```sh
kubectl get pods,jobs --selector app.kubernetes.io/instance=obs-imports \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl logs deployment/obs-imports-imports --container import-inventory --since=5m \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

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

Validated with VM Import Controller **1.8.2**, API `migration.harvesterhci.io/v1beta1`. Existing completed imports were checked live; no new migration was started. No automatic monitors are included. See [metric limits](metric-contracts.md), [multiple clusters](multiple-clusters.md) and [removal](lifecycle.md).
