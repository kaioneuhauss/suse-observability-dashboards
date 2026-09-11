# Install with Fleet

Fleet installs the same three Helm charts. Use Fleet **instead of** manual Helm for a given release. Complete the [same prerequisites](../prerequisites/README.md), including Secrets in the target clusters.

## 1. Prepare your Git branch

Fork/copy this repository to your organization's Git repository. Keep the charts at the paths referenced by `fleet/gitrepo-*.yaml`. Publish the branch before creating the GitRepos.

Start from the short profiles in `deploy/`, then place the edited values **inside each chart bundle**:

| Your values | Fleet file to maintain |
|---|---|
| Platform per cluster | `charts/sre-platform-telemetry/config/<cluster>.yaml` |
| Harvester VM collector | `charts/sre-kubevirt-telemetry/config/values.yaml` |
| Central content | `charts/suse-observability-content/config/values.yaml` |

Do not maintain a second manual copy once Fleet is the owner. Files in `local/` are not pushed to Git and Fleet cannot read them. Do not commit Secrets, tokens or kubeconfigs.

## 2. Match the right clusters

In `charts/sre-platform-telemetry/fleet.yaml`, keep one target customization per intended cluster. Set its namespace, selector label and profile path. Example:

```yaml
targetCustomizations:
  - name: production
    clusterSelector:
      matchLabels:
        observability.example.com/cluster: production
    defaultNamespace: suse-observability
    helm:
      valuesFiles:
        - values.yaml
        - config/production.yaml
  - name: exclude-others
    clusterSelector: {}
    doNotDeploy: true
```

Replace only this section within the existing file; preserve its Helm settings. Defaults must come first in `valuesFiles`. The selector label must match the actual Fleet Cluster object; the profile's `clusterName` must match the Agent integration. They are related by your configuration, not automatically inferred.

In the KubeVirt `fleet.yaml`, target only Harvester. In the content `fleet.yaml`, target only the central server cluster. Keep the final `doNotDeploy` fallback. Remove stale lab target customizations.

On the management cluster, inspect the Fleet objects:

```bash
kubectl get clusters.fleet.cattle.io --all-namespaces \
  --kubeconfig "$KCFG" --context "$CTX"
```

Label the intended **Fleet Cluster objects**, not Kubernetes Nodes. Replace workspace/name with the result above:

```bash
kubectl label clusters.fleet.cattle.io CLUSTER-OBJECT \
  --kubeconfig "$KCFG" --context "$CTX" -n FLEET-WORKSPACE \
  observability.example.com/enabled=true \
  observability.example.com/cluster=production --overwrite
```

## 3. Apply collectors, then content

Edit `fleet/gitrepo-*.yaml`: repository URL, branch, paths and workspace namespace. Downstream clusters usually use `fleet-default`; the management/local cluster may use `fleet-local`, with the separate management GitRepo. Inspect the actual inventory before applying.

After committing your values/selectors, with the management cluster context:

```bash
kubectl apply -f fleet/gitrepo-collectors.yaml \
  --kubeconfig "$KCFG" --context "$CTX"
# Only if monitoring the local management cluster through fleet-local:
kubectl apply -f fleet/gitrepo-management.yaml \
  --kubeconfig "$KCFG" --context "$CTX"
```

Wait for Ready bundles and verify every collector target and ingestion. Then:

```bash
kubectl apply -f fleet/gitrepo-content.yaml \
  --kubeconfig "$KCFG" --context "$CTX"
```

Confirm both publisher Jobs and the saved content in SUSE. A GitRepo with zero targets can prove repository access, but it is not a deployment test.

## 4. Operate

Edit the tracked profile and commit to update. Increment `lifecycle.revision` when you need to rerun content publication without another manifest change. Fleet reconciles Kubernetes resources; it does not continuously undo external edits in SUSE.

For a release already managed manually, plan ownership transfer. Do not enable `force` or `takeOwnership` to bypass a conflict. For removal, follow the [Fleet deletion sequence](UNINSTALL.md#fleet).

See the [official Fleet YAML reference](https://fleet.rancher.io/0.15/reference/ref-fleet-yaml) and [detailed lab example](details/DEPLOYMENT-REFERENCE.md#9-usar-os-mesmos-charts-no-fleet) when more detail is needed.
