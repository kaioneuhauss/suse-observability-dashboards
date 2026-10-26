# Traefik

Use this module to see incoming traffic, HTTP errors, slow requests and certificate expiry. It installs one dashboard, six monitors and Traefik collectors. It does not install or replace Traefik.

This is a community lab integration, **not recommended for production**.

<a id="before-installing"></a>

## 1. Check the requirements

Complete the [common setup](prerequisites.md). Prometheus metrics must be enabled on your existing Traefik. For RKE2, first check who manages it:

```sh
kubectl get helmchart,helmchartconfig --namespace kube-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get pods --namespace kube-system --selector app.kubernetes.io/name=rke2-traefik --show-labels \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

For a locally managed RKE2 installation, merge the following values into `spec.valuesContent` of its `rke2-traefik` HelmChartConfig. Preserve the existing values. If the resource already exists, open it with:

```sh
kubectl edit helmchartconfig rke2-traefik --namespace kube-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

If no HelmChartConfig exists and RKE2 is the owner, save this as `traefik-metrics.yaml`:

```yaml
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: rke2-traefik
  namespace: kube-system
spec:
  valuesContent: |-
    metrics:
      prometheus:
        entryPoint: metrics
        addEntryPointsLabels: true
        addServicesLabels: true
    ports:
      metrics:
        port: 9100
        expose:
          default: false
```

```sh
kubectl apply --filename traefik-metrics.yaml \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

Rancher-provisioned clusters may instead manage these values under `spec.rkeConfig.chartValues.rke2-traefik`. Fleet-managed values must be changed at their Git source. Do not overwrite a configuration owned by another controller. For a standalone Helm Traefik release, merge the same `metrics` and `ports` blocks into its saved values and upgrade that release using its installed chart version.

This change can restart Traefik. Check your applications' HTTP/HTTPS access after it completes. Metrics stay internal on port 9100. See [RKE2 Helm configuration](https://docs.rke2.io/helm/) and [Traefik metrics](https://doc.traefik.io/traefik/observability/metrics/prometheus/).

## 2. Add the repository

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

**Expected result:** Helm confirms the repository is available.

## 3. Fill in your settings

Save as `traefik.yaml`, using your integration name and SUSE URL:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
```

The defaults find `app.kubernetes.io/name=rke2-traefik` in `kube-system`, on port 9100. For another Traefik installation, add its actual namespace and labels:

```yaml
telemetry:
  traefik:
    namespace: traefik
    selector:
      app.kubernetes.io/name: traefik
    port: 9100
    targetPort: metrics
```

## 4. Install the module

This command installs the module and waits for it to finish. Keep the values file for updates and reinstalls.

```sh
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.3.0 --values traefik.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports `STATUS: deployed`. Successful publishing Jobs are removed automatically.

## 5. Check the result

```sh
kubectl get pods,jobs --selector app.kubernetes.io/instance=obs-traefik \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

**Expected result:** collector Pods are ready. The publishing Jobs may already be gone; that is normal after success.

Open **Traefik · Incoming Traffic & Errors** and choose your cluster. Visit a known application and check that its traffic increases. In Metrics Explorer, check `up{job="traefik",cluster_name="my-cluster"}`: every expected replica should report `1`.

Open connections count concurrent connections, not completed requests. Latency percentiles are estimates. Application and Traefik totals can differ because they measure different points in the request path. Monitor topology mapping was validated with the RKE2 DaemonSet; check it before relying on alerts for a different Traefik deployment.

## Optional: existing NetworkPolicies

If Traefik Pods are already isolated, the chart can add a collector-only metrics rule:

```yaml
telemetry:
  traefik:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

Merge this with any other `telemetry.traefik` settings in the same YAML block. Do not create a first isolation policy without reviewing access to web/websecure. See [validation](validation.md) and [removal](lifecycle.md).

## 6. Remove this module

Keep the publishing Secret available. The following command removes this release and, in the default mode, its managed dashboards and monitors:

```sh
helm uninstall obs-traefik \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports the release was uninstalled. Your applications, VMs, volumes, SUSE server, official Agent and shared Secrets remain. Do not delete the namespace. A `telemetry` release only removes its collectors.

To reinstall, repeat step 4 with the same values file. If removal fails, follow [the removal guide](lifecycle.md#3-if-removal-fails) before retrying. Older versions need the [upgrade step](lifecycle.md#moving-from-120-or-121) first.
