# Remove this integration package

Choose the path that owns the release: manual Helm or Fleet. Keep the publisher token valid until external SUSE content has been deleted. Back up dashboard changes you want to preserve.

## Manual Helm

### 1. Delete the project's SUSE content

Set `KCFG`, `CTX` to the central cluster and `CONTENT_NS` to its publisher namespace. Use your saved central values. Enable both dashboards and monitors, and include all project items you intend to remove. A previous subset will delete only that subset.

```bash
helm upgrade suse-observability-content \
  ./charts/suse-observability-content \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$CONTENT_NS" \
  -f local/central/values.yaml \
  --set lifecycle.action=delete \
  --set lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS \
  --wait --timeout 15m
kubectl logs job/suse-observability-content-dashboards \
  --kubeconfig "$KCFG" --context "$CTX" -n "$CONTENT_NS"
kubectl logs job/suse-observability-content-monitors \
  --kubeconfig "$KCFG" --context "$CTX" -n "$CONTENT_NS"
```

Continue only after both Jobs succeed and the selected objects are absent in SUSE. If the release was already uninstalled, reinstall it with the original credentials/selection and explicit delete action to perform this step.

### 2. Remove the chart releases

In the central cluster:

```bash
helm uninstall suse-observability-content \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$CONTENT_NS"
```

In each monitored cluster, after changing the target variables:

```bash
helm uninstall sre-platform-telemetry \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$AGENT_NS"
```

On Harvester only:

```bash
helm uninstall kubevirt-otel-collector \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$AGENT_NS"
```

Completed publisher hooks expire after 24 hours. For immediate cleanup, after verified deletion, remove only the two project Jobs in the central namespace:

```bash
kubectl delete jobs suse-observability-content-dashboards suse-observability-content-monitors \
  --kubeconfig "$KCFG" --context "$CTX" -n "$CONTENT_NS" --ignore-not-found
```

### 3. Optional project-only cleanup

Remove the publisher Secret and revoke its token if no other automation uses them. Remove the copied `kubevirt-metrics-ca` ConfigMap if no other collector uses it. Retain shared registry/intake Secrets, the official Agent, namespaces and the SUSE server.

Traefik metrics and the central OTLP endpoint were configured through their original owner. Revert only the changes exclusively introduced for this project, using that same owner and a reviewed baseline. Do not disable endpoints still used by other monitoring tools.

## Fleet

1. Keep the content bundle targeted to its cluster. In its tracked values, set `lifecycle.action: delete`, `lifecycle.confirmDelete: DELETE_MANAGED_OBJECTS`, enable both sections and include the intended objects. Commit/push and wait for Fleet and both Jobs to succeed. Confirm SUSE deletion.
2. Then remove the project's GitRepo/bundle paths through Fleet and wait for its release cleanup. Do not run manual `helm uninstall` while Fleet still reconciles the release. Check whether your Fleet policy keeps resources on deletion.
3. Verify that the project's collector workloads, releases and hooks are removed. Perform the optional Secret/CA/token cleanup above.

Do not remove a shared GitRepo that manages unrelated bundles. Native SUSE monitors, the server, official Agents and other applications are outside this package's removal scope.
