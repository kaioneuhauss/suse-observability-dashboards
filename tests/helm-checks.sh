#!/usr/bin/env bash
# Local render/schema checks only. Does not touch a Kubernetes cluster.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v helm >/dev/null || { echo 'Instale Helm 3 para executar este teste.' >&2; exit 1; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
for values in charts/*/config/*.yaml; do
  chart="${values%/config/*}"
  name="${chart##*/}-${values##*/}"
  release="${chart##*/}"
  [[ "$release" == sre-kubevirt-telemetry ]] && release=kubevirt-otel-collector
  ns=suse-observability
  [[ "$values" == */config/observability-cluster.yaml ]] && ns=suse-observability-agent
  helm lint "$chart" --strict -f "$values"
  helm template "$release" "$chart" -n "$ns" -f "$values" > "$TMP/$name"
  test -s "$TMP/$name"
done

# Beginner profiles inherit the same complete chart defaults.
for profile in cluster harvester virtual-machines central; do
  case "$profile" in
    cluster|harvester) chart=charts/sre-platform-telemetry ;;
    virtual-machines) chart=charts/sre-kubevirt-telemetry ;;
    central) chart=charts/suse-observability-content ;;
  esac
  helm lint "$chart" --strict -f "deploy/$profile/values.yaml"
  helm template test "$chart" -f "deploy/$profile/values.yaml" > "$TMP/simple-$profile.yaml"
done
helm template test charts/sre-platform-telemetry -f deploy/cluster/values.yaml --set etcd.enabled=true --set traefik.enabled=true > "$TMP/simple-enabled.yaml"

reject() {
  if "$@" >"$TMP/negative.out" 2>&1; then
    echo "ERRO: configuracao insegura aceita: $*" >&2; exit 1
  fi
}
reject helm template t charts/sre-platform-telemetry -f charts/sre-platform-telemetry/config/harvester.yaml --set scrapeInterval=5s
reject helm template t charts/sre-platform-telemetry -f charts/sre-platform-telemetry/config/rancher-kaio.yaml --set traefik.allowMetricsNetworkPolicy=true --set traefik.existingIsolationConfirmed=false
reject helm template t charts/suse-observability-content -f charts/suse-observability-content/config/values.yaml --set lifecycle.action=delete
reject helm template t charts/suse-observability-content -f charts/suse-observability-content/config/values.yaml --set 'monitors.include[0]=nao-existe'
reject helm template t charts/sre-kubevirt-telemetry -f charts/sre-kubevirt-telemetry/config/values.yaml --set otel.batchMaxSize=1
# Verify template forms accepted in opt-in enforce, private-CA and explicit delete branches.
helm template t charts/sre-platform-telemetry -f charts/sre-platform-telemetry/config/rancher-kaio.yaml --set safety.cardinality.mode=enforce --set traefik.allowMetricsNetworkPolicy=true --set traefik.existingIsolationConfirmed=true > "$TMP/enforce.yaml"
helm template t charts/sre-kubevirt-telemetry -f charts/sre-kubevirt-telemetry/config/values.yaml --set safety.cardinality.mode=enforce --set otlp.caSecret=suse-otlp-ca > "$TMP/kubevirt-enforce.yaml"
helm template t charts/suse-observability-content -f charts/suse-observability-content/config/values.yaml --set lifecycle.action=delete --set lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS > "$TMP/delete.yaml"
echo 'HELM CHECKS OK. Ainda exige dry-run no servidor, instalacao canario e aceite de dados.'
