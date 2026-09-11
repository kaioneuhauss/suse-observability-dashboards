# Referência operacional · v6

Esta referência complementa o guia principal. Não é necessário executar todos os blocos em toda instalação.

## 1. Cliente novo: roles e Secrets dos publicadores

Use a CLI `sts` autenticada por um administrador da instância SUSE correta. O contexto de kubectl não muda o contexto de sts. Confira a URL na configuração da CLI e use `sts --context NOME ...` explicitamente para o preparo administrativo. As operações abaixo só se aplicam se o cliente ainda não possui papéis/tokens aprovados; no laboratório informado, preserve os existentes.

Permissões do papel de dashboards: `get-dashboards`, `create-dashboards`, `update-dashboards`, `delete-dashboards`. O papel do laboratório também possui `get-metrics`, `get-topology` e `get-views`. Permissões do papel de monitores: `get-monitors`, `create-monitors`, `update-monitors`, `delete-monitors`. O comportamento de importação da base 2.10.2 exige as três permissões de escrita para os monitores, conforme projeto anterior. Elas são permissões de instância, não limitadas aos 33 nomes.

Exemplo para criar os papéis em uma instância nova, usando Bash e um contexto sts já administrativo:

```bash
export SUSE_ADMIN_CONTEXT=admin-cliente
sts --context "$SUSE_ADMIN_CONTEXT" rbac create-subject --subject sre-dashboard-publisher
for PERMISSION in get-dashboards create-dashboards update-dashboards delete-dashboards get-metrics get-topology get-views; do
  sts --context "$SUSE_ADMIN_CONTEXT" rbac grant \
    --subject sre-dashboard-publisher --permission "$PERMISSION" || break
done
sts --context "$SUSE_ADMIN_CONTEXT" rbac create-subject --subject sre-monitor-publisher
for PERMISSION in get-monitors create-monitors update-monitors delete-monitors; do
  sts --context "$SUSE_ADMIN_CONTEXT" rbac grant \
    --subject sre-monitor-publisher --permission "$PERMISSION" || break
done
```

Se o subject já existir, confira as permissões em vez de recriar. Se ocorrer 403, interrompa: o chart não resolve RBAC nem propriedade elevando privilégios. Não crie um bootstrap admin token no servidor como atalho.

Crie um Service Token por publicador, com data de expiração aprovada, e guarde no cofre. Exemplo CLI 3.3.6 para dashboards; execute em subshell Bash, sem `set -x`:

```bash
(
  set -euo pipefail
  set +x
  umask 077
  TMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TMP_DIR"' EXIT
  # Substitua por uma data aprovada antes de executar.
  EXPIRATION=2027-09-11
  sts --context "$SUSE_ADMIN_CONTEXT" service-token create \
    --name sre-dashboard-helm --roles sre-dashboard-publisher \
    --expiration "$EXPIRATION" --output json > "$TMP_DIR/result.json"
  jq -erj '."service-token".token | select(type=="string" and length>0)' \
    "$TMP_DIR/result.json" > "$TMP_DIR/token"
  # Guarde a credencial no cofre antes de remover o temporario.
  kubectl --kubeconfig "$OBS_KCFG" --context observability \
    -n suse-observability create secret generic suse-observability-dashboard-token \
    --from-file=serviceToken="$TMP_DIR/token"
)
```

Para monitores, use role `sre-monitor-publisher`, nome de token `sre-monitor-helm` e Secret `suse-observability-monitor-token`. O campo continua `serviceToken`. Se o formato JSON da CLI for diferente, interrompa; não salve um Secret com valor vazio. `kubectl create` não sobrescreve credenciais existentes.

Os comandos de exemplo removem temporários ao sair; a cópia no cofre deve ser feita durante o preparo, antes de fechar o subshell. Como alternativa, obtenha o token do cofre diretamente para um arquivo temporário protegido e execute apenas o `kubectl create secret`. Não compartilhe a saída com o valor do token e não versione Secrets em base64.

## 2. Propriedade dos dashboards e rotação

No anexo do usuário, o humano `user-ff9zf` tinha `delete-dashboards`, mas recebeu 403. Usar o valor exato de `suse-observability-dashboard-token/serviceToken` resolveu. Por isso os cinco dashboards no chart central apontam para esse Secret. Não deduza propriedade apenas do role, do nome de um contexto chamado admin ou do fato de a tela ser pública.

