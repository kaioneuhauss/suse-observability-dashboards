# Impacto: resumo para planejamento

Medições do laboratório em 11/09/2026. A amostragem dos coletores durou aproximadamente 4,5 minutos. Use os valores para preparar um piloto, não como garantia de pico ou sizing de produção.

## Quanto os coletores utilizaram

| Cluster | CPU média adicional | Maior memória amostrada | Requests CPU / RAM |
|---|---|---|---|
| Observability, 6 nós | 30 mCPU | 268,7 MiB | 180m / 568Mi |
| Rancher, 3 nós | 21,4 mCPU | 269,6 MiB | 120m / 400Mi |
| Harvester, 1 nó | 18,3 mCPU | 192,1 MiB | 65m / 360Mi |

Total: 23 Pods de coleta. CPU média somada: **69,7 mCPU**. Soma dos maiores usos de memória por cluster: **730,4 MiB**, não necessariamente um pico simultâneo. `1000 mCPU = 1 núcleo`. As reservas do scheduler são os requests, não o uso médio. Todos os componentes têm requests e limits; os publicadores são Jobs temporários.

## Preciso aumentar o servidor ou storage?

Não há baseline controlado anterior à primeira instalação. A variação histórica do servidor não pode ser atribuída apenas a este projeto. Comece pelo [sizing oficial SUSE](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/requirements.html) e meça um canário com carga representativa.

Os charts não criam PVCs. Novas métricas usam o armazenamento existente do SUSE. No laboratório, cerca de 6101 séries a cada 30s representam aproximadamente 203 amostras/s. Para 30 dias, uma simulação de 2 a 8 bytes/amostra resulta em **0,98 a 3,93 GiB** de dados/índices adicionais, antes de margens, compaction e réplicas. Isso é cenário de planejamento, não garantia de compressão.

O volume de métricas tinha aproximadamente 0,94 GiB em uso. Kafka tinha aproximadamente 38,4 GiB e cresceu cerca de 6 GiB na janela de 24h observada; seus tópicos de saúde/correlação precisam de análise separada. Não extrapole essa taxa indefinidamente nem altere retenção interna para “otimizar dashboards”.

As filas temporárias também precisam de espaço nos nós durante falhas do destino. Os vmagents têm até 1 GiB de fila por instância; estavam vazias na medição. Não são armazenamento durável e podem perder dados após saturação ou substituição do Pod.

## O que já reduz o impacto

Coleta a cada 30s, allowlists de métricas, filas e lotes limitados, seleção de fontes realmente existentes e fim automático dos Jobs. Preservamos TLS e limites de recursos. Montagens read-only de host e host networking exigem análise das políticas de segurança do cliente.

## Aceite simples no cliente

1. Meça CPU/RAM, ingestão, consultas e uso de PVCs antes do projeto.
2. Instale em um cluster canário e compare a mesma carga e janela.
3. Verifique ausência de OOM, descartes, filas crescentes e scrapes atrasados.
4. Acompanhe 24h, sete dias e um ciclo de retenção; considere réplicas e snapshots físicos.
5. Expanda recursos se a evidência indicar. Não reduza reservas com base numa amostra curta.

Os [números completos, fórmulas e limites](details/MEASUREMENTS.md) ficam na referência técnica. Não foi demonstrado impacto zero em qualquer ambiente.
