# Prepare application metrics, with or without Virtualization

Use this page if you want the Applications dashboard and your application's HTTP metrics are not reaching SUSE yet. Skip it if you already have a working pipeline with the [required metric contract](applications.md#1-check-the-requirements).

The flow is: **instrumented application → telemetry collector → SUSE → Applications dashboard**. You do not need Harvester or the Virtualization chart. This is a community lab example, not recommended for production.

## 1. Choose the path that matches your application

| Your application | What to do |
|---|---|
| Already sends compatible HTTP metrics to SUSE | Check their names/labels and install [Applications](applications.md) |
| Has an OpenTelemetry SDK and exports OTLP | Use the separate collector below, or the version-compatible Agent gateway in section 6 |
| Exposes Prometheus/OpenMetrics at `/metrics` | Configure scraping using the [official SUSE scraping guide](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/use/metrics/k8s-otel-prometheus-scraping.html), or your existing approved collector; verify Agent version support first |
| Sends traces only, or has no instrumentation | Follow the [SUSE instrumentation guide](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/setup/otel/getting-started/getting-started-k8s.html) for your runtime and enable HTTP metrics before installing the dashboard |

Environment variables configure an existing SDK; they do not insert one into an arbitrary application. SDKs differ in metric names, histogram type and labels. A trace or a span-derived metric is not automatically the HTTP metric contract used by this project.

**Version check:** the lab's Agent chart `1.2.14` has no `otel.telemetryGateway` setting. Do not paste current Agent flags into that version and assume they work. The separate collector below is independent of the Agent, but still needs a working server OTLP endpoint and application instrumentation.

## 2. Prepare the destination and credential

**Where:** use the application's Kubernetes cluster, in this example namespace `suse-observability`. Keep the official Agent if you need Kubernetes topology. The collector does not replace it.

1. Complete the [server OTLP setup](otlp.md). Record the TLS gRPC address, for example `otlp-observability.example.com:443`.
2. In SUSE, follow the OpenTelemetry StackPack setup and obtain its ingestion Service Token. Save it in `/private/otel-token.txt` without extra whitespace or a trailing newline. This is not the publishing token.
3. Check whether the namespace exists; create it only if absent. Then create a dedicated ingestion Secret:

```sh
kubectl get namespace suse-observability --kubeconfig /path/to/cluster.yaml --context my-cluster
```

Only when the previous command reports `NotFound`:

```sh
kubectl create namespace suse-observability --kubeconfig /path/to/cluster.yaml --context my-cluster
```

```sh
kubectl create secret generic application-otel-ingestion \
  --from-file=token=/private/otel-token.txt \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

**Check:** the token is authorized for OTLP ingestion and the Secret exists in the collector namespace. Reuse an existing correct Secret instead of replacing it. Store/remove temporary credential files according to your secret policy.

## 3. Install a separate OpenTelemetry collector with Helm

This example uses the [official OpenTelemetry Collector chart](https://opentelemetry.io/docs/platforms/kubernetes/helm/collector/), pinned to chart `0.178.0` and collector `0.163.2`. Those versions are independent of the dashboard chart. It accepts OTLP inside the cluster and exports to SUSE over TLS. It does not scrape hosts or change VMs.

Save `application-otel.yaml`. Replace **`my-cluster`** and **`otlp-observability.example.com:443`**. The cluster name must match the official Agent when one is present.

```yaml
mode: deployment
fullnameOverride: application-otel
image:
  repository: otel/opentelemetry-collector-contrib
  tag: "0.163.2"
command:
  name: otelcol-contrib
presets:
  kubernetesAttributes:
    enabled: true
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
extraEnvs:
  - name: SUSE_OTEL_TOKEN
    valueFrom:
      secretKeyRef:
        name: application-otel-ingestion
        key: token
ports:
  jaeger-compact:
    enabled: false
  jaeger-thrift:
    enabled: false
  jaeger-grpc:
    enabled: false
  zipkin:
    enabled: false
