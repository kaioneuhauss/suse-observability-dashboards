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

The collector needs only permission to list `virtualmachineimports`; the chart supplies that RBAC. It does not read VMware credentials. It uses HTTPS remote write, so it does not need an OTLP endpoint or the Application Collection image Secret.

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
  --version 1.3.0 --values imports.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports `STATUS: deployed`. Successful publishing Jobs are removed automatically.

## 5. Check the result

```sh
kubectl get pods,jobs --selector app.kubernetes.io/instance=obs-imports \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl logs deployment/obs-imports-imports --container import-inventory --since=5m \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

**Expected result:** collector Pods are ready. The publishing Jobs may already be gone; that is normal after success.

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

## 6. Remove this module

Keep the publishing Secret available. The following command removes this release and, in the default mode, its managed dashboards and monitors:

```sh
helm uninstall obs-imports \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports the release was uninstalled. Your applications, VMs, volumes, SUSE server, official Agent and shared Secrets remain. Do not delete the namespace. A `telemetry` release only removes its collectors.

To reinstall, repeat step 4 with the same values file. If removal fails, follow [the removal guide](lifecycle.md#3-if-removal-fails) before retrying. Older versions need the [upgrade step](lifecycle.md#moving-from-120-or-121) first.
