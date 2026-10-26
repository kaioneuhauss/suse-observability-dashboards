# Vários clusters, sem duplicar dashboards

Cada chart tem três modos:

| Modo | Onde instalar | O que cria |
|---|---|---|
| `all` | Cluster monitorado, namespace do Agent | Coletores e publicadores do módulo |
| `telemetry` | Cada cluster monitorado | Somente os coletores do módulo |
| `content` | Um cluster com acesso à API SUSE | Somente dashboard(s) e monitores |

Aplicações usa apenas `content`, pois a aplicação já fornece suas métricas. Escolha **uma release publicadora por módulo e por instância SUSE**. Instalar `all` novamente em outro cluster faria dois releases administrarem os mesmos objetos externos. Os filtros do dashboard já abrangem todos os clusters que enviam dados.

## Primeiro cluster simples

Siga o guia do módulo com `mode: all` (padrão). O Secret de ingestão e o de publicação precisam existir no mesmo namespace da release.

## Adicionar outro cluster

Use o mesmo chart com o nome da integração desse cluster e `mode: telemetry`. Não precisa levar o token de publicação:

```yaml
mode: telemetry
clusterName: outro-cluster
observability:
  url: https://observability.exemplo.com.br
```

Instale com o kubeconfig/contexto do novo cluster. Para Virtualization, inclua `observability.otlpEndpoint`. A integração aparecerá nos filtros quando houver dados.

## Manter a publicação somente no central

Em cada origem, use `mode: telemetry`. No central, crie um arquivo por módulo:

```yaml
mode: content
observability:
  url: https://observability.exemplo.com.br
```

O namespace central precisa apenas do Secret de publicação. Não precisa do Secret de ingestão, nome do cluster, CA KubeVirt ou OTLP. Exemplo:

```bash
helm upgrade --install obs-virtualization ./charts/suse-observability-virtualization \
  --kubeconfig "$CENTRAL_KCFG" --kube-context "$CENTRAL_CTX" -n "$CONTENT_NS" \
  -f local/virtualization-content.yaml --wait --timeout 15m
```

Esse foi o desenho usado no laboratório para preservar as identidades proprietárias já existentes. Os quatro módulos de conteúdo ficam no central; os coletores ficam nas origens.

## Fleet

Fleet pode administrar cada chart sem dependências externas. No diretório do GitRepo, use um bundle por módulo/destino. Fixe a revisão do seu Git e mantenha values sem credenciais:

```yaml
# fleet.yaml na raiz de um bundle contendo o chart ou apontando para ele no repo
namespace: suse-observability
helm:
  chart: ./charts/suse-observability-traefik
  releaseName: obs-traefik
  values:
    mode: telemetry
    clusterName: meu-cluster
    observability:
      url: https://observability.exemplo.com.br
```

Ajuste o caminho à raiz real do bundle. Use selectors/targets explícitos para impedir publicação em mais de um cluster. Antes de migrar uma release Helm manual para Fleet, confira adoção e propriedade; não crie outra release coletando os mesmos alvos. O teste deste trabalho usou Helm direto; o novo desenho Fleet precisa de aceite no destino.