O publicador usa nomes exatos do arquivo do chart. Se encontrar nome duplicado, identificador não customizado ou erro 403, falha sem criar uma cópia alternativa. Um Secret novo com outro token pode não possuir os objetos antigos. Antes de revogar a credencial proprietária, planeje a transferência ou recriação controlada pelo mecanismo suportado na sua versão SUSE. Guarde exports; trocar o token em Git não transfere propriedade.

`lifecycle.action=plan` lista a existência/ID com a credencial configurada, sem gravar na API. Ele não comprova permissão de escrita. O Job existe em Kubernetes mesmo no modo plan, e usa rede/CPU/download da CLI como os demais Jobs.

## 3. Backup e atualização de dashboards

Com sts autenticado como proprietário, exporte antes de mudar definições:

```bash
mkdir -p backups
sts --context CONTEXTO_PROPRIETARIO dashboard list
sts --context CONTEXTO_PROPRIETARIO dashboard describe \
  --id ID_ATUAL --file backups/dashboard-atual.yaml
```

Não use IDs antigos do histórico sem listar novamente. O chart usa `replace` por padrão para conservar o caminho de publicação comprovado na base anterior: só exclui/recria quando a definição difere. O ID muda e links diretos antigos podem quebrar. Alterações manuais no conteúdo gerido serão substituídas no próximo apply. A estratégia `patch` preserva o ID quando a API realmente persistir a alteração; o publicador compara depois e retorna erro se o conteúdo não coincidir. Não faz delete automático como fallback de um patch que falhou.

Os Jobs fazem backup temporário antes de replace e tentam restauração em uma falha de criação após uma exclusão feita por eles. O backup fica em emptyDir e não é garantia de recuperação. Helm rollback restaura objetos Kubernetes, não é transação da API SUSE. Para regressão, publique o chart/definição anterior em novo upgrade com a credencial correta ou restaure o export revisado.

## 4. Validar SAN dos quatro componentes KubeVirt

Use a CA pública extraída do próprio Harvester. Os nomes abaixo são defaults da base, não descoberta automática:

| Componente | server_name |
|---|---|
| virt-api | virt-api.harvester-system.svc |
| virt-controller | virt-controller.harvester-system.svc |
| virt-handler | virt-handler.harvester-system.svc |
| virt-operator | kubevirt-operator-webhook.harvester-system.svc |

Selecione um Pod de cada componente e confira todas as réplicas com certificados distintos. Exemplo virt-api:

```bash
COMPONENT=virt-api
DNS_NAME=virt-api.harvester-system.svc
POD=$(kubectl --kubeconfig "$HRV_KCFG" --context harvester \
  -n harvester-system get pods -l "kubevirt.io=$COMPONENT" \
  -o jsonpath='{.items[0].metadata.name}')
kubectl --kubeconfig "$HRV_KCFG" --context harvester \
  -n harvester-system port-forward "pod/$POD" 18443:8443
```

Em outro terminal, com DNS_NAME definido e na mesma pasta:

```bash
DNS_NAME=virt-api.harvester-system.svc
openssl s_client -connect 127.0.0.1:18443 \
  -CAfile private/kubevirt-ca.pem -servername "$DNS_NAME" \
  -verify_hostname "$DNS_NAME" -verify_return_error </dev/null
curl --fail --silent --show-error --cacert private/kubevirt-ca.pem \
  --resolve "$DNS_NAME:18443:127.0.0.1" \
  "https://$DNS_NAME:18443/metrics" -o private/kubevirt-metrics.txt
```

Exija TLS válido e HTTP 200. Ajuste a porta caso o Pod real não use 8443. Encerre o túnel e repita. Um teste através do Service pode alcançar apenas uma réplica e não comprova os quatro certificados. Não altere o certificado do KubeVirt só para adaptar o chart; ajuste `kubevirt.serverNames` ao SAN válido do destino. Se não houver identidade verificável adequada, pare e revise a exposição suportada.

## 5. Baseline e limites

Padrão observe: allowlist ativa e limites de CPU/RAM/disco ativos, porém sem aplicar os limites opcionais de sample/series/labels. Isso não é medição de todas as métricas do endpoint nem garantia de retenção sem perdas.

