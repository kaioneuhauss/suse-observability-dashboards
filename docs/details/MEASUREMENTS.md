# Recursos, armazenamento e segurança

Referência técnica detalhada da implementação validada no laboratório. Para uma instalação nova, comece pelo [guia simples](../GUIA-HELM-FLEET.md). Os comandos com nomes de clusters e dois Secrets representam a instalação existente; não são campos obrigatórios para todo cliente. O [preparo simplificado de credenciais](../../prerequisites/PUBLISHER.md) permite reutilizar uma role padrão e um único Secret.

Medição do laboratório em 11/09/2026. Os números abaixo ajudam a planejar um piloto; não são uma certificação de desempenho nem substituem o dimensionamento oficial do SUSE Observability.

## 1. O que foi medido

Foram separados três custos: containers adicionais de coleta, Jobs temporários de publicação e servidor central. Os dashboards consultam dados; criar outro gráfico sobre uma série existente não grava outra cópia dessa série. Coletores, novas séries, monitores, consultas simultâneas e retenção podem aumentar o consumo.

Os coletores foram amostrados dez vezes, a cada 30 segundos, durante aproximadamente quatro minutos e meio, pela API `metrics.k8s.io`. CPU representa a taxa de uso na janela informada pelo Metrics Server; memória representa a medida de uso exposta por essa API. Não é um teste de carga máxima. O histórico do servidor foi comparado em janelas de uma hora, no mesmo horário, há um, três e sete dias. O uso dos PVCs veio do kubelet; o armazenamento de métricas também foi conferido diretamente nas estatísticas do VictoriaMetrics.

**Não existe uma medição controlada anterior à primeira instalação do projeto.** O ponto de sete dias atrás já tinha componentes de observabilidade em execução. Portanto, o aumento histórico do servidor não pode ser atribuído integralmente a estes charts. Caches, tráfego, novos recursos descobertos, saúde, topologia e outras integrações também mudaram.

## 2. Coletores adicionais nos clusters

| Cluster | Nós | CPU média | Maior CPU amostrada | Maior memória amostrada | Requests CPU / memória | Limits CPU / memória |
|---|---:|---:|---:|---:|---|---|
| Observability | 6 | 30 mCPU | 39,4 mCPU | 268,7 MiB | 180 mCPU / 568 MiB | 2450 mCPU / 2240 MiB |
| Rancher | 3 | 21,4 mCPU | 27,9 mCPU | 269,6 MiB | 120 mCPU / 400 MiB | 1700 mCPU / 1568 MiB |
| Harvester | 1 | 18,3 mCPU | 31,0 mCPU | 192,1 MiB | 65 mCPU / 360 MiB | 950 mCPU / 1184 MiB |

Inclui plataforma, inventários e, no Harvester, o Collector KubeVirt: 23 Pods e 38 containers. Exclui o Agent oficial e o servidor SUSE, que já são pré-requisitos. Cada linha é a soma dos containers adicionais naquele cluster. `1000 mCPU = 1 núcleo`.

O maior uso observado representou aproximadamente 0,11%/0,23%/0,10% da CPU allocatable e 0,37%/1,13%/0,15% da memória allocatable dos respectivos clusters. Essa proporção depende do tamanho dos nós do laboratório. Requests são reservas utilizadas pelo scheduler; limits são limites por container, não uma reserva adicional nem um consumo contínuo garantido.

Para reproduzir este laboratório, planeje inicialmente as **reservas da tabela**, acrescidas de margem para rollout, outros workloads e picos. Não use a CPU média como request recomendado. Para outro cliente, recalcule as quantidades de nós, membros etcd e clusters.

### Valores padrão por container

| Componente | Request CPU / RAM | Limit CPU / RAM | Quantidade típica |
|---|---|---|---|
| node-exporter | 10m / 24Mi | 100m / 96Mi | Um por nó Linux |
| vmagent | 10m / 32Mi | 150m / 128Mi | Um por nó; um por membro etcd; um para cada inventário/Traefik habilitado |
| Inventário de Ingress | 5m / 24Mi | 100m / 64Mi | Um por cluster com Traefik |
| Inventário de Pods | 5m / 48Mi | 100m / 192Mi | Um por cluster |
| Collector KubeVirt | 20m / 192Mi | 300m / 512Mi | Um por Harvester |
| Publicador de conteúdo | 20m / 64Mi | 200m / 192Mi | Dois Jobs temporários no central |
| Teste Helm de Traefik | 5m / 32Mi | 100m / 96Mi | Um Pod temporário quando executado |

