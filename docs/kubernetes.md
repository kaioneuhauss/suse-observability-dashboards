# Kubernetes / RKE2

See cluster health and application resource usage: unavailable nodes, missing replicas, filesystem pressure and containers approaching their memory limits. This module installs two dashboards, host collectors, a requests/limits inventory and 21 monitors. etcd collection is optional and off by default.

This is a community lab integration, **not recommended for production**.

## Before installing

Complete the [common setup](prerequisites.md). The official Agent must be sending node and Pod data. Host collectors need Linux nodes, host networking and read-only host mounts allowed by your cluster's admission policies.

**Already installed Virtualization on this cluster?** Add `mode: content` to the values below. Virtualization already collects the host and Pod inventory data; running both collectors would duplicate it and conflict on local ports.

## Install

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

Save as `kubernetes.yaml`:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
```

Replace the values and cluster details:

```sh
helm upgrade --install obs-kubernetes obs-dashboards/suse-observability-kubernetes \
  --version 1.2.1 --values kubernetes.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

## Check it

```sh
kubectl get pods,jobs --selector app.kubernetes.io/instance=obs-kubernetes \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
kubectl get nodes --kubeconfig /path/to/cluster.yaml --context my-cluster
```

Open **Kubernetes · Cluster Health** and **Kubernetes · Application Resource Usage**. Check node counts, inventory freshness and requests/limits for a known application. In Metrics Explorer, `up{job="sre-node",cluster_name="my-cluster"}` should be `1` for the expected nodes.

Usage, requests and limits answer different questions. High CPU alone is not proof of an incident; compare it with latency, throttling and application impact. See [validation](validation.md) and [removal](lifecycle.md).

## Optional: etcd metrics

Only enable this after your platform administrator confirms that `http://127.0.0.1:2381/metrics` is available on each etcd node. Add to your values and repeat the Helm install command:

```yaml
telemetry:
  etcd:
    enabled: true
```

The collector runs on nodes labeled `node-role.kubernetes.io/etcd=true`. It does not expose the port or change etcd. Check `up{job="sre-etcd",cluster_name="my-cluster"}` after enabling it. If Virtualization owns host collection, set this option in that release instead.

etcd panels and monitors have no samples where collection is disabled. That is not a healthy etcd result. To skip publishing all monitors for this module, set `content.monitors.enabled: false` before the first installation. Changing this flag later stops publication but does not delete monitors already in SUSE; see [lifecycle](lifecycle.md).
