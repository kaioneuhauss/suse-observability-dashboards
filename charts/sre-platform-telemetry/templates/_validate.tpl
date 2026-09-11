{{- define "sre.validate" -}}
{{- $v := .Values -}}
{{- if or (not (regexMatch "^[1-9][0-9]*s$" $v.scrapeInterval)) (not (regexMatch "^[1-9][0-9]*s$" $v.scrapeTimeout)) -}}
{{- fail "Use scrapeInterval/scrapeTimeout em segundos inteiros, ex.: 30s e 10s" -}}
{{- end -}}
{{- $interval := int (trimSuffix "s" $v.scrapeInterval) -}}
{{- $timeout := int (trimSuffix "s" $v.scrapeTimeout) -}}
{{- if and (eq $v.safety.profile "conservative") (lt $interval 30) -}}{{ fail "Perfil conservative exige scrapeInterval >= 30s" }}{{- end -}}
{{- if gt $timeout $interval -}}{{ fail "scrapeTimeout deve ser <= scrapeInterval" }}{{- end -}}
{{- if and $v.traefik.allowMetricsNetworkPolicy (not $v.traefik.existingIsolationConfirmed) -}}
{{- fail "Confirme isolamento existente com traefik.existingIsolationConfirmed=true antes de criar NetworkPolicy" -}}
{{- end -}}
{{- if or (eq (int $v.vmagent.nodePort) (int $v.vmagent.etcdPort)) (eq (int $v.nodeExporter.port) (int $v.vmagent.nodePort)) (eq (int $v.nodeExporter.port) (int $v.vmagent.etcdPort)) -}}
{{- fail "As portas locais do node-exporter e dos dois vmagent devem ser diferentes" -}}
{{- end -}}
{{- end -}}
