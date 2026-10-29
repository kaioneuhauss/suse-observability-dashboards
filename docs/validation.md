# Check the installation

Start with the Kubernetes resources, then check what the dashboards actually show. A successful Helm installation does not prove every metric is correct for your environment.

## 1. Check Pods and publishing Jobs

Example for a Traefik collector release; replace the kubeconfig, context and namespace. For other modules, use the workload names shown in their guides. For Applications or `mode: content`, only run `helm status`; these releases do not have collector workloads.

```sh
helm status obs-traefik --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability
kubectl get deployment/obs-traefik-traefik \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

**Expected result:** the release is `deployed` and collector workloads are ready. Successful publishing Jobs are removed immediately. Applications and `mode: content` have no persistent Pods after successful publication. Failed Jobs stay available for inspection for up to 24 hours by default.

If Helm reports a publishing error, read the failed Job (Imports has no monitor Job):

```sh
kubectl logs job/obs-traefik-dashboards \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
kubectl logs job/obs-traefik-monitors \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

## 2. Check recent data

Wait a few minutes for collection and ingestion. Open the module's dashboard and select the right cluster. Check the collection health panels and compare one known resource with its source: a running VM in Harvester, a request in an application or a Pod's resource settings in Kubernetes.

For deeper checks, use **Metrics Explorer** in SUSE. The module guides give the relevant metric names. Confirm the expected targets, recent samples and correct cluster name. Remote write uses `cluster_name`; KubeVirt OTLP uses `k8s_cluster_name`. Both must refer to the same integration name.

## 3. Try the filters

Try Everything, a single cluster and a single VM or application. Reset dependent filters to Everything when changing clusters. Compare the same time window and units. Long time windows have partial history after a new installation.

**No data is not zero.** It can mean no traffic, a stopped VM, missing guest statistics, a blocked collector or a metric that does not apply. Do not turn missing data into a healthy value. See [Metric definitions and limits](metric-contracts.md).

## 4. Check monitors separately

Confirm monitors are enabled, have recent data and attach to the right component. Set notification channels and rules in SUSE. Test an incident and recovery in an approved lab before relying on notifications. Publishing a monitor does not prove that an email or page is delivered.

## Common problems

| What you see | What to check |
|---|---|
| `ImagePullBackOff` | Registry access, image name and the Secret in the release namespace |
| Publishing Job returns 403 | Token permissions, expiry and ownership of the existing dashboards |
| KubeVirt `unknown authority` | Current CA, `prepare-ca`/`sync-ca` logs and access to the named CA ConfigMap |
| Longhorn timeout | Ready service endpoints and access from the collector to TCP/9500 |
| Traefik has no data | Prometheus enabled, correct Pod selector/port and NetworkPolicy |
| Application has no data | Metric names, labels, histogram buckets and actual request traffic |
| Host collector cannot start | Another collector on the same port, tolerations or host networking restrictions |
| Deleted resources come back | Helm/Fleet ownership; update the source that reconciles them |
| No publishing Job after success | Expected: Helm removes successful Jobs; check the dashboard and release status |

To inspect a failing Pod, replace its name here:

```sh
kubectl describe pod POD_NAME --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
kubectl logs POD_NAME --all-containers --since=10m \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

Recorded lab checks are in [Lab validation](lab-validation.md). Maintainers can find optional API audit tools in [Development](../dev/README.md); they are not required for installation.

## Unsaved changes after viewing a dashboard

Version 1.5.0 fixes native grid gaps and threshold ordering that could make opening a dashboard look like an edit. After updating, open **Dashboards → All** and use the current dashboard link. A tab left open before the update may point at a replaced ID or retain an older draft. Do not save that old draft over the managed definition. Preserve intentional edits in a separately owned copy.

Normal time/filter changes use the viewer URL. If a current dashboard still shows an asterisk without an intentional edit, record the dashboard, browser size and steps before saving anything. See the [tested paths and limits](lab-validation.md#150--navigation-actionable-volumes-and-alert-coverage).

## Identify a storage problem

In **Virtualization · Storage & Backups**, use **Which volumes need attention?**. The card shows the state and an abbreviated VM/Pod/PVC identity. Use **Full names and values → Table view** for complete state, cluster, volume, PVC, PVC namespace and any matched Pod. Pod association uses the official Agent; a hotplug disk can identify the parent virt-launcher Pod. A PVC-only fallback does not prove that the volume is unused. Backup review lists use the same path. Health and old-backup cards preview three entries; the no-backup list previews five. The linked query includes every match.

`pvc_namespace` identifies the application/VM namespace. It differs from the Longhorn collector's `longhorn-system` namespace. A blank PVC label means no claim identity is reported; do not infer a VM from the namespace. Compare the volume with Longhorn before remediation. See [alerts and their limits](alerts.md).
