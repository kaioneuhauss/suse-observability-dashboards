# Use and investigate the dashboards

## Read the resource lists

VM Performance has independent Top 5 lists for CPU use, memory use and CPU waiting time. Other action lists show up to five entries; the compact storage health and old-backup cards show up to three. **Full names and values → Table** opens the complete list, including entries outside the preview. Rankings use the end of the selected period.

Storage labels use **VM:** for a running VM matched through KubeVirt's launcher-Pod identity, **Pod:** for another measured consumer, and **PVC:** when no unambiguous active consumer was mapped. A PVC fallback is not proof that a disk is unused. The full table retains the available VM, Pod, PVC, Longhorn volume, namespace and cluster identities.

The resource guide also links to native Pod/PVC lists. Those screens have their own filters; select the same cluster/namespace, then open the resource. A panel-level metric-table link cannot reliably guess which one of several Pods you wanted to investigate.

### Select a cluster, namespace and resource

1. Open **Cluster**. Keep **Include everything** enabled to see all measured clusters. To choose one, turn it off, click the input, then click the cluster name.
2. Open **Namespace**, turn off **Include everything** and select a namespace from that cluster. Repeat for VM, Application or Volume when that filter exists.
3. If the toolbar says **None**, nothing is selected. It does not mean "all". Select a value or enable **Include everything** again. A namespace list can be empty when Cluster is None.
4. When changing clusters, reset Namespace and the following filters to **Everything**, then select values from the new cluster. A selection from the previous cluster may not exist in the new one.
5. Read the names beside the values. Long names use an ellipsis in the middle, preserving the start and end. Click **Full names and values**, select **Table** and check the time range to read complete identities and every matching resource. Cards are a shortlist, not the complete incident list; abbreviated names are not unique identifiers.

**Why does Traefik show only one namespace?** Its Namespace filter lists namespaces with discovered Kubernetes Ingress backends in the selected cluster. It does not list every namespace that exists. Another namespace appears when its Ingress is discovered; useful request charts also need traffic through that Traefik instance, service metrics and successful collection. A Pod or ClusterIP Service alone does not create an Ingress. This chart's inventory covers standard Kubernetes Ingress, not every Traefik CRD/provider. Confirm the source with:

```sh
kubectl get ingress --all-namespaces --kubeconfig /path/to/cluster.yaml --context my-cluster
```

**Which Pod uses this volume?** Storage detail cards show a Running/Pending Pod association reported by the official Agent. For KubeVirt hotplug disks, it can identify the parent `virt-launcher` Pod; the direct mount belongs to its `hp-volume` child Pod. The full table includes `pod_name`, `pvc_namespace`, `pvc`, `volume` and `k8s_cluster_name`. A shared volume can have multiple consumer rows. A `PVC:` label means no unambiguous current Pod reference was matched; check whether the VM is stopped, the claim is unused or Pod telemetry is missing. It does not prove an orphaned volume. The overview still counts unique volumes. Never delete a volume based only on this list.

### Investigate the cause

Use the native resource page for Pod health, events, logs and related resources. These dashboards complement those screens. Application traces require instrumentation and OpenTelemetry delivery; installing a dashboard does not generate traces or execute repairs.

For a VM, distinguish virtualization errors (VM/VMI state, host, `virt-launcher`, PVC and Longhorn) from failures inside the guest OS. A Windows service error or an application exception needs guest/application telemetry. The current [SUSE Virtualization integration guide](https://documentation.suse.com/external-tree/en-us/cloudnative/suse-observability/latest/en/use/suse/suse-virtualization.html) describes a native Virtualization StackPack; availability depends on the server/Agent version. It was not listed in this lab's 2.10.2 catalog. Check compatibility before updating. For application tracing on Linux VMs, see the [official OpenTelemetry guide](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/otel/getting-started/getting-started-linux.html). No guest agent, new tracing pipeline or automatic remediation is installed by this project.

### What about alerts?

The charts install **39 monitors** across all five modules. Virtualization includes VM pressure, collection failures and degraded/faulted PVC-backed Longhorn volumes. Imports includes failed/invalid records, inventory failure and optional performance collection failure. The Kubernetes, Traefik and Applications modules add their own checks.

They are starting points, not complete incident coverage. Virtualization alone does not include Kubernetes host-memory/etcd monitors. Backup age, missing backups, import duration and bandwidth need your own recovery/performance policies. Not every graph should create an alert. See [alert coverage and limits](alerts.md).

Open **Monitors** in SUSE Observability and review the `SRE ·` rules. Notification channels/routing must be configured separately in SUSE Observability. A published monitor is not proof that an email or other notification reaches someone.

