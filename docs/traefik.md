# Traefik

Instala somente a coleta Traefik, inventário de Ingress, um dashboard e seis monitores. Não instala node-exporter, coleta etcd ou KubeVirt.

## Pré-requisitos

Complete os [pré-requisitos comuns](prerequisites.md). Identifique o Traefik real, a versão, o namespace e a fonte que administra seus values. No RKE2 provisionado pelo Rancher, normalmente é `spec.rkeConfig.chartValues.rke2-traefik`; em RKE2 local/importado, é o HelmChartConfig. Se Fleet administra essa configuração, altere o Git de origem.

Mescle este fragmento nos values existentes do Traefik:

```yaml
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

Essa alteração pode reiniciar o Traefik. Preserve os demais values e valide HTTP/HTTPS após o rollout. O chart de dashboards não altera o Traefik. Veja os fragmentos em `prerequisites/rke2-traefik-values.yaml` e `prerequisites/rancher-rke2-traefik.yaml`.

## Instalar

```bash
cp examples/traefik.yaml local/traefik.yaml
```

Preencha `clusterName` e `observability.url`. Os padrões encontram `app.kubernetes.io/name=rke2-traefik` em `kube-system`, porta 9100. Para outro deployment, ajuste:

```yaml
telemetry:
  traefik:
    namespace: traefik
    selector:
      app.kubernetes.io/name: traefik
    port: 9100
    targetPort: metrics
```

Se políticas existentes isolam o Traefik, permita somente a coleta interna. O chart pode acrescentar essa regra após confirmar o isolamento:

```yaml
telemetry:
  traefik:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

Não habilite essa opção em Pods que ainda não são isolados sem revisar o efeito nas portas web/websecure.

```bash
helm upgrade --install obs-traefik ./charts/suse-observability-traefik \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$NS" \
  -f local/traefik.yaml --wait --timeout 15m
```

## Aceite e interpretação

Confirme `up{job="traefik",cluster_name="meu-cluster"}=1` para todas as réplicas. Faça uma requisição a uma aplicação conhecida, confira o aumento de seu contador e teste os filtros cluster/namespace/aplicação.

p95/p99 dependem dos buckets e do volume observado. Conexões abertas são simultaneidade, não requisições concluídas. O painel de conexões é de escopo do cluster e não segue o filtro de aplicação. Tráfego de health checks e de controle pode explicar diferenças com o contador da aplicação. Os monitores de mapeamento Traefik foram validados com o DaemonSet RKE2; para Traefik em Deployment, adapte e valide o mapeamento topológico antes de confiar na notificação.

Referências: [RKE2 HelmChartConfig](https://docs.rke2.io/helm), [Traefik Prometheus](https://doc.traefik.io/traefik/observability/metrics/prometheus/).