config:
  receivers:
    jaeger: null
    zipkin: null
    prometheus: null
  exporters:
    debug: null
    otlp_grpc/suse:
      endpoint: otlp-observability.example.com:443
      headers:
        Authorization: "Bearer ${env:SUSE_OTEL_TOKEN}"
      tls:
        insecure: false
        insecure_skip_verify: false
  processors:
    resource/cluster:
      attributes:
        - key: k8s.cluster.name
          value: my-cluster
          action: upsert
    transform/dashboard_labels:
      metric_statements:
        - context: datapoint
          statements:
            - set(attributes["cluster_name"], resource.attributes["k8s.cluster.name"])
            - set(attributes["service_name"], resource.attributes["service.name"]) where resource.attributes["service.name"] != nil
            - set(attributes["namespace"], resource.attributes["k8s.namespace.name"]) where resource.attributes["k8s.namespace.name"] != nil
  service:
    pipelines:
      logs: null
      metrics:
        receivers: [otlp]
        processors: [memory_limiter, k8s_attributes, resource/cluster, transform/dashboard_labels, batch]
        exporters: [otlp_grpc/suse]
      traces:
        receivers: [otlp]
        processors: [memory_limiter, k8s_attributes, resource/cluster, batch]
        exporters: [otlp_grpc/suse]
```

| Setting | Why it is here |
|---|---|
| `mode`, `fullnameOverride` | Creates one Deployment and a predictable Service name: `application-otel` |
| `image`, `command` | Uses the contrib distribution containing the needed processors |
| `presets.kubernetesAttributes` | Adds Kubernetes metadata and the chart's associated read permissions |
| `resources` | Starting resource budget, to be reviewed against actual application volume |
| `extraEnvs` | Reads the token from a Secret; no token literal in the values file |
| `ports` and null receivers | Disable unused Jaeger/Zipkin inputs and the default Prometheus receiver |
| `otlp_grpc/suse` | TLS-authenticated export to the server's gRPC endpoint |
| `resource/cluster` | Adds the integration name consistently |
| `transform/dashboard_labels` | Copies resource identity into the labels expected by the dashboard; does not invent metrics or convert units |
| `pipelines` | Metrics and traces are enabled; logs are excluded. Memory protection, Kubernetes enrichment and batching precede export |

The chart keeps its default OTLP receivers on 4317/4318 and health endpoint. This is a single-replica lab example with memory-backed queues. It does not provide durable delivery or an HA design. Network policy must permit only your intended application namespaces to reach the receiver and allow the collector to reach the Kubernetes API and SUSE. Do not expose this unauthenticated internal receiver to the Internet.

For a private server CA, follow [the private CA Secret procedure](prerequisites.md#5-check-the-requirements-for-your-module), then merge these fields into the same file. Keep the other exporter settings:

```yaml
extraVolumes:
  - name: suse-ca
    secret:
      secretName: observability-ca
extraVolumeMounts:
  - name: suse-ca
    mountPath: /etc/suse-ca
    readOnly: true
config:
  exporters:
    otlp_grpc/suse:
      tls:
        ca_file: /etc/suse-ca/ca.crt
```

Install on the application cluster:

```sh
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update open-telemetry
helm upgrade --install application-otel open-telemetry/opentelemetry-collector \
  --version 0.178.0 --values application-otel.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 10m
kubectl rollout status deployment/application-otel --timeout=5m \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
kubectl get service application-otel --kubeconfig /path/to/cluster.yaml \
  --context my-cluster --namespace suse-observability
```

**Check:** the Deployment is ready and its ClusterIP Service exposes 4317 and 4318. Do not install this if another working pipeline already receives the application's data.

## 4. Point your instrumented application at the collector

In the application's own Helm values, use the chart's supported environment-variable field. If it has none and you directly own the Deployment, use `kubectl edit deployment YOUR_APPLICATION --namespace YOUR_APP_NAMESPACE --kubeconfig /path/to/cluster.yaml --context my-cluster` and merge the following into the intended container's `env` list. Keep existing settings. For Fleet/GitOps, edit its source instead.

```yaml
env:
  - name: POD_UID
    valueFrom:
      fieldRef:
        fieldPath: metadata.uid
  - name: OTEL_SERVICE_NAME
    value: my-application
  - name: OTEL_RESOURCE_ATTRIBUTES
    value: "k8s.pod.uid=$(POD_UID)"
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: http://application-otel.suse-observability.svc.cluster.local:4318
  - name: OTEL_EXPORTER_OTLP_PROTOCOL
    value: http/protobuf
  - name: OTEL_METRICS_EXPORTER
    value: otlp
  - name: OTEL_TRACES_EXPORTER
    value: otlp
  - name: OTEL_LOGS_EXPORTER
    value: none
