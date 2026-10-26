#!/usr/bin/env bash
# User-facing lifecycle helper. Every cluster command has an explicit destination.
set -euo pipefail
umask 077
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
fail() { echo "ERRO: $*" >&2; exit 1; }
usage() {
  cat <<'EOF'
Uso: bash scripts/pack.sh <configure|check|install|status|remove> <modulo> [arquivo.yaml] [modo]
Modulos: virtualization, imports, traefik, applications, kubernetes
Defina KCFG (kubeconfig), CTX (contexto) e NS (namespace existente).
configure: defina tambem OBS_URL; Virtualization requer OTLP_ENDPOINT.
Exemplo: bash scripts/pack.sh configure traefik local/traefik.yaml telemetry
remove: faz backup e remove SOMENTE a release obs-<modulo> e seu conteudo gerenciado.
EOF
}
[[ $# -ge 2 ]] || { usage; exit 1; }
action=$1; module=$2
case "$action" in configure|check|install|status|remove) ;; *) usage; exit 1;; esac
case "$module" in virtualization|imports|traefik|applications|kubernetes) ;; *) fail "Modulo desconhecido: $module";; esac
: "${KCFG:?Defina KCFG com o caminho do kubeconfig}"
: "${CTX:?Defina CTX com o contexto exato}"
: "${NS:?Defina NS com um namespace existente}"
[[ -f "$KCFG" ]] || fail "Kubeconfig nao encontrado: $KCFG"
for tool in kubectl helm; do command -v "$tool" >/dev/null || fail "Instale $tool primeiro (docs/prerequisites.md)"; done
release="obs-$module"
chart="${PACK_CHARTS_DIR:-$ROOT/charts}/suse-observability-$module"
values=${3:-"$ROOT/local/$module.yaml"}
k=(--kubeconfig "$KCFG" --context "$CTX" --namespace "$NS" --request-timeout=30s)
h=(--kubeconfig "$KCFG" --kube-context "$CTX" --namespace "$NS")
echo "Destino: contexto=$CTX namespace=$NS release=$release"
kubectl get namespace "$NS" "${k[@]}" -o name >/dev/null

