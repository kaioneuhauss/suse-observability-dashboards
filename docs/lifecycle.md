# Update, remove and reinstall

These steps use **Helm and kubectl only**. They work with the same values file you used to install. The examples use Virtualization; for another module, replace `virtualization` in the release, chart and file names. Always use that release's kubeconfig, context and namespace.

## 1. Save your settings

Before changing an existing installation, check its version and save its settings to a private file:

```sh
helm list --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability
helm get values obs-virtualization -o yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability > virtualization-backup.yaml
helm get manifest obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability > virtualization-manifest.yaml
```

**Expected result:** the release is listed and the two files contain its values and Kubernetes definitions. Keep them outside Git. Export manual dashboard edits from SUSE separately; Helm's backup does not include them.

## 2. Remove the module

For chart **1.3.0**, run:

```sh
helm uninstall obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

Helm first runs cleanup Jobs for this module's dashboards and monitors. After they succeed, it removes the release's collectors, definitions and RBAC. Successful Jobs are removed too. Keep the publishing Secret and network access to SUSE available until this finishes. A `telemetry` release has no external content to delete.

**Expected result:** Helm reports the release was uninstalled. Check:

```sh
helm list --all --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability
kubectl get pods,jobs,configmaps,services,serviceaccounts --selector app.kubernetes.io/instance=obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

The release is absent and its resources are gone. Open SUSE and confirm the module's dashboards disappeared. Other modules, applications, VMs, volumes, the SUSE server and its historical metrics, official Agents and shared Secrets stay in place. **Do not delete the namespace.**

With multiple clusters, repeat removal for each source collector and then the central publisher. See [Multiple clusters](multiple-clusters.md#3-remove-a-module-from-multiple-clusters).

## 3. If removal fails

Stop and inspect the failed cleanup Job. For example:

```sh
kubectl get jobs --selector app.kubernetes.io/instance=obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl logs job/obs-virtualization-dashboards-delete \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl logs job/obs-virtualization-monitors-delete \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

Only read logs for Jobs that exist. Fix the reported token, permission, ownership, image or connection error, then repeat `helm uninstall`. Do not bypass the hooks with `--no-hooks`: that can leave external dashboards and monitors behind.

A failed cleanup stops Helm before it deletes the release's Kubernetes resources. External cleanup is **not transactional**: some dashboards may already have been deleted before an error. A retry checks what remains. Failed Jobs stay for up to 24 hours by default. This behavior uses [Helm pre-delete hooks](https://helm.sh/docs/topics/charts_hooks/).

## 4. Install again

Use the same module guide and saved values. For the backup from step 1:

```sh
helm repo update obs-dashboards
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.3.0 --values virtualization-backup.yaml \
  --set lifecycle.action=apply --set-string lifecycle.confirmDelete= \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports `deployed`, collectors become ready and dashboards return. Dashboard IDs can change after reinstalling. Historical metrics remain in SUSE. Follow [Check the installation](validation.md) to confirm fresh samples.

## Update without removing

Use step 4 while the release is installed. Keep its release name, namespace, `mode`, full values and publishing identity. Read the changelog first. Unchanged dashboards keep their IDs; changed dashboards use the default `replace` strategy, which can overwrite manual edits and change links.

## Moving from 1.2.0 or 1.2.1

These versions do not clean up external content during `helm uninstall`. Before using the shorter removal command, save their values with step 1 and run the upgrade in step 4. The 1.3.0 dashboard and monitor catalog is unchanged from 1.2.0/1.2.1. This upgrade adds the cleanup hooks while keeping the existing owner and module selection. **Only continue to step 2 after the upgrade succeeds.**

If an old completed publishing Job remains, remove only its exact name after the release is gone:

```sh
kubectl delete job obs-virtualization-dashboards obs-virtualization-monitors --ignore-not-found \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

For older catalogs or the combined package at Git revision `c059f58`, use that version's `lifecycle.action=delete` with `lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS` before uninstalling its identified release. Do not use a new catalog to delete old content with different names, or remove resources by wildcard. Change any Fleet/GitOps owner at its source first.

## Optional: keep dashboards when uninstalling

Add `lifecycle.deleteOnUninstall: false` in YAML form to your values and upgrade successfully before uninstalling:

```yaml
lifecycle:
  deleteOnUninstall: false
```

This deliberately keeps the managed dashboards and monitors in SUSE. It is not the default cleanup procedure. Plan-only (`lifecycle.action: plan`) releases also have no deletion hooks.

## Optional: disable monitors

Before the first installation, `content.monitors.enabled: false` skips monitors. Changing this later does not delete already published monitors, and disabled content is not targeted by uninstall hooks.

To remove existing monitors while keeping dashboards and collectors, first run an explicit deletion upgrade with the installed version and existing values, adding `--set lifecycle.action=delete --set lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS --set content.dashboards.enabled=false --set content.monitors.enabled=true`. After success, upgrade again with your normal values, `lifecycle.action=apply`, dashboards enabled and monitors disabled. Confirm the result in SUSE. This is an advanced selective operation, not part of the normal installation or removal.
