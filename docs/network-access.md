# Check network access before installation

Do this on the monitored cluster: SUSE Virtualization (Harvester) for the Virtualization or Imports module, or the relevant Kubernetes cluster for other collectors. You do not need to create a NetworkPolicy when traffic is already allowed. Keep existing platform policies in place.

## 1. Check the paths your module uses

| From | To | Required for |
|---|---|---|
| Collectors and publishing Jobs | Cluster DNS, UDP/TCP 53 | Name resolution |
| Collectors and publishing Jobs | Kubernetes API, usually TCP 443 | Discovery, inventory and public CA reads |
| Collectors | SUSE Observability HTTPS receiver, TCP 443 | Agent and Prometheus remote write |
| Virtualization collector | SUSE Observability OTLP hostname, TCP 443 with TLS/gRPC | VM and Longhorn metrics |
| Virtualization collector | KubeVirt metrics endpoints discovered through `kubevirt-prometheus-metrics` | VM metrics; inspect EndpointSlices for the actual target ports |
| Virtualization collector | Longhorn managers, TCP 9500 | Storage metrics; this port also serves the Longhorn API |
| Imports collector, when performance is enabled | Node kubelets, TCP 10250 with TLS | Importer and image-service CPU, memory and network metrics |
| Traefik collector | Traefik metrics Pods, TCP 9100 by default | Requests, errors and duration |
| Host collector | Local node exporter and optional local etcd metrics | Node metrics; etcd defaults to `127.0.0.1:2381` |
| Publishing Jobs | SUSE Observability API and `dl.stackstate.com`, HTTPS | Publish content and obtain the checksum-verified CLI |
| Cluster nodes | Chart image registries, HTTPS | Pull container images |

Use your actual ports and destinations. A firewall, egress policy or CNI-specific policy can block a path even when Kubernetes NetworkPolicies look correct. Registry pulls originate from nodes; do not assume a Pod egress rule controls them.

## 2. Check existing isolation

```sh
kubectl get networkpolicy --all-namespaces \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get networkpolicy --namespace longhorn-system -o yaml \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get endpointslice --namespace harvester-system \
  -l kubernetes.io/service-name=kubevirt-prometheus-metrics \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

**Check:** identify whether an Ingress policy selects Pods with `app: longhorn-manager`. A policy elsewhere in the namespace does not necessarily isolate those Pods. NetworkPolicies add their allowances together; both source egress and destination ingress must permit a connection when both are isolated. See [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

## 3. Allow this collector through existing Longhorn isolation

Only after confirming that Longhorn managers are already isolated, add this to `virtualization.yaml`:

```yaml
virtualization:
  longhorn:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

**What happens:** installing the Virtualization chart creates `obs-virtualization-longhorn-metrics` in `longhorn-system`. It allows TCP/9500 from the release's collector Pod labels **and** its namespace together. You do not create a separate policy YAML. Uninstalling this release removes only that policy, leaving the platform policies in place.

If managers are not isolated, leave both options at their defaults (`false`). Adding the first ingress policy changes their default access and can break platform traffic. The chart deliberately requires confirmation instead of making this decision automatically.

After installation, inspect the generated rule:

```sh
kubectl get networkpolicy obs-virtualization-longhorn-metrics \
  --namespace longhorn-system -o yaml \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

**Check:** the rule contains the correct namespace, the `obs-virtualization` Pod selector and TCP/9500 only. This rule does not remove access granted by other policies. Confirm fresh `up=1` collection in SUSE Observability as well; a policy object is not a connectivity test.

## 4. Traefik and other restrictions

If existing ingress policies isolate Traefik metrics, the equivalent settings in `traefik.yaml` are:

```yaml
telemetry:
  traefik:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

The namespace and workload selector must match Traefik. See [Traefik setup](traefik.md). For restricted egress or nonstandard CNI policies, ask the network owner to allow only the paths in step 1 for the selected module. Do not use an allow-all rule as a shortcut.

Return to [prerequisites](prerequisites.md#6-check-the-module-specific-prerequisites) or [install your module](../README.md#3-install-your-first-module).