Todos os containers renderizados têm requests e limits de CPU e memória. Os schemas dos três charts exigem esses campos e rejeitam ausência ou zero. O teste `test_resources.py` verifica todos os perfis e casos inválidos. Kubernetes também valida se requests excedem limits no aceite do manifesto. O pacote não altera os recursos do Agent oficial, Traefik, etcd, aplicações ou servidor SUSE.

A memória interna de trabalho do vmagent é limitada a 64 MiB, dentro do limit de 128 MiB. No OTel, `memory_limiter` usa 384 MiB dentro de um limit de 512 MiB, com margem para picos e processamento. Limites muito baixos podem causar throttling, OOM ou perda de coleta; não foram reduzidos com base na amostra curta.

## 3. Servidor central: comparação histórica

| Momento | CPU média em uma hora | Memória média em uma hora |
|---|---:|---:|
| Sete dias antes | 0,657 núcleo | 19,524 GiB |
| Três dias antes | 0,811 núcleo | 20,265 GiB |
| Um dia antes | 0,815 núcleo | 19,872 GiB |
| Medição atual | 0,871 núcleo | 20,608 GiB |

A diferença observada em relação a sete dias antes foi **+0,214 núcleo e +1,084 GiB de memória** no conjunto do servidor. Isso é comparação de períodos, não uma medição causal do custo dos dashboards. Não significa que todo cliente precise acrescentar exatamente esses valores.

A consulta soma containers do servidor com nomes `suse-observability-*`, excluindo os Jobs `suse-observability-content-*`, no namespace central. Usa CPU do Agent em nanocores convertida para núcleos e memória working set convertida para GiB. Compara a média de uma hora em cada data para reduzir a dependência de um único instante.

Para produção, comece pelo perfil oficial compatível com o ambiente observado e acompanhe uso, filas, duração de consultas e ingestão. Os perfis SUSE usam **Default Nodes**: uma máquina grande pode representar mais de uma unidade de dimensionamento. Não reduza o servidor para os valores baixos de CPU observados neste laboratório. Consulte os [requisitos oficiais](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/requirements.html).

## 4. Armazenamento: onde houve crescimento

| PVC/componente | Uso atual do filesystem | Um dia antes | Sete dias antes | Crescimento em 24h | Capacidade aproximada do filesystem |
|---|---:|---:|---:|---:|---:|
| VictoriaMetrics | 0,942 GiB | 0,779 GiB | 0,184 GiB | 0,162 GiB | 48,915 GiB |
| Kafka | 38,400 GiB | 32,401 GiB | 19,567 GiB | 5,999 GiB | 97,872 GiB |
| HBase | 2,286 GiB | 2,004 GiB | 1,466 GiB | 0,281 GiB | 97,872 GiB |
| Elasticsearch | 1,275 GiB | 1,179 GiB | 0,239 GiB | 0,096 GiB | 48,915 GiB |

Os charts deste projeto **não criam PVCs**. O histórico é armazenado pelo servidor existente. Os números do quadro são do filesystem, que pode ter capacidade útil menor que o tamanho solicitado ao PVC.

O VictoriaMetrics estava configurado com `retentionPeriod=1` (um mês). Não há evidência de necessidade imediata de expandir o seu PVC de 50 GiB por causa deste pacote, considerando o uso atual e esta taxa. Ainda é necessário observar pelo menos um ciclo completo de retenção, crescimento de séries e picos de consulta. Não foi reduzida a retenção nem o tamanho de nenhum volume.

### Kafka merece acompanhamento separado

Uma inspeção por diretório encontrou cerca de 15,9 GiB em `sts_correlated_connections`, 11,7 GiB em `sts_health_sync` e 5,7 GiB em `sts_correlate_endpoints`. São tópicos de correlação e saúde do servidor; não são uma cópia de cada gráfico. Há configurações por tópico diferentes da retenção global: por exemplo, `sts_health_sync` tem retenção temporal `-1`, enquanto outros tópicos usam 24h. A retenção por bytes e o tamanho/rotação de segmentos também importam.

Por isso, não se deve extrapolar indefinidamente +6 GiB/dia nem alterar globalmente a retenção do Kafka como uma “otimização dos dashboards”. Se esse crescimento persistir, acompanhe atraso dos consumidores, rotação/remoção de segmentos e uso por tópico; envolva o suporte SUSE antes de alterar políticas internas. A leitura de configuração e de diretórios foi feita sem alterar o broker ou remover dados.

