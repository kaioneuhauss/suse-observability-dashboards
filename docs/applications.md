# Aplicações instrumentadas

Este chart publica um dashboard e dois monitores. Não exige Traefik, Harvester ou coletores de host. **Não instrumenta aplicações nem cria um receptor OTLP**: as métricas da aplicação precisam estar chegando ao SUSE.

## Métricas necessárias

| Sinal | Padrão esperado |
|---|---|
| Requisições concluídas | `http_server_requests_total` |
| Latência | `http_server_request_duration_seconds_bucket`, `_sum`, `_count` |
| Requisições ativas, se expostas | `http_server_active_requests` |
| Identidade | `cluster_name`, `service_name`, `namespace` (mapeamento dos monitores) |
| Rota e resultado | `http_route`, `http_response_status_code` |

Use rotas normalizadas (`/orders/{id}`), não IDs, URLs brutas ou usuário como labels. Histograma em segundos. Latência sem buckets não permite calcular p95/p99. Traces isolados não garantem a existência dessas métricas.

O padrão preserva o contrato usado pelo projeto. Para uma aplicação OTel que expõe o contador do histograma e os labels normalizados correspondentes, configure os nomes reais, por exemplo:

```yaml
observability:
  url: https://observability.exemplo.com.br
applicationMetrics:
  requestCounter: http_server_request_duration_seconds_count
  clusterLabel: k8s_cluster_name
```

O exemplo pressupõe que `namespace` já identifica o namespace Kubernetes correto; se a origem usa outro label, normalize-o no pipeline antes da ingestão.

Também existem `durationHistogram`, `serviceLabel`, `statusLabel` e `routeLabel`. O chart aplica os aliases aos filtros, painéis e monitores. Não agrega automaticamente contratos diferentes em uma mesma definição. Confirme nomes, unidade, status e semântica no Metrics Explorer antes de selecionar um perfil; a validação ao vivo deste laboratório usou o contrato padrão.

## Instalar

Prepare o [Secret de publicação](prerequisites.md). Use o cluster/namespace central ou outro que tenha acesso HTTPS à API SUSE:

```bash
cp examples/applications.yaml local/applications.yaml
helm upgrade --install obs-applications ./charts/suse-observability-applications \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$NS" \
  -f local/applications.yaml --wait --timeout 15m
```

Somente a URL precisa ser alterada quando os nomes padrão de Secret e métricas já correspondem ao ambiente.

## SRE e aceite

Compare uma rota conhecida com requisições, códigos HTTP e duração na aplicação. Teste tráfego, erro e recuperação em uma aplicação de teste autorizada. `No data` pode ser ausência de tráfego ou instrumentação; não significa disponibilidade de 100%.

O painel de disponibilidade mede `1 - fração de 5xx` entre requisições concluídas. Não mede uptime ou falhas anteriores à instrumentação. O consumo do orçamento de erro usa `slo.availabilityTarget`, padrão `99.9`, e compara janelas de 5 minutos e 1 hora. `1x` é a velocidade de consumo permitida; isso não comprova um SLO de 30 dias. Health/ready/live/metrics são excluídos pelo contrato das consultas; revise se sua aplicação usa esses termos em rotas de negócio.

Os monitores publicados continuam sendo erro HTTP e latência. O painel de orçamento fornece contexto; criar uma política de paging por SLO exige objetivo acordado, volume mínimo e teste das janelas. Referências: [SUSE e OpenTelemetry](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/setup/otel/getting-started/getting-started-k8s.html), [Google SRE: alertas por SLO](https://sre.google/workbook/alerting-on-slos/).
