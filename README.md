# Dashboards para entender seu ambiente no SUSE Observability

Descubra **o que está acontecendo, onde investigar e se ainda há capacidade**. São nove dashboards nativos em cinco módulos independentes, cada um com seu próprio Helm chart. Instale apenas o que usa.

Os dashboards ficam **em inglês**, com títulos diretos e explicações sobre cada gráfico. Este passo a passo está em português. Não precisa de Grafana, servidor Perses, Python local ou geração de arquivos para instalar.

## Escolha o que precisa

| Você quer acompanhar… | Módulo | Dashboards no SUSE | Preparação específica |
|---|---|---|---|
| VMs e hosts Harvester / SUSE Virtualization | `virtualization` | **VM & Host Overview**, **VM Performance**, **Capacity Planning**, **Storage & Backups** | [Virtualization](docs/virtualization.md) |
| Importações VMware pelo VM Import Controller | `imports` | **VMware Import Progress** | [Imports](docs/imports.md) |
| Requisições que passam pelo Traefik | `traefik` | **Incoming Traffic & Errors** | [Traefik](docs/traefik.md) |
| Requisições medidas dentro das aplicações | `applications` | **Traffic, Errors & Speed** | [Aplicações](docs/applications.md) |
| Saúde de Kubernetes/RKE2 e uso de recursos | `kubernetes` | **Cluster Health**, **Application Resource Usage** | [Kubernetes](docs/kubernetes.md) |

**Exemplo:** você tem SUSE Observability e Harvester, mas não tem Traefik nem aplicações instrumentadas. Instale somente `virtualization` no Harvester. Para acompanhar importações VMware, acrescente `imports`. Nenhum desses módulos exige os outros.

Cada visão responde uma pergunta:

- **Visão geral:** minhas VMs e hosts estão ficando sem CPU, memória ou espaço?
- **Performance:** a VM espera CPU, usa swap ou aguarda o disco?
- **Capacidade:** quanto foi atribuído às VMs e quanto ainda está disponível?
- **Storage e backups:** quais volumes precisam de atenção e quais backups estão registrados?
- **Importações:** quais terminaram, falharam ou continuam em processamento?
- **Traefik e aplicações:** onde estão os erros e quais requisições estão lentas?
- **Kubernetes:** há servidores indisponíveis, aplicações sem réplicas ou recursos mal dimensionados?