```

`POD_UID` lets the collector identify the source Pod; `OTEL_SERVICE_NAME` is the application identity; endpoint/protocol select internal OTLP over HTTP. Preserve any existing resource attributes when adding the Pod UID. The exporter settings require a compatible SDK already loaded in the application. Updating the Pod template restarts application Pods through their normal rollout: schedule that change with the application owner.

## 5. Verify metrics before installing the dashboard

Send a few normal requests through the application, then inspect:

```sh
kubectl logs deployment/application-otel --tail=100 \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

In SUSE Metrics Explorer, find the actual HTTP request counter and duration histogram. Verify service/cluster/namespace identity, response status and normalized route. Check timestamps and duration units. The required names are in [Applications](applications.md#1-check-the-requirements).

The common OTel duration histogram can appear as `http_server_request_duration_seconds_*`; its `_count` may be your request counter. Only after confirming that, add this to `applications.yaml`:

```yaml
observability:
  url: https://observability.example.com
applicationMetrics:
  requestCounter: http_server_request_duration_seconds_count
```

If the SDK emits an exponential/native histogram, configure its supported explicit bucket view before using this dashboard's classic-histogram queries. Do not rename a millisecond metric to seconds. Names, histogram format and status labels must be checked against actual ingestion, not assumed from the SDK brand.

**Ready to proceed:** fresh HTTP metrics exist with compatible units/labels. Return to [README option E](../README.md#install-applications) to install only the dashboard/monitors. If there are only traces, stop here and fix the metric instrumentation first.

## 6. Alternative: use a newer Agent's telemetry gateway

Current [SUSE gateway documentation](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/setup/otel/telemetry-gateway.html) describes a bundled receiver. Use it only if your compatible Agent chart actually contains these settings:

```sh
helm show values suse-observability/suse-observability-agent --version AGENT_CHART_VERSION
```

Inspect the output in your editor or terminal. If supported, add to that Agent's existing values:

```yaml
otel:
  enabled: true
  telemetryGateway:
    enabled: true
```

Upgrade the existing Agent through its owner, keeping its installed compatible version, credentials and other values. Point the SDK at the actual gateway Service in the Agent namespace, then check the same metric contract as in section 5. Do not install the separate collector as well. The gateway's span-derived metrics are not automatically a replacement for this dashboard's HTTP counters/histograms.

The lab Agent `1.2.14` does not support this switch; it was not upgraded as part of this documentation work. Do not assume that an unknown Helm value will cause an error: some charts accept it and ignore it.

## 7. Remove the dashboard and optional collector

First remove the Applications **dashboard module**, keeping its publisher Secret available:

```sh
helm uninstall obs-applications --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

If the optional `application-otel` collector was installed only for this experiment, first restore the application's previous exporter settings through its owner and check its rollout. Confirm no other applications use this receiver, then remove it:

```sh
helm uninstall application-otel --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 10m
kubectl delete secret application-otel-ingestion --kubeconfig /path/to/cluster.yaml \
  --context my-cluster --namespace suse-observability
```

Remove the dedicated ingestion Secret only after confirming it has no other users. Keep shared CA Secrets, the official Agent and server OTLP endpoint. For an Agent gateway, revert only the settings you added through its owner after checking other consumers; do not uninstall the Agent.

**Validation boundary:** the new separate-collector example passed Helm rendering and the official collector `0.163.2` configuration validator. The binary's SHA-256 matched its official GitHub release asset digest. It was not deployed or tested with a newly instrumented application during this documentation update. The previous application dashboard validation used the lab's existing telemetry. A real rollout must complete sections 4 and 5 before it is accepted.
