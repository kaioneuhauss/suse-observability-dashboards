# Dashboards independentes para SUSE Observability

Instale somente o que existe no seu ambiente. Cada módulo tem **seu próprio Helm chart**, dashboard(s) e, quando necessário, coletores e monitores. Não depende dos outros módulos.

| Seu ambiente | Chart | Conteúdo | Procedimento |
|---|---|---|---|
| SUSE Virtualization / Harvester | `suse-observability-virtualization` | 4 dashboards: visão geral, contenção, capacidade e proteção; 5 monitores | [Virtualization](docs/virtualization.md) |
| Importações VMware → Harvester | `suse-observability-imports` | Fases, falhas, discos e tempos registrados pelo VM Import Controller | [Imports](docs/imports.md) |
| Traefik | `suse-observability-traefik` | Tráfego, erros, p95/p99, conexões e TLS; 6 monitores | [Traefik](docs/traefik.md) |
| Aplicações com métricas HTTP | `suse-observability-applications` | RED, disponibilidade por requisição e orçamento de erro; 2 monitores | [Aplicações](docs/applications.md) |
| Kubernetes / RKE2 | `suse-observability-kubernetes` | Hosts, workloads, recursos, PVCs e etcd opcional; 21 monitores | [Kubernetes](docs/kubernetes.md) |

Precisa apenas de Virtualization? Instale somente esse chart no Harvester. Ter SUSE Observability é o pré-requisito comum; o módulo de VMs também exige um cluster Harvester monitorado. Não instale coletores de VMs nos guests.

## O que os dashboards ajudam a decidir

- **Virtualization:** localizar espera de CPU e I/O, avaliar memória do guest e host, comparar demanda com recursos configurados e revisar saúde e proteção dos volumes.
- **Imports:** acompanhar os registros de importação VMware do VM Import Controller, sem confundir discos prontos com porcentagem de transferência.
- **Traefik:** investigar tráfego, falhas HTTP, cauda de latência e conexões por entrada/backend.
- **Aplicações:** correlacionar requisições, erros, latência e consumo do orçamento de erro com a instrumentação existente.
- **Kubernetes:** acompanhar disponibilidade de workloads, pressão nos hosts, requests/limits, PVCs, etcd e a própria coleta.

São **nove dashboards em cinco módulos independentes**. O [guia dos dashboards de Virtualization](docs/virtualization-dashboards.md) descreve cada visão, seus filtros e limites. A organização dos temas de Virtualization foi inspirada no [harvester-extra-dashboards, de doccaz](https://github.com/doccaz/harvester-extra-dashboards); os painéis aqui usam o formato nativo do SUSE Observability.

## Instalação rápida

1. Tenha o **SUSE Observability e o Agent oficial funcionando**. Prepare uma vez os [acessos de ingestão e publicação](docs/prerequisites.md).
2. Escolha o módulo e copie seu arquivo de exemplo.
3. Preencha nome da integração e URL. Para Virtualization, preencha também o endpoint OTLP.
4. Execute Helm no cluster monitorado e no namespace do Agent.

```bash
git clone https://github.com/kaioneuhauss/suse-observability-dashboards.git
cd suse-observability-dashboards
mkdir -p local
cp examples/virtualization.yaml local/virtualization.yaml
```

Exemplo de `local/virtualization.yaml`:

```yaml
clusterName: meu-harvester
observability:
  url: https://observability.exemplo.com.br
  otlpEndpoint: otlp-observability.exemplo.com.br:443
```

Com os Secrets preparados no namespace e os pré-requisitos do módulo atendidos:

```bash
export KCFG=/caminho/harvester.yaml
export CTX=harvester
export NS=suse-observability
helm upgrade --install obs-virtualization ./charts/suse-observability-virtualization \
  --kubeconfig "$KCFG" --kube-context "$CTX" --namespace "$NS" \
  --values local/virtualization.yaml --wait --timeout 15m
```

Os charts já estão prontos. A instalação não precisa de Python local, geração de YAML, Grafana, servidor Perses ou `helm dependency build`. `sts` é executado dentro dos Jobs de publicação; um administrador pode precisar dele uma vez para criar o Service Token.

**Mais de um cluster:** publique cada módulo **uma única vez por instância SUSE**. O primeiro pode usar `mode: all`; os demais usam `mode: telemetry`. Também é possível manter todos os publicadores no cluster central usando `mode: content`. [Exemplos completos](docs/multiple-clusters.md).

## Verificar, atualizar e remover

- [Aceite e solução de problemas](docs/validation.md): Pods prontos, Jobs concluídos, métricas recentes, filtros, alertas e limites do teste.
- [Migração e remoção](docs/lifecycle.md): limpeza restrita aos objetos do módulo, preservação das plataformas e rollback.
- [Contratos de métricas](docs/metric-contracts.md): unidades, fórmulas, dados ausentes e limites de precisão.
- [Validação deste laboratório](docs/lab-validation.md): versões e evidência efetivamente coletadas.
- [Desenvolvimento](docs/development.md): fontes compartilhadas, testes e criação dos charts.

Os painéis permanecem em inglês, com descrições de unidades, janelas e interpretação. As instruções estão em português. Os limites de alerta são pontos iniciais; ajuste-os ao SLO e ao comportamento do serviço. Notificações precisam de canal, regra e teste próprios.

Integração comunitária, não um produto ou compromisso de suporte da SUSE. Não instala nem atualiza o SUSE Observability, o Agent, o Traefik ou o Harvester.
