# Contratos e precisão das métricas

Uma consulta executar sem erro não comprova sua interpretação. O aceite verifica nome/labels, tipo, unidade, janela, denominador, deduplicação, comportamento sem dados e comparação com a fonte. A evidência e os limites deste ambiente estão em [lab-validation.md](lab-validation.md).

## Unidades e fórmulas

| Família | Contrato usado |
|---|---|
| CPU KubeVirt | `rate(cpu_usage_seconds_total[5m])` = CPUs consumidas; porcentagem = 100 × consumo / (cores × sockets × threads), sem substituir topologia por CPU request |
| Espera de vCPU | Counters em segundos; taxa por vCPU, deduplicação por VM/id e média dos vCPUs, vezes 100 |
| RAM guest | `available` é a memória reportada pelo domínio; `usable` corresponde ao disponível recuperável do guest. Uso estimado = available − usable. RSS QEMU e memória configurada são medidas distintas |
| Swap guest | KubeVirt expõe tráfego acumulado como gauge; delta positivo de 5 minutos / 300 é uma estimativa vulnerável a reinício/reset. Não se aplica uma taxa de counter indiscriminadamente |
| I/O guest | Tempo acumulado em segundos / operações acumuladas, usando taxas na mesma janela; × 1000 para ms. Operações zero deixam latência sem valor |
| CPU host | Taxa do counter em segundos por modo/CPU; média entre CPUs. CPU ocupada = 1 − idle. Capacidade usa CPUs lógicas |
| RAM host | MemTotal e MemAvailable em bytes; uso operacional = total − available, incluindo efeitos de cache recuperável |
| CPU do Agent | `container_cpu_usage` em nanocores; / 1.000.000 = mCPU. Não aplicar `rate()` novamente. Requests/limits do inventário em cores, × 1000 = mCPU |
| Memória do Agent | Working set e RSS em bytes, com significados diferentes. Requests e limits do inventário também em bytes |
| Longhorn estados | Robustness/attachment: uma série por estado com valor 0 ou 1. Contar estados ativos após deduplicar volume, não somar quantidade de séries |
| Longhorn I/O | Latência gauge em **ns**, / 1.000.000 = ms. IOPS e throughput são gauges já calculados como taxas |
| Longhorn capacidade | Volume provisionado é lógico; node usage/capacity é físico gerenciado; scheduled é reserva lógica de réplicas. Thin provisioning pode deixar scheduled acima do físico |
| Longhorn proteção | Last backup é timestamp Unix ou zero; idade apenas para timestamp positivo. Snapshot size não é espaço físico total replicado nem espaço recuperável garantido |
| HTTP | Counters de requisições e buckets acumulados; taxas antes de agregar. Histogramas em segundos, quantis × 1000 = ms. Quantis são estimativas dependentes dos buckets |
| HTTP no período | `range_sum(increase(counter[${__interval}]) …)` soma incrementos não sobrepostos seguindo o step efetivo resolvido pela API SUSE. `[1i]` é aceito pelo backend, mas rejeitado pelo parser SUSE 2.10.2. Não congelar o incremento em `@ end()` e não fixar 1 minuto quando o step pode aumentar |
| Disponibilidade HTTP | 1 − fração de 5xx das requisições concluídas. Tráfego zero deixa o quociente indefinido. Não equivale a uptime; 4xx não consome esse orçamento específico |
| VMIC | Inventário de CRs; diskSize em bytes lógicos. Intervalos calculados somente entre timestamps explícitos; não representam duração completa ou porcentagem global |

`percentunit` recebe razões entre 0 e 1; `percent` recebe valores já multiplicados por 100. Bytes IEC usam potências de 1024. Labels de cluster de OTLP (`k8s_cluster_name`) e de remote write (`cluster_name`) são normalizados explicitamente quando há junção.

As métricas de estado/configuração são deduplicadas por identidade lógica antes de contar. As taxas de counters são calculadas por série antes de agregar, para respeitar resets. A deduplicação não permite instalar coletores duplicados deliberadamente: cada conjunto de alvos deve ter um proprietário.

## Ausência e histórico

- Sem telemetria não se presume zero nem saudável. Zeros de contagem só têm fallback quando existe a família necessária de inventário/estado. Ausência de métrica de backup não vira zero volumes desprotegidos.
- Um disco ocioso pode ter IOPS zero e latência vazia. Uma VM parada pode não ter consumo. Um guest sem estatísticas pode não ter RAM/filesystem. Esses casos precisam ser separados de scrape falho.
- Séries antigas podem permanecer consultáveis durante o lookback do backend. Confira saúde e idade da amostra; histórico não prova estado atual.
- p95 de 24 horas usa somente o histórico disponível. Quantis, médias, taxas e contagens derivadas de coleta não são medições de precisão ilimitada. Perdas de amostras, resets e mudanças de configuração afetam a leitura.
- Os totais HTTP foram conferidos em passos de 60, 300 e 900 segundos para a mesma janela alinhada. Bordas de períodos, arredondamento e falta de amostras continuam sujeitos à resolução da coleta. O backend SUSE usa MetricsQL; essas expressões não são portáveis sem adaptação para Prometheus puro.

## Fontes versionadas e aceite de outra versão

- [Métricas KubeVirt v1.7.4](https://github.com/kubevirt/kubevirt/blob/v1.7.4/docs/metrics.md).
- [Coletor de volumes Longhorn v1.11.2](https://github.com/longhorn/longhorn-manager/blob/v1.11.2/metrics_collector/volume_collector.go) e [coletor de backups](https://github.com/longhorn/longhorn-manager/blob/v1.11.2/metrics_collector/backup_collector.go).
- [VM Import Controller v1.8.2](https://github.com/harvester/vm-import-controller/tree/v1.8.2).
- [Semântica MetricsQL](https://docs.victoriametrics.com/metricsql/).
- [Métricas Traefik](https://doc.traefik.io/traefik/observe/metrics/overview/).

Ao atualizar plataforma/Agent, confira HELP/TYPE no endpoint, labels no backend e valores na API de origem. Não estenda automaticamente a validação deste laboratório a outras versões, contratos de instrumentação ou cargas. `scripts/audit-queries.py` cobre execução/filtros; comparação semântica e teste do fluxo operacional também fazem parte do aceite.

O parâmetro `${__interval}` é resolvido pelo SUSE conforme a resolução do gráfico. Referência: [queries representativas](https://documentation.suse.com/cloudnative/suse-observability/latest/en/develop/reference/writing-promql.html). A aceitação direta pelo VictoriaMetrics não comprova compatibilidade com a interface SUSE; execute também a auditoria nativa.