### Filesystem, PVC e armazenamento físico são medidas diferentes

O PVC de métricas de 50 GiB foi rastreado pelo CSI Harvester até o volume Longhorn. Havia uma réplica, estado saudável e aproximadamente 2,74 GiB em `actualSize`, enquanto o filesystem mostrava cerca de 0,94 GiB em uso. Blocos alocados, snapshots, descarte e camadas de virtualização podem produzir diferenças; essa diferença isolada não prova erro na métrica do filesystem. A causa exata de cada bloco não foi determinada. Em um cliente, inclua réplicas, snapshots, backups e folga do datastore no cálculo físico.

## 5. Estimativa incremental de métricas

Foram contadas cerca de **6101 séries ativas** das fontes do projeto. Com intervalo de 30 segundos, isso equivale a aproximadamente **203 amostras/s**, ou **17,57 milhões/dia**, supondo séries estáveis e intervalos regulares. A ingestão global bruta do VictoriaMetrics foi aproximadamente 3664 amostras/s numa janela de 273 segundos. A proporção de 5,6% é indicativa: não é uma atribuição exata após deduplicação e pode variar com churn e aplicações.

Os arquivos de dados e índices do VictoriaMetrics representavam aproximadamente 1,81 byte por amostra armazenada no conjunto observado. Compressão varia com nomes, labels, churn e repetição; não use esse valor como garantia para outro cliente.

Para planejamento, o quadro abaixo usa **cenários de 2 a 8 bytes/amostra**, não um compromisso de compressão da SUSE. Estima somente dados e índices adicionais deste fluxo, antes de folga operacional e replicação:

| Retenção | Cenário 2 bytes/amostra | Cenário 8 bytes/amostra |
|---|---:|---:|
| 14 dias | 0,46 GiB | 1,83 GiB |
| 30 dias | 0,98 GiB | 3,93 GiB |
| 90 dias | 2,95 GiB | 11,78 GiB |

Fórmula: `séries × 86400 ÷ intervalo_segundos × dias × bytes_por_amostra ÷ 1024³`. Acrescente margem para compaction, caches, crescimento e operação; depois considere a redundância do servidor e as réplicas do storage. A retenção real do servidor deste laboratório continua sendo um mês. O cenário de 90 dias não foi implantado nem testado.

## 6. Disco temporário e indisponibilidade do destino

Cada vmagent tem uma fila limitada a 1024 MiB por URL, em `emptyDir` limitado a 1280 MiB. No laboratório são 22 instâncias: até 22 GiB de filas configuradas, distribuídos pelos nós, e até 27,5 GiB de limites desses volumes temporários. Isso **não estava ocupado**: a métrica de backlog era zero. O request de ephemeral storage é uma reserva diferente; não é um PVC.

Se o destino parar, a fila pode crescer, atingir o limite e descartar dados. `emptyDir` não sobrevive à substituição do Pod. O Collector KubeVirt tem fila em memória de 128 requests; esse número não representa bytes. Os monitores de backlog/descarte ajudam a detectar o problema. Uma interrupção longa sem perda exige uma decisão específica de durabilidade e capacidade; este pacote não promete armazenamento offline ilimitado.

## 7. Otimizações implementadas

- Allowlist de famílias efetivamente utilizadas, antes do envio; evita coletar indiscriminadamente todos os exporters.
- Intervalo padrão de 30s e timeout de 10s; sem scrape de 1s para simular tempo real.
- Desativação de `loadavg`, `time` e `stat` no node-exporter: suas famílias já eram descartadas e não eram usadas pelos dashboards/monitores. Mantidos CPU, memória, filesystem, disco, rede e vmstat. Aplicação com canário e rollout de um nó por vez.
- Inventário de Pods paginado, atualização de 30s e expiração de 90s; consultas apenas de leitura, sem um processo de inventário por nó.
- Filas, batch, memória, requests/limits e Jobs com duração limitada. Nenhum publicador fica consultando indefinidamente o servidor.
- Deduplicação de filesystems e seleção de partições operacionais; sem somar bind mounts e discos loop.
- Uma instalação central para os cinco dashboards; métricas compartilhadas entre painéis. Sem duplicar a instalação do Agent ou Collector KubeVirt.

A economia específica de remover os três coletores internos não foi isolada em benchmark. Essa mudança reduz trabalho desnecessário, mas não justifica prometer uma redução numérica de CPU/RAM. Intervalo de 60s poderia reduzir amostras de gauges, porém exige rever taxas, janelas e monitores; não foi aplicado globalmente porque alteraria a resolução validada.