Veja o [guia dos 161 painéis](docs/panel-guide.md) e o [guia de Virtualization](docs/virtualization-dashboards.md). Os temas de Virtualization foram inspirados no [harvester-extra-dashboards, de doccaz](https://github.com/doccaz/harvester-extra-dashboards); aqui usamos o formato nativo do SUSE.

## Antes de começar — uma vez por ambiente

Você precisa de:

1. **SUSE Observability funcionando** e sua URL HTTPS. Este projeto adiciona conteúdo a uma instalação existente.
2. **Agent oficial no cluster monitorado**, com métricas chegando ao SUSE. O cluster que publica somente conteúdo não precisa desse Agent.
3. **Acesso ao cluster:** kubeconfig, contexto e namespace do Agent.
4. **kubectl e Helm** no computador. Procedimento executado com kubectl 1.35.2 e Helm 4.1.1; o CI também verifica os charts com Helm 3.
5. **Secret de publicação** para criar dashboards/monitores. A ingestão reutiliza o Secret do Agent.
6. O pré-requisito do módulo: por exemplo, métricas habilitadas no Traefik ou endpoint OTLP e acesso às imagens no Virtualization.

**Falta configurar algum item?** Siga [Preparar o ambiente, do acesso aos Secrets](docs/prerequisites.md). O guia explica ferramentas, kubeconfig, namespace, Agent, tokens e verificações. Depois, leia o guia específico da tabela acima.

## Instalar — exemplo completo para Harvester

Execute os comandos no seu computador, em um terminal Bash. Substitua os exemplos pelos dados do ambiente. Nunca coloque senhas ou tokens em YAML.

### 1. Baixar o projeto

```bash
git clone https://github.com/kaioneuhauss/suse-observability-dashboards.git
cd suse-observability-dashboards
```

Use a raiz do projeto nos próximos comandos. Os charts já vêm prontos.

### 2. Informar onde instalar

```bash
export KCFG=/caminho/harvester.yaml
export CTX=harvester
export NS=suse-observability
export OBS_URL=https://observability.exemplo.com.br
export OTLP_ENDPOINT=otlp-observability.exemplo.com.br:443
```

`KCFG` é o arquivo de acesso. `CTX` escolhe o cluster dentro dele. `NS` é o namespace existente onde estão Agent e Secrets. `OBS_URL` é a interface/API SUSE. `OTLP_ENDPOINT` é um endereço separado de ingestão gRPC, necessário somente para Virtualization.

### 3. Criar a configuração mínima

```bash
bash scripts/pack.sh configure virtualization local/virtualization.yaml all
```

O comando lê o nome da integração do ConfigMap do Agent e grava um arquivo sem credenciais. **Não sobrescreve arquivos existentes.** Confira o resultado:

```yaml
mode: all
clusterName: meu-harvester
observability:
  url: https://observability.exemplo.com.br
  otlpEndpoint: otlp-observability.exemplo.com.br:443
```

Se os Secrets diferem do padrão ou Longhorn está isolado por NetworkPolicy, acrescente as opções do [guia Virtualization](docs/virtualization.md). Não habilite uma nova política sem revisar o isolamento existente.

### 4. Conferir e instalar

```bash
bash scripts/pack.sh check virtualization local/virtualization.yaml
bash scripts/pack.sh install virtualization local/virtualization.yaml
```

`check` valida os values, renderiza o chart e faz dry-run de admissão sem instalar recursos. `install` repete essas verificações, instala a release `obs-virtualization` e aguarda os recursos/publicadores. Jobs hooks são substituídos pelo Helm e não entram no dry-run de `apply`.

Resultado esperado: `STATUS: deployed`, Pods prontos e Jobs publicadores concluídos. Isso comprova a instalação; a entrega de métricas precisa da próxima etapa.

### 5. Abrir e conferir

1. No SUSE, abra **Dashboards** e procure **Virtualization**.
2. Abra **VM & Host Overview** e selecione seu cluster.
3. Compare **Running VMs** com as instâncias em execução no Harvester. A contagem aparece sem casas decimais.
4. Em **Can we collect VM and storage metrics?**, confira os alvos esperados com valor `1`.
5. Teste os filtros e compare CPU, memória e filesystem de uma VM conhecida.
6. Abra as demais visões. Dados vazios exigem verificar fonte, filtros e pré-requisitos; não significam automaticamente zero ou saudável.

Aguarde alguns ciclos de coleta. Taxas de cinco minutos e estatísticas de 24 horas precisam de histórico suficiente. Consulte [validação e problemas comuns](docs/validation.md).

## Instalar outro módulo

Aponte as variáveis para o cluster correto, cumpra o pré-requisito específico e troque o nome do módulo:

```bash
bash scripts/pack.sh configure traefik local/traefik.yaml all
bash scripts/pack.sh install traefik local/traefik.yaml
```

Para `applications`, o comando escolhe `content`, pois não há novo coletor. Você também pode copiar os arquivos em `examples/` e usar Helm diretamente, conforme cada guia.

**Mais de um cluster:** publique cada módulo uma única vez por instância SUSE. Use `all` no primeiro cluster e `telemetry` nos demais, ou centralize os publicadores em `content`. Siga [vários clusters](docs/multiple-clusters.md). Se Virtualization já coleta hosts no Harvester, Kubernetes deve usar `content`, evitando coleta duplicada.

## Verificar, atualizar ou remover

```bash
# Ver a instalacao e seus Pods/Jobs
bash scripts/pack.sh status virtualization

# Aplicar novamente a configuracao, inclusive depois de atualizar o projeto
bash scripts/pack.sh install virtualization local/virtualization.yaml

# Remover SOMENTE o modulo no destino KCFG/CTX/NS
bash scripts/pack.sh remove virtualization
```

A remoção salva values/manifests em `local/backups/`, exclui o conteúdo externo do módulo quando aplicável e desinstala seus coletores. **Servidor SUSE, Agents oficiais, aplicações, VMs, volumes e Secrets compartilhados ficam preservados.** O histórico de métricas segue a retenção do SUSE.

Para reinstalar, execute `install` com o mesmo arquivo. Para remover outro módulo, troque seu nome. Em vários clusters, remova os coletores em cada origem e o conteúdo uma vez no publicador. Use a mesma versão do chart instalado para a remoção. [Remoção detalhada, migração e rollback](docs/lifecycle.md).

## Documentação

| Documento | Para que serve |
|---|---|
| [Pré-requisitos](docs/prerequisites.md) | Preparar ferramentas, acessos, Agent, Secrets e rede |
| [Vários clusters](docs/multiple-clusters.md) | Separar coletores e publicação sem duplicação |
| [Guia dos painéis](docs/panel-guide.md) | Entender o que cada gráfico mostra |
| [Validação](docs/validation.md) | Conferir instalação e dados; resolver problemas comuns |
| [Contratos das métricas](docs/metric-contracts.md) | Fórmulas, unidades e limites de interpretação |
| [Validação do laboratório](docs/lab-validation.md) | Versões, testes realizados e limites reais |
| [Desenvolvimento](docs/development.md) | Alterar fontes, gerar charts e executar testes |

São 34 monitores: Virtualization 5, Traefik 6, aplicações 2 e Kubernetes 21. Imports é informativo. Ajuste limites ao serviço; notificações exigem canal, regra e teste próprios. Integração comunitária, sem promessa de suporte oficial da SUSE.