Antes de enforce, acompanhe uma janela representativa de carga e crescimento, não somente 12 horas ociosas. Consultas de partida para vmagent:

```promql
max by (cluster_name,job,instance) (scrape_samples_scraped)
max by (cluster_name,job,instance) (scrape_samples_post_metric_relabeling)
max by (cluster_name,job,instance) (scrape_duration_seconds)
max by (cluster_name,job,instance) (up)
sum by (cluster_name) (vmagent_remotewrite_pending_data_bytes{job="sre-collector"})
sum by (cluster_name) (increase(vmagent_remotewrite_samples_dropped_total{job="sre-collector"}[15m]))
sum by (cluster_name) (increase(vm_persistentqueue_bytes_dropped_total{job="sre-collector"}[15m]))
```

No modo enforce, quando essas séries estiverem disponíveis na versão vmagent:

```promql
scrape_series_current / scrape_series_limit
sum_over_time(scrape_series_limit_samples_dropped[1h])
```

`sample_limit` e `label_limit` não são uma garantia de descartar somente uma amostra excedente: podem falhar o scrape inteiro. `series_limit` é uma extensão do vmagent; não é enviada ao Prometheus Receiver do OTel. Métricas sintéticas de scrape variam entre coletores/versões; não invente zero quando a série não existe.

O OTel exporta telemetria interna pelo próprio pipeline em `service_name="sre-otel-collector"` (job normalizado `default/sre-otel-collector`, cluster em `k8s_cluster_name`). Procure as famílias `otelcol_exporter_queue_size`, `otelcol_exporter_queue_capacity`, `otelcol_exporter_send_failed_metric_points` e `otelcol_process_memory_rss` no Metrics Explorer. Sufixos `_total`/unidades podem ser normalizados na exportação; confira os nomes reais antes de criar alertas. Se a instância SUSE estiver fora, esse mesmo pipeline pode não entregar os alertas sobre si: mantenha monitoramento externo do central.

O catálogo contém 33 monitores, incluindo filas, descartes e falha de scrape Traefik. Compare os limiares com o baseline do cliente; nem toda consulta de capacidade implica um alerta adicional.

## 6. Efeitos de recursos e limites de suporte

A coleta host usa hostNetwork e mounts read-only de /proc, /sys e raiz. Isso é acesso sensível apesar de não executar escritas. Revise políticas de admissão/Pod Security e portas locais; não crie exceção global ao namespace sem analisar o impacto sobre outros workloads. Os coletores etcd também disputam CPU e disco com o control plane.

O chart KubeVirt tem Role de leitura para pods/services/EndpointSlices de `harvester-system` e não modifica KubeVirt, VMs ou Longhorn. Seus limites ainda podem causar descarte de telemetria em sobrecarga. O publicador tem `automountServiceAccountToken: false`; não recebe credencial para manipular recursos Kubernetes e não lê Secrets pela API. O kubelet injeta só a chave indicada pelo PodSpec.

As versões explícitas herdadas de v4 não equivalem a certificação entre toda combinação de Harvester/RKE2/SUSE. Os charts novos são customizados. Consulte o suporte SUSE para a cobertura contratual, especialmente do add-on Experimental, e mantenha o código sob controle de versão com responsáveis pela integração.

## 7. Drift, tags e imagens

As definições, layout, filtros e publicadores foram revisados. A base usa CLI 3.3.6 e imagem OTel 0.156.0-k8s-13.1. O modo padrão do Job baixa a CLI por HTTPS, verifica o SHA-256 fixado nos defaults e extrai somente um binário sts regular. Se mudar a distribuição/versão, valide e atualize seu hash; prefira uma imagem pré-construída no pipeline do cliente para ambientes restritos.

O Dockerfile copia `/usr/bin/sts` da imagem oficial distroless para uma imagem Python. Não tenta executar shell/cp dentro da imagem distroless. A imagem resultante ainda precisa ser construída, escaneada, validada e fixada por digest. Nesse modo `publisher.cli.path=/usr/local/bin/sts`; os Jobs deixam de baixar a CLI, mas ainda precisam acessar a API SUSE.