## 8. Controles de segurança e limites

| Controle | Implementação / atenção no cliente |
|---|---|
| Credenciais | Secrets existentes; ingestão separada de publicação. Nenhuma credencial no Git/ZIP. |
| Publicadores | Permissões de dashboards ou monitores; sem administrador global. Monitor import exige também delete-monitors na versão validada; o fluxo apply não executa exclusão. |
| Kubernetes RBAC | Inventários/descoberta somente leitura dos recursos necessários. Coletores locais sem automount de token de ServiceAccount. |
| Host | node-exporter lê `/proc`, `/sys` e raiz do host por mounts read-only; precisa desse acesso para medir o SO. Host networking e hostPath não atendem automaticamente ao perfil Pod Security Restricted. Avaliar exceção no namespace. |
| Container | Non-root, sem privilege escalation, capabilities removidas, root filesystem read-only e seccomp nos componentes de longa duração. Conferir as políticas de admissão do destino. |
| Rede | Endpoints locais de host/etcd em loopback. Traefik 9100 sem exposição pública; regra opcional limitada a coletores, somente após revisar a isolação existente. |
| TLS | Validação de CA e SAN; sem insecureSkipVerify. CA do navegador não substitui a CA dos containers. Renovação das CAs copiadas exige procedimento. |
| Imagens | Versões explícitas. O publicador valida SHA-256 da CLI. Para produção/air gap, usar registry e imagem aprovados, idealmente digest, com o processo de assinatura/scan da organização. Não foi feita certificação independente de ausência de CVEs. |
| Dados | Labels com cardinalidade limitada; não adicionar payloads, tokens, URLs com IDs livres ou dados pessoais às métricas. |
| Notificações | SMTP global e regras manuais, por decisão do usuário. Sem credencial adicional de notificações no chart. |

O laboratório apresentou filas vazias, alvos saudáveis e baixo consumo no período medido. Isso não garante impacto zero sob qualquer carga ou indisponibilidade. O aceite deve incluir carga representativa, recursos livres no nó, ausência de OOM/throttling persistente, duração de scrapes abaixo do intervalo, ausência de perdas e crescimento de storage compatível com a retenção.

## 9. Como repetir a medição no cliente

1. Antes dos charts, registre por pelo menos um período representativo CPU/memória dos nós e servidor, tamanho dos PVCs, ingestão, duração de consultas e retenção. Guarde horários e versões.
2. Instale em um cluster canário. Repita a mesma carga e as mesmas janelas; separe os containers adicionais dos existentes.
3. Compare 24h, sete dias e um ciclo completo de retenção. Não reduza limites apenas porque o primeiro scrape consumiu pouco.
4. Acompanhe os monitores de fonte ausente, fila/descarte, PVC disponível/previsão e latência de disco. Investigue saturação e consumidores antes de aumentar recursos indiscriminadamente.
5. Se uma expansão for necessária, confirme suporte da StorageClass, amplie o PVC e mantenha os values do servidor consistentes. Apenas mudar o values não amplia automaticamente um PVC existente. Siga o [procedimento de retenção e expansão da SUSE](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/data-management/data_retention.html).

Comandos de leitura, ajustando o contexto e o namespace:

```bash
kubectl top pods --kubeconfig "$OBS_KCFG" --context observability \
  -n suse-observability-agent --containers
kubectl top pods --kubeconfig "$OBS_KCFG" --context observability \
  -n suse-observability --containers
kubectl get pvc --kubeconfig "$OBS_KCFG" --context observability \
  -n suse-observability
kubectl get events --kubeconfig "$OBS_KCFG" --context observability \
  -n suse-observability-agent --sort-by=.lastTimestamp
```

No explorador de métricas SUSE, use a janela escolhida e confira os labels reais:

```promql
sum by (cluster_name) (vmagent_remotewrite_pending_data_bytes{job="sre-collector"})
sum by (cluster_name) (increase(vmagent_remotewrite_samples_dropped_total{job="sre-collector"}[30m]))
max by (cluster_name,node,job,instance) (scrape_duration_seconds{job=~"sre-node|sre-etcd|traefik"})
otelcol_exporter_queue_size{service_name="sre-otel-collector"}
max by (persistentvolumeclaim) (kubernetes_kubelet_volume_stats_used_bytes{namespace="suse-observability",cluster_name="observability-cluster"})
```

Ausência de uma série de erro não prova zero erros. Confirme que o próprio collector está presente e atualizando antes de interpretar silêncio como saúde.
