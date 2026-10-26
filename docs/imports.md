# Importações VMware com VM Import Controller

Módulo opcional e independente. Publica o dashboard **VMware Imports (VMIC)** e instala um pequeno inventário somente de leitura no Harvester. Não depende do chart Virtualization, não acessa o vCenter e não inicia, desliga, repete ou modifica importações.

## O que você consegue acompanhar

| Informação | Interpretação |
|---|---|
| Registros, ativos, concluídos e falhos | Objetos `VirtualMachineImport` ainda retidos no cluster |
| Fase por importação | Estado gravado pelo controller; fases desconhecidas continuam identificadas como desconhecidas |
| Idade de uma importação ativa | Tempo desde a criação do objeto, incluindo filas e esperas |
| Discos totais, prontos e falhos | Quantidade de objetos de disco; não é porcentagem de transferência |
| Capacidade lógica dos discos | `diskSize` informado pelo controller, em bytes; não é dado já transferido |
| Intervalos registrados | Desligamento → exportação e submissão → prontidão das imagens, quando existem todos os timestamps necessários |
| Saúde e idade do inventário | Confirma que o coletor conseguiu listar os objetos recentemente |

`virtualMachineRunning` significa sucesso segundo o controller. Testes do sistema operacional, rede e aplicação continuam necessários. Não há uma métrica confiável de progresso global, ETA ou duração completa da migração nesse contrato; o dashboard não inventa esses valores. A integração Coriolis ficou fora desta entrega.

## Pré-requisitos

1. [SUSE Observability e Agent](prerequisites.md) funcionando, com integração identificada pelo mesmo `clusterName`.
2. VM Import Controller instalado e sua CRD disponível. Versão validada: **1.8.2**, API `migration.harvesterhci.io/v1beta1`.
3. Permissão para instalar o chart e seu ClusterRole, que permite apenas `list` de `virtualmachineimports`. O coletor não lê Secrets nem os objetos das origens VMware.
4. Acesso às imagens Python e vmagent ou seus espelhos. Não exige a imagem OTel de `dp.apps.rancher.io` nem endpoint OTLP: usa remote write via HTTPS.

Verifique no contexto do Harvester:

```bash
kubectl get crd virtualmachineimports.migration.harvesterhci.io --kubeconfig "$KCFG" --context "$CTX"
kubectl get virtualmachineimports.migration.harvesterhci.io --kubeconfig "$KCFG" --context "$CTX" -A
```

Não instale o módulo em um cluster sem essa CRD. Zero objetos com inventário saudável é válido. CRD ausente ou acesso negado torna o inventário indisponível.

## Instalar

Prepare os Secrets de ingestão e publicação conforme os pré-requisitos comuns. Copie `examples/imports.yaml` para `local/imports.yaml`:

```yaml
clusterName: meu-harvester
observability:
  url: https://observability.exemplo.com.br
```

```bash
helm upgrade --install obs-imports ./charts/suse-observability-imports \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$NS" \
  -f local/imports.yaml --wait --timeout 15m
```

Para manter a publicação centralizada, instale `mode: telemetry` no Harvester e `mode: content` uma única vez no central, conforme [vários clusters](multiple-clusters.md). O módulo não publica monitores automaticamente: uma importação antiga retida como falha não deve gerar paging permanente sem uma política operacional acordada.

## Aceite

```bash
kubectl rollout status deployment/obs-imports-imports --kubeconfig "$KCFG" --context "$CTX" -n "$NS"
kubectl logs deployment/obs-imports-imports --kubeconfig "$KCFG" --context "$CTX" -n "$NS" -c import-inventory --since=5m
```

No Metrics Explorer:

```promql
harvester_import_inventory_up{cluster_name="meu-harvester"}
count(harvester_import_info{cluster_name="meu-harvester"})
sum by (phase,outcome) (harvester_import_info{cluster_name="meu-harvester"})
```

Compare os nomes, fases, contagens de discos e timestamps com os objetos na API. Uma falha de leitura elimina a exposição do inventário antigo e publica `inventory_up=0`; os painéis dependentes também verificam esse sinal. A atualização padrão ocorre a cada 30 segundos. Interrupção completa de envio exige observar a atualidade das amostras, pois o backend pode manter a última série por seu período de lookback.

Os labels exportados são namespace, nome da importação, nome da VM de destino, tipo de origem, fase/resultado e etapa. Senhas, endereços das origens, caminhos de arquivos e mensagens de erro não são exportados. A remoção de um CR elimina esse registro do inventário atual; o histórico de métricas segue a retenção do backend. Revise essa retenção para auditoria de migrações.

Contrato verificado no [código VM Import Controller v1.8.2](https://github.com/harvester/vm-import-controller/tree/v1.8.2). Consulte também os [contratos de métricas](metric-contracts.md).