if [[ "$action" == configure ]]; then
  mode=${4:-all}; [[ "$module" != applications ]] || mode=content
  case "$mode" in all|telemetry|content) ;; *) fail 'Modo deve ser all, telemetry ou content';; esac
  : "${OBS_URL:?Defina OBS_URL, por exemplo https://observability.exemplo.com.br}"
  [[ "$OBS_URL" =~ ^https://[a-zA-Z0-9.-]+(:[0-9]+)?/?$ ]] || fail 'OBS_URL deve ser a URL HTTPS base, sem credenciais, query ou caminho'
  [[ ! -e "$values" ]] || fail "Arquivo ja existe: $values. Edite-o ou escolha outro nome; nao foi sobrescrito."
  cluster=''
  if [[ "$mode" != content ]]; then
    cluster=$(kubectl get configmap suse-observability-agent-cluster-name "${k[@]}" -o jsonpath='{.data.STS_CLUSTER_NAME}')
    [[ "$cluster" =~ ^[a-zA-Z0-9_.-]+$ ]] || fail 'Nao foi possivel ler um nome de integracao simples. Copie examples/<modulo>.yaml e preencha clusterName manualmente.'
  fi
  if [[ "$module" == virtualization && "$mode" != content ]]; then
    : "${OTLP_ENDPOINT:?Defina OTLP_ENDPOINT com host:porta, sem https:// (docs/virtualization.md)}"
    [[ "$OTLP_ENDPOINT" =~ ^[a-zA-Z0-9.-]+:[0-9]+$ ]] || fail 'OTLP_ENDPOINT deve ser host:porta'
  fi
  mkdir -p "$(dirname "$values")"
  {
    printf 'mode: %s\n' "$mode"
    [[ -z "$cluster" ]] || printf 'clusterName: "%s"\n' "$cluster"
    printf 'observability:\n  url: "%s"\n' "${OBS_URL%/}"
    if [[ "$module" == virtualization && "$mode" != content ]]; then printf '  otlpEndpoint: "%s"\n' "$OTLP_ENDPOINT"; fi
  } > "$values"
  echo "Criado: $values. Confira os Secrets e os pre-requisitos especificos antes de instalar."
  exit 0
fi

if [[ "$action" == check || "$action" == install ]]; then
  [[ -f "$values" ]] || fail "Arquivo nao encontrado: $values. Execute configure ou copie examples/$module.yaml."
  helm lint "$chart" --strict --values "$values"
  temp=$(mktemp -d); trap 'rm -rf "$temp"' EXIT
  helm template "$release" "$chart" "${h[@]}" --values "$values" --no-hooks > "$temp/rendered.yaml"
  # Server-side dry run checks admission/RBAC without creating workloads.
  kubectl apply --kubeconfig "$KCFG" --context "$CTX" --request-timeout=30s --server-side --dry-run=server --force-conflicts --field-manager=suse-dashboard-preflight -f "$temp/rendered.yaml" > "$temp/admission.log"
  echo 'Values, renderizacao e admissao Kubernetes: OK. Isto ainda nao comprova entrega de metricas.'
  [[ "$action" == install ]] || exit 0
  # apply is explicit, even when a values file was previously used for deletion.
  helm upgrade --install "$release" "$chart" "${h[@]}" --values "$values" \
    --set lifecycle.action=apply --set lifecycle.confirmDelete= --wait --timeout 15m
fi

if [[ "$action" == status || "$action" == install ]]; then
  helm status "$release" "${h[@]}"
  kubectl get deployment,daemonset,pod,job "${k[@]}" -l "app.kubernetes.io/instance=$release"
  echo 'Proximo passo: abra os dashboards e valide dados recentes e filtros (docs/validation.md).'
  exit 0
fi

if [[ "$action" == remove ]]; then
  # Work from installed values, not a potentially edited local file.
  present=$(helm list "${h[@]}" --deployed --failed --pending --uninstalling --filter "^$release$" --short)
  if [[ -z "$present" ]]; then
    echo 'Release ja ausente. Confira o conteudo externo se a remocao anterior nao usou este procedimento.'
    exit 0
  fi
  backup_root=${PACK_BACKUP_DIR:-"$ROOT/local/backups"}
  mkdir -p "$backup_root"
  backup=$(mktemp -d "$backup_root/$release.XXXXXXXX")
  helm get values "$release" "${h[@]}" -o yaml > "$backup/values.yaml"
  helm get manifest "$release" "${h[@]}" > "$backup/manifest.yaml"
  mode=$(sed -n 's/^mode: *//p' "$backup/values.yaml" | tr -d "\"'")
  mode=${mode:-all}; [[ "$module" != applications ]] || mode=content
  if [[ "$mode" != telemetry ]]; then
    installed=$(helm list "${h[@]}" --deployed --failed --pending --uninstalling --filter "^$release$" -o json | sed -n 's/.*"chart":[[:space:]]*"\([^"]*\)".*/\1/p')
    version=$(helm show chart "$chart" | sed -n 's/^version: *//p')
    [[ "$installed" == "suse-observability-$module-$version" ]] || fail "Use o chart da versao instalada ($installed) para remover seus nomes exatos. Backup: $backup"
    helm upgrade "$release" "$chart" "${h[@]}" --values "$backup/values.yaml" \
      --set lifecycle.action=delete --set lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS \
      --wait --timeout 15m
  fi
  helm uninstall "$release" "${h[@]}" --wait --timeout 10m
  kubectl delete job "$release-dashboards" "$release-monitors" "${k[@]}" --ignore-not-found
  echo "Removido: $release. Backup Helm: $backup"
  echo 'Servidor, Agents oficiais, aplicacoes, VMs, volumes e Secrets compartilhados foram preservados.'
fi
