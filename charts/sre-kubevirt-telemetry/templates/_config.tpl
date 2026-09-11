{{- define "kubevirt.config" -}}
extensions:
  health_check:
    endpoint: ${env:POD_IP}:13133
  bearertokenauth:
    scheme: SUSEObservability
    token: ${env:SUSE_INGEST_TOKEN}
receivers:
  prometheus:
    config:
      scrape_configs:
{{- range $component, $serverName := .Values.kubevirt.serverNames }}
        - job_name: kubevirt-metrics-{{ $component }}
          scrape_interval: {{ $.Values.scrapeInterval }}
          scrape_timeout: {{ $.Values.scrapeTimeout }}
          scheme: https
          tls_config:
            ca_file: /kubevirt-ca/ca-bundle
            server_name: {{ $serverName | quote }}
            insecure_skip_verify: false
{{- if eq $.Values.safety.cardinality.mode "enforce" }}
          sample_limit: {{ $.Values.safety.cardinality.sampleLimit }}
          label_limit: {{ $.Values.safety.cardinality.labelLimit }}
{{- end }}
          kubernetes_sd_configs:
            - role: endpointslice
              namespaces:
                names: [{{ $.Values.kubevirt.namespace | quote }}]
              selectors:
                - role: endpointslice
                  label: {{ printf "kubernetes.io/service-name=%s" $.Values.kubevirt.service | quote }}
          relabel_configs:
            - source_labels: [__meta_kubernetes_pod_label_kubevirt_io]
              regex: {{ $component | quote }}
              action: keep
            - source_labels: [__meta_kubernetes_endpointslice_port_name]
              regex: {{ $.Values.kubevirt.metricsPortName | quote }}
              action: keep
            - source_labels: [__meta_kubernetes_endpointslice_endpoint_conditions_ready]
              regex: "true"
              action: keep
            - source_labels: [__meta_kubernetes_pod_name]
              target_label: k8s_pod_name
            - source_labels: [__meta_kubernetes_namespace]
              target_label: k8s_namespace_name
            - source_labels: [__meta_kubernetes_endpointslice_endpoint_node_name]
              target_label: k8s_node_name
            - target_label: job
              replacement: kubevirt-metrics
{{- if $.Values.safety.metricAllowlist.enabled }}
          metric_relabel_configs:
            - source_labels: [__name__]
              regex: {{ $.Values.safety.metricAllowlist.regex | quote }}
              action: keep
{{- end }}
{{- end }}
{{- if .Values.selfMonitoring }}
        - job_name: sre-otel-collector
          scrape_interval: {{ .Values.scrapeInterval }}
          scrape_timeout: {{ .Values.scrapeTimeout }}
          static_configs:
            - targets: ['127.0.0.1:8888']
          metric_relabel_configs:
            - source_labels: [__name__]
              regex: 'otelcol_(exporter_(queue_size|queue_capacity|send_failed_metric_points|sent_metric_points|enqueue_failed_metric_points).*|processor_refused_metric_points.*|process_memory_rss.*)'
              action: keep
{{- end }}
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: {{ .Values.otel.memoryLimitMiB }}
    spike_limit_mib: {{ .Values.otel.spikeLimitMiB }}
  resource:
    attributes:
      - key: k8s.cluster.name
        value: {{ .Values.clusterName | quote }}
        action: upsert
  batch:
    timeout: 10s
    send_batch_size: {{ .Values.otel.batchSize }}
    send_batch_max_size: {{ .Values.otel.batchMaxSize }}
exporters:
  otlp_grpc/suse-observability:
    endpoint: {{ .Values.otlp.endpoint | quote }}
    compression: gzip
    timeout: 10s
    auth:
      authenticator: bearertokenauth
    tls:
      insecure: false
      insecure_skip_verify: false
{{- if .Values.otlp.caSecret }}
      ca_file: /otlp-ca/ca.crt
{{- end }}
    sending_queue:
      enabled: true
      sizer: requests
      queue_size: {{ .Values.otel.queueSize }}
      num_consumers: {{ .Values.otel.queueConsumers }}
      block_on_overflow: false
    retry_on_failure:
      enabled: true
      initial_interval: 5s
      max_interval: 30s
      max_elapsed_time: {{ .Values.otel.retryMaxElapsedTime }}
service:
  extensions: [health_check, bearertokenauth]
  telemetry:
    metrics:
      readers:
        - pull:
            exporter:
              prometheus:
                host: 127.0.0.1
                port: 8888
  pipelines:
    metrics:
      receivers: [prometheus]
      processors: [memory_limiter, resource, batch]
      exporters: [otlp_grpc/suse-observability]
{{- end -}}
