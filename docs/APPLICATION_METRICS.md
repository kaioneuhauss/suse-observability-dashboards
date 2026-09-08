# Application metrics and HTTP error investigation

[Back to README](../README.md)

The Traefik dashboard measures the ingress layer without application instrumentation. The Instrumented apps dashboard measures inside the application and expects the metric contract below. Installing these charts does not modify application code or automatically translate arbitrary OpenTelemetry metric names.

## Expected metric contract

| Metric | Type and labels used by the dashboards |
| --- | --- |
| `http_server_requests_total` | Counter; `cluster_name`, `service_name`, `http_route`, `status_class`; error detail also uses `http_request_method` and `http_response_status_code` |
| `http_server_request_duration_seconds_bucket` | Classic histogram buckets; `le` and the application/service labels used by the query |
| `http_server_request_duration_seconds_sum` / `_count` | Duration sum and completed request count for averages where queried |
| `http_server_active_requests` | Gauge used to discover an instrumented service before completed traffic exists |

Inspect the actual [application dashboard queries](../charts/suse-observability-dashboards/dashboards/01-application-sre-overview.yaml) before adapting your instrumentation. Names and label conventions differ between SDKs and frameworks. Export durations in seconds for this contract; the dashboard converts them to milliseconds for display.

Use normalized routes such as `/orders/{id}` rather than one metric label per concrete request URL. Do not add user IDs, request IDs, tokens or payloads to metric labels. They belong, where appropriate, in governed logs/traces rather than high-cardinality time series.

## Compare a load test correctly

1. Start collection and verify at least two samples before the test.
2. Record before/after counters for the same application, route and status codes.
3. Run a bounded test against an application you are authorized to test. Record request count, duration, codes and client latency.
4. Wait for scrape and ingestion, then compare counter deltas and duration sum/count deltas.
5. Use the same window when interpreting charts. Do not compare a three-second generator average directly with the dashboard's five-minute rate.

Client duration includes the connection to the server; proxy and application measurements start and finish at different points. Histogram percentiles are estimates based on bucket boundaries. A recent rate based on a 30-second scrape cannot reconstruct an exact one-second peak.

## Enable optional Traefik access logs

Metrics show which service returned a code and when the error rate increased. They cannot contain the exact timestamp, exception and payload of every request. Access logs add per-request context; application logs and traces are needed for the underlying cause.

Merge [access-logs-values.yaml](../integrations/traefik-agent-v2/access-logs-values.yaml) into the **same persistent Traefik configuration** described in [Prerequisites](PREREQUISITES.md#3-traefik-metrics-in-rancher-managed-rke2). For a Rancher-provisioned cluster, merge its `logs` block under `spec.rkeConfig.chartValues.rke2-traefik`. For directly managed RKE2, merge it into the existing HelmChartConfig's `spec.valuesContent`.

```yaml
logs:
  access:
    enabled: true
    format: json
    fields:
      general:
        defaultmode: drop
        names:
          StartUTC: keep
          RequestMethod: keep
          RequestPath: keep
          RequestHost: keep
          DownstreamStatus: keep
          ServiceName: keep
          RouterName: keep
          Duration: keep
          OriginStatus: keep
          OriginDuration: keep
          RetryAttempts: keep
      headers:
        defaultmode: drop
```

The supplied fragment also includes `ClientHost`; omit it if client addresses are not required. Review path/client retention and access policies. Headers are omitted by default. This repository does not activate access logs or a full logs/traces pipeline merely by installing the dashboard chart.

After reconciliation, inspect recent Traefik logs:

```bash
kubectl logs --kubeconfig "$SRE_CLUSTER_KCFG" --context "$SRE_CLUSTER_CTX" \
  --namespace kube-system --selector app.kubernetes.io/name=rke2-traefik \
  --all-containers --prefix --since=10m --max-log-requests=20
```

Verify that the official logs pipeline actually ingests these events before relying on centralized search. Correlate `StartUTC`, method, path, service and status with application logs. `DownstreamStatus` is the response sent to the caller; `OriginStatus` helps distinguish an upstream application response from a proxy-generated error. An HTTP 400 or 500 alone does not establish its cause.

For cross-service investigation, propagate trace context and instrument the application using the supported SUSE/OpenTelemetry workflow. New logging cannot recover requests that were never recorded.

Reference: [Traefik access logs](https://doc.traefik.io/traefik/reference/install-configuration/observability/logs-and-accesslogs/).
