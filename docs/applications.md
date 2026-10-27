# Applications

See request volume, errors and response times from inside your applications. This chart publishes one dashboard and two monitors. It does not install a collector or instrument your code. The application metrics must already be arriving in SUSE Observability.

This is a community lab integration, **not recommended for production**.

<a id="before-installing"></a>

## 1. Check the requirements

You need the [publishing Secret](prerequisites.md#4-create-the-publishing-secret) and these metrics in Metrics Explorer:

| Signal | Expected name or labels |
|---|---|
| Completed requests | `http_server_requests_total` |
| Duration histogram, in seconds | `http_server_request_duration_seconds_bucket`, `_sum`, `_count` |
| Active requests, optional | `http_server_active_requests` |
| Application identity | `cluster_name`, `service_name`, `namespace` |
| Route and HTTP result | `http_route`, `http_response_status_code` |

Use normalized routes such as `/orders/{id}`, not individual IDs or user names. Traces alone do not guarantee these metrics exist. A histogram without buckets cannot provide p95/p99. For instrumentation, follow the [SUSE OpenTelemetry guide](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/setup/otel/getting-started/getting-started-k8s.html).

## 2. Add the repository

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

**Expected result:** Helm confirms the repository is available.

## 3. Fill in your settings

Save as `applications.yaml`:

```yaml
observability:
  url: https://observability.example.com
```

Use a cluster and namespace containing the publishing Secret. No ingestion Secret or `clusterName` is needed for this chart:

## 4. Install the module

This command installs the module and waits for it to finish. Keep the values file for updates and reinstalls.

```sh
helm upgrade --install obs-applications obs-dashboards/suse-observability-applications \
  --version 1.4.0 --values applications.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports `STATUS: deployed`. Successful publishing Jobs are removed automatically.

## 5. Check the result

```sh
helm status obs-applications \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability
```

**Expected result:** the release is deployed. This module has no collector Pods.

Open **Applications · Traffic, Errors & Speed**. Select a known application and compare requests, status codes and duration with its own measurements. **No data** can mean missing instrumentation or no traffic; it is not 100% availability.

Request availability is the share of completed requests without a 5xx response. It is not uptime. Error budget usage compares the 5-minute and 1-hour rates with `slo.availabilityTarget`, which defaults to `99.9`. It does not prove a 30-day SLO. Health, ready, live and metrics routes are excluded by the queries; check whether this fits your route names.

## Optional: different metric names

If your application uses the histogram count as its request counter and OTel cluster labels, add these settings after checking the real metric names:

```yaml
applicationMetrics:
  requestCounter: http_server_request_duration_seconds_count
  clusterLabel: k8s_cluster_name
```

You can also set `durationHistogram`, `serviceLabel`, `statusLabel` and `routeLabel`. The chart applies them to filters, panels and monitors. Keep `namespace` normalized to the Kubernetes namespace in the ingestion pipeline. One dashboard definition uses one metric contract; it does not automatically combine incompatible schemas.

The lab used the default contract. Validate custom names against actual application data. See [metric limits](metric-contracts.md), [validation](validation.md) and [removal](lifecycle.md).

## 6. Remove this module

Keep the publishing Secret available. The following command removes this release and, in the default mode, its managed dashboards and monitors:

```sh
helm uninstall obs-applications \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports the release was uninstalled. Your applications, VMs, volumes, SUSE server, official Agent and shared Secrets remain. Do not delete the namespace. A `telemetry` release only removes its collectors.

To reinstall, repeat step 4 with the same values file. If removal fails, follow [the removal guide](lifecycle.md#3-if-removal-fails) before retrying. Older versions need the [upgrade step](lifecycle.md#moving-from-120-or-121) first.
