{{- define "content.metricAliases" -}}
{{- $text := .text -}}
{{- with .values.applicationMetrics -}}
{{- $text = $text | replace "http_server_requests_total" .requestCounter | replace "http_server_request_duration_seconds" .durationHistogram | replace "http_response_status_code" .statusLabel | replace "cluster_name" .clusterLabel | replace "service_name" .serviceLabel | replace "http_route" .routeLabel -}}
{{- end -}}
{{- $text -}}
{{- end -}}
