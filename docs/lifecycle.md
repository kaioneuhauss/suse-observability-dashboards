# Update, remove and reinstall

All steps use Helm and kubectl. The examples use Virtualization. For another module, replace `virtualization` in the chart, release, values file and Job names. Use the kubeconfig, context and namespace where that release is installed.

## Check what is installed

```sh
helm list --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability
helm get values obs-virtualization -o yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability
```

The `CHART` column includes the installed version. Keep that version available for removal. For example, `suse-observability-virtualization-1.2.1` means use `--version 1.2.1`.

## Update

Keep your release name, namespace, existing publisher identity and saved values. Read the changelog, update the repository, then apply the new version:

```sh
helm repo update obs-dashboards
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.2.1 --values virtualization.yaml \
  --set lifecycle.action=apply --set-string lifecycle.confirmDelete= \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

Use your complete saved values file, including any custom Secret names, collection options and `mode`. If you no longer have it, save the output of `helm get values` to a private file before updating. Do not replace a central `content` release with the README's default `all` example.

Unchanged dashboards keep their IDs. Changed dashboards use the default `replace` strategy, which can change links and overwrite manual edits. Export any edits you need from the SUSE UI before updating. A 403 means the token's access or ownership needs fixing; the publisher does not create a duplicate to bypass it.

## Remove

There are two parts: content stored in SUSE and resources stored in Kubernetes. `helm uninstall` alone removes Kubernetes resources, but leaves the dashboards and monitors in SUSE.

If you want a backup, save the installed settings and manifests first. Keep these files private:

```sh
helm get values obs-virtualization -o yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability > virtualization-backup.yaml
helm get manifest obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability > virtualization-manifest.yaml
```

These files do not include manual edits made in the SUSE UI. Export those separately if needed.

### 1. Delete the module's dashboards and monitors

Skip this step for `mode: telemetry`. For `all` or `content`, keep the publishing token available and run this with the **installed chart version**:

```sh
helm upgrade obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.2.1 --reuse-values \
  --set lifecycle.action=delete --set lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

Wait for success. If it fails, **stop here**, check the publishing Job logs and fix the error before retrying. The chart only deletes the names and identifiers belonging to this module.

### 2. Remove the release and its Jobs

```sh
helm uninstall obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 10m
kubectl delete job obs-virtualization-dashboards obs-virtualization-monitors --ignore-not-found \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

The last command removes retained Helm hook Jobs. Imports has no monitor Job, so `--ignore-not-found` handles that case. Collector-only releases just need `helm uninstall`.

Check the result:

```sh
helm list --kubeconfig /path/to/harvester.yaml --kube-context harvester --namespace suse-observability
kubectl get pods,jobs --selector app.kubernetes.io/instance=obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

Confirm the module's dashboards are gone in SUSE. The SUSE server, retained metrics, official Agents, applications, VMs, volumes and shared Secrets are preserved. Do not delete the namespace. Delete or revoke a Secret only after confirming that no other module or application uses it.

With multiple clusters, uninstall collectors in each source cluster and delete content once at its publisher. Do not delete the publisher token first.

## Reinstall

Run the module's install command with your saved values. When restoring from a backup taken during deletion, explicitly pass `--set lifecycle.action=apply --set-string lifecycle.confirmDelete=` as in the update example. Then follow [Check the installation](validation.md).

The charts restore definitions from the repository; dashboard IDs may change. Removing and reinstalling a module does not clear SUSE's historical metrics.

## Older versions and the previous combined package

Version 1.2.0 packages are also available in the Helm repository for removal of that version. For earlier releases, use the matching chart from the repository's Git history; do not use a new catalog to delete old content with different names.

The combined package is preserved at Git revision `c059f58`. Before migrating it, record its exact releases and ownership, export dashboards/monitors and back up Helm values/manifests. Delete its external content using that version's `lifecycle.action=delete` and confirmation setting, then uninstall only its identified releases. Do not remove resources by wildcard.

If Helm/Fleet manages a resource from another source, change that source first. Otherwise it can recreate what you delete. Preserve the native SUSE dashboard and all platform workloads.

## Disable monitors before a first install

`content.monitors.enabled: false` skips monitor publication. It does not delete previously published monitors. To remove existing monitors but keep dashboards, first run the deletion step with `--set content.dashboards.enabled=false --set content.monitors.enabled=true`. After success, run the update command with your normal values, `lifecycle.action=apply`, dashboards enabled and monitors disabled. Confirm the outcome in SUSE. Never uninstall the release while you intend to retain its collectors.