Fleet gerencia o Job/ConfigMap Kubernetes, não monitora continuamente os objetos externos. Para nova rodada após rotação de Secret ou restauração manual, aumente `lifecycle.revision` em Git. Secrets usados como variáveis de ambiente só são relidos por um novo Pod; para o KubeVirt faça rollout planejado do Deployment após atualizar a credencial pela fonte oficial do Agent.

Referências: R1–R10 no guia principal; código primário da CLI 3.3.6 em https://github.com/StackVista/stackstate-cli/tree/v3.3.6/cmd/dashboard e https://github.com/StackVista/stackstate-cli/blob/v3.3.6/Dockerfile.goreleaser.

## 8. Verificação de monitores e notificações

O papel do publicador consegue importar e consultar monitores. No laboratório, `sts monitor run` retornou 403 com esse papel; isso é diferente de falha na avaliação agendada. `sts monitor status` confirmou execuções bem-sucedidas e zero estados sem associação. Não acrescente privilégios administrativos ao publisher apenas para testar. Um operador com a permissão apropriada pode usar a prévia de teste da interface ou uma credencial operacional aprovada. O teste padrão da CLI é dry-run; `--yes` grava estados e pode gerar notificações.

Confirme o destino antes de enviar testes. O teste de canal prova conectividade, mas não substitui validar os filtros de monitor, severidade e componente. Capture a mensagem de abertura e a de recuperação com cluster, namespace, recurso, valor, limiar e link da investigação.

## 9. Inventário de configurações de pods

O pequeno Deployment `sre-platform-telemetry-pods` lê somente a lista de Pods da API Kubernetes, com paginação de 500 objetos e limite de 100.000 objetos por rodada. O ClusterRole concede apenas `list` em `pods`; não lê Secrets, não executa comandos e não coleta variáveis de ambiente. O exporter publica nome/namespace/container, estado e requests/limits de containers regulares. Exclui pods terminados e init containers.

Essa fonte corrige a ausência das configurações de três pods hotplug na coleta oficial instalada. O consumo de CPU/memória continua vindo do Agent. `sre_pod_inventory_success=1` informa uma rodada recente válida; em falhas ou dados vencidos, o inventário deixa de publicar a configuração antiga. O gráfico de cobertura e os monitores nativos de disponibilidade ajudam a identificar falha desse Deployment. Revise RBAC e cardinalidade no cliente.

## Totals that follow the selected time period

Request totals, HTTP error totals and request breakdowns in the application and Traefik dashboards now use the toolbar period. The duplicate 1-hour/24-hour request cards were replaced. The new count is explicitly labelled Estimated. Traefik shows total requests and average requests/s for the selected period; the application view shows total requests and HTTP 5xx count, alongside its average rate. Five-minute/recent rates still show current traffic and are explicitly labelled.

The tested SUSE 2.10.2 frontend exposes `__interval` and `__rate_interval`, but no full-range variable. The selected-period totals use the installed VictoriaMetrics backend and sum non-overlapping one-minute counter increases across the selected period. All such queries explicitly set `minStep: "1m"`. Keep the one-minute window and the one-minute query step together; changing only one can skip or duplicate increments. The initial query point is excluded to avoid including the preceding minute. The core expression is:

```promql
range_sum(increase(counter[1m]) and on()
  (vector(time()) > scalar(last_over_time(vector(time())[1s:1s] @ start()))))
```

Counter resets are handled before aggregation. Average traffic divides the total estimate by the selected duration, expressed using frozen `time()` values at `@ start()` and `@ end()`. This must run as a range query with a 60-second step; an instant `/query` call cannot validate it. The SUSE API rejects a MetricsQL `[1i]` window and standalone `start()`/`end()` arithmetic, so those alternatives are not used.

This backend-specific implementation passed actual SUSE API tests for 1 hour, 24 hours, 48 hours and 7 days. It is not portable to a pure Prometheus backend without adaptation. Periods above seven days and arbitrary partial-minute boundaries require further acceptance testing. Scrape gaps, new series, retention and unavailable historical Ingress inventory can undercount activity. Current inventory can also exclude applications that have already been deleted. Access logs are required for an authoritative per-request audit. Alert windows remain fixed and independent of the viewer's period.

Sources: [SUSE PromQL parameters](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/metrics/k8sTs-explore-metrics.html), [VictoriaMetrics range transforms](https://docs.victoriametrics.com/MetricsQL.html#range_sum).
