# SUSE Observability: guia de estudo da implementação

Versão 6 - laboratório validado em setembro de 2026. Este documento explica as decisões e ensina a evoluir o projeto. Para executar a implantação, use o procedimento de cliente em GUIA-HELM-FLEET.md. Consulte RESULTADOS.md para distinguir testes reais de verificações estáticas.

## 1. O que estamos construindo

Um dashboard apresenta dados; ele não cria os dados. Esta implementação tem quatro etapas: medir na origem, transportar, consultar e interpretar. Um monitor avalia periodicamente uma condição; uma regra de notificação decide quem será avisado. É possível ter um Pod coletor Ready e, ainda assim, nenhum dado chegar ao destino.

O Agent oficial descobre a topologia Kubernetes e coleta recursos dos containers. Os charts complementares acrescentam fontes específicas que não estavam disponíveis com os rótulos e o detalhe necessários. O servidor SUSE Observability recebe as métricas, relaciona recursos à topologia e executa consultas e monitores.

| Origem | Coleta | Transporte | Uso |
|---|---|---|---|
| SO do nó | node-exporter + vmagent | Prometheus remote write | Memória disponível, filesystem, CPU e I/O |
| etcd | vmagent no nó de etcd | Prometheus remote write | Consenso, líder, persistência e quota |
| Traefik | vmagent e inventário de Ingress/Service | Prometheus remote write | Tráfego por aplicação, códigos, duração e certificados |
| API Kubernetes | inventário de Pods | Prometheus remote write | Requests, limits e estado de containers regulares |
| KubeVirt | Prometheus Receiver do Collector OpenTelemetry | OTLP gRPC com TLS | SO convidado, vCPU e disco virtual |
| Aplicação instrumentada | métricas HTTP da própria aplicação | Pipeline já existente no ambiente | Rota, resultado e duração dentro da aplicação |
| Arquivos JSON/STY | Jobs de publicação | API SUSE autenticada | Definições de dashboards e monitores |

Esses caminhos não são intercambiáveis. O token de ingestão não deve receber permissões administrativas; um Service Token de publicação não instala instrumentação na aplicação.

## 2. Por que três charts

Um chart por dashboard repetia a URL, credenciais e processo de publicação. Agora o chart central publica as cinco visões em uma instalação. Os coletores permanecem separados porque executam em lugares diferentes: plataforma em cada cluster; KubeVirt no Harvester; conteúdo uma vez no central.

### sre-platform-telemetry

`templates/collectors.yaml` cria os DaemonSets habilitados para SO e etcd e suas configurações. `templates/traefik.yaml` cria coleta, descoberta e inventário de backend para os clusters que possuem Traefik. `templates/pod-inventory.yaml` fornece o inventário de configurações de Pods. `files/` contém os pequenos exporters de inventário. `templates/test-traefik.yaml` contém o teste de conectividade Helm.

O node-exporter lê /proc, /sys e filesystems do host. Os mounts são somente leitura, mas esse acesso continua sensível. O vmagent realiza scrape periódico, filtra famílias, identifica o cluster/nó e envia dados. A fila local tem limite e não é um arquivo de auditoria durável.

O inventário de Pods usa somente `list pods`, com páginas de 500, teto de 100.000 objetos e validade dos dados. A consulta da API evita a lacuna observada em Pods hotplug. Ele não lê Secrets nem variáveis de ambiente; os requests/limits não são inferidos do consumo.

### sre-kubevirt-telemetry

`templates/_config.tpl` monta a configuração do Collector; `templates/resources.yaml` contém Deployment, ConfigMap, ServiceAccount e RBAC. O Receiver Prometheus descobre EndpointSlices em `harvester-system`, usa a CA interna KubeVirt e valida o SAN de cada serviço. Os processadores limitam memória, acrescentam identificação do cluster e agrupam lotes. O exporter envia OTLP gRPC comprimido ao servidor.

O Collector não modifica as VMs, não instala guest agent e não configura o armazenamento. Alguns indicadores só existem quando a VM fornece estatísticas. A memória observada pelo hipervisor não substitui automaticamente o MemAvailable do Linux convidado.

### suse-observability-content

`dashboards/*.json` contém as cinco definições completas. `monitors/*.sty` contém as regras SUSE. `files/catalog.json` permite selecionar monitores. `files/panel-monitor-coverage.json` liga cada gráfico à orientação operacional. `files/publisher.py` implementa a publicação e a verificação do conteúdo persistido.

Os dois Jobs são hooks `post-install,post-upgrade`, têm prazo máximo, recursos limitados e Service Tokens diferentes. Eles terminam após publicar. Não precisam montar o token Kubernetes do ServiceAccount. Antes de substituir um dashboard, verificam propriedade/identidade e limitam a operação aos objetos gerenciados. A recriação pode alterar IDs; reabra pela lista, não por um bookmark antigo.

Não há Job de SMTP ou notificações. O operador configura SMTP globalmente e associa os monitores a canais pela interface, conforme o procedimento acordado.

## 3. Anatomia de um Helm chart

Um chart é um pacote de templates Kubernetes, valores e metadados. Helm não inventa APIs no destino: se o template usa uma API não instalada, o deploy falha.

```text
meu-chart/
  Chart.yaml          nome, versão do pacote e versão da aplicação
  values.yaml         defaults
  values.schema.json  validações de tipos, enumerações e campos obrigatórios
  templates/          recursos Kubernetes renderizados
  files/              arquivos estáticos usados pelos templates
  config/             valores específicos do ambiente
  fleet.yaml          seleção e configuração quando Fleet gerencia o pacote
```

`Chart.yaml.version` identifica a versão do pacote. `appVersion` é informação da aplicação; não faz upgrade automático de uma imagem. Imagens são escolhidas pelos valores dos templates. Tags podem mudar no registry: valide e fixe digests na produção.

`values.yaml` deve ter defaults compreensíveis. Um arquivo passado por `-f` substitui campos; o último arquivo tem precedência. Por isso, no Fleet, a ordem é defaults primeiro e perfil depois. Não duplique todos os defaults em cada perfil. Evite uma variável para cada detalhe que nunca muda: exponha somente escolhas operacionais necessárias.

Um ConfigMap contém configuração não secreta. Um Secret contém material sensível em base64, que não é criptografia. Não versione tokens, senhas, kubeconfigs ou Secrets preenchidos. Referencie Secrets existentes no namespace em que o Pod será criado.

### Exercício: criar um chart simples

Use um diretório de estudo separado, sem instalar automaticamente no cliente:

```bash
helm create exemplo-telemetria
helm lint ./exemplo-telemetria
helm template exemplo ./exemplo-telemetria > /tmp/exemplo-renderizado.yaml
```

O scaffold cria muitos recursos genéricos. Remova os que não pertencem ao objetivo, revise imagem, probes, recursos, conta de serviço e exposição de rede. Não use o scaffold sem revisão. Para aprender, altere um valor por vez e compare o manifesto renderizado.

Um campo pode ser obrigatório no template:

```yaml
metadata:
  name: {{ .Release.Name }}-config
  namespace: {{ .Release.Namespace }}
data:
  clusterName: {{ required "clusterName is required" .Values.clusterName | quote }}
```

Depois use `values.schema.json` para rejeitar tipos inválidos antes do deploy. `helm template` prova renderização, não conectividade, autenticação, image pull ou funcionamento do backend.

Hooks são úteis para uma ação finita, como publicar conteúdo externo. Kubernetes/Fleet não observam continuamente o objeto criado fora do cluster. Se alguém editar um dashboard no SUSE, o próximo Job pode reaplicar o arquivo; não existe reconciliação contínua da API externa nesta solução. Incremente `lifecycle.revision` em Git para provocar nova publicação quando necessário.

## 4. Configuração por camada

### Servidor central

Instale e dimensione o servidor pela documentação oficial. Configure DNS/TLS, autenticação, retenção, SMTP e a entrada OTLP. O chart de conteúdo utiliza a URL da interface/API; o Collector KubeVirt utiliza o endpoint OTLP gRPC. Não são a mesma rota.

Um fragmento de values de Ingress deve ser acrescentado ao conjunto completo que administra a release do servidor. Não aplique um upgrade apenas com o fragmento e perca sizing, armazenamento ou autenticação. Alterar o servidor pode reiniciar componentes; prepare janela e rollback.

### Clusters RKE2

Confirme primeiro qual ingress controller existe. No Rancher-provisionado, a origem da configuração pode ser `spec.rkeConfig.chartValues.rke2-traefik`. No local/importado, pode ser um HelmChartConfig em kube-system. Edite a fonte correta e preserve campos existentes; não crie dois donos concorrentes.

Traefik precisa expor métricas internamente, com rótulos de serviços. O chart complementar só coleta o endpoint; não habilita o endpoint no processo Traefik. A porta 9100 não precisa ficar pública. Uma NetworkPolicy aditiva só deve ser criada depois de avaliar as políticas existentes: a primeira policy que seleciona um Pod pode isolá-lo.

O coletor etcd lê `127.0.0.1:2381/metrics` no próprio nó. A API de clientes do etcd é outra finalidade. O desenho testado não exige publicar 2379/2381 na rede externa. Confirme endpoint e seleção dos nós antes de habilitar a opção; não copie rótulos de outro cliente sem inspeção.

### Harvester

Harvester inclui KubeVirt e outros componentes que não existem em um cluster de aplicações comum. Mantenha Traefik desligado quando o ambiente usa NGINX. Instale o Agent pelo processo compatível com a versão, evitando duplicar o add-on e uma release manual.

A CA KubeVirt é pública; copiá-la não fornece chave privada. Ela permite verificar a identidade do endpoint. Sua rotação exige atualizar a cópia e recriar o Pod do Collector. Confiar no certificado no Chrome não configura a confiança do container.

O Secret de registry autentica o download da imagem. O Secret de ingestão autentica o envio de métricas. São credenciais com funções e ciclos de vida diferentes.

## 5. Como escolher métricas

Comece pela pergunta que alguém precisa responder. “A aplicação está atendendo bem?” pede tráfego, erros e duração. “Por que ficou lenta?” pede correlação com saturação, filas, CPU, memória, disco e dependências. CPU alta sem erro ou latência não é, sozinha, indisponibilidade.

Os quatro sinais do Google SRE são latência, tráfego, erros e saturação. RED aplica Rate, Errors e Duration a serviços. USE organiza Utilization, Saturation e Errors por recurso. São formas de organizar perguntas; não são uma lista universal de gráficos obrigatórios.

| Tipo | Interpretação | Operações comuns |
|---|---|---|
| Counter | Total acumulado, pode reiniciar com o processo | rate/increase, depois agregação |
| Gauge | Estado observado: bytes livres, fila, réplicas | valor atual, max/min, tendência |
| Histogram | Contagens acumuladas por faixas de duração | rate dos buckets, agregação por le, histogram_quantile |

Nunca use o valor bruto de um counter como “requisições hoje”. Não calcule média de percentis entre réplicas. Para p95 conjunto, agregue os buckets compatíveis, preservando `le`, antes de calcular o percentil.

A média é soma das durações dividida pelo número de chamadas. Poucas chamadas extremamente lentas podem elevá-la acima do p95; isso não é matematicamente impossível. Já p50 maior que p95 para a mesma distribuição exige investigar consulta, séries ou apresentação.

Rótulos são dimensões, não texto livre. Cluster, namespace, serviço, rota normalizada e status HTTP costumam ser úteis. Request ID, usuário, URL completa e mensagens de exceção pertencem a logs/traces; como labels, podem multiplicar séries sem controle.

## 6. Como construir um dashboard neste projeto

1. Escolha a pergunta e a fonte. Consulte a métrica real na instância, veja rótulos, unidade e frequência. Compare uma amostra com kubectl, endpoint bruto ou SO.
2. Teste a consulta no Metrics Explorer para Everything, um cluster e um namespace. Confirme que um cluster inexistente não ganha um falso zero.
3. Abra um dashboard de estudo na interface, adicione o widget e escolha unidade/título. Exporte a definição com a mesma versão da CLI usada no ambiente.
4. Use uma definição existente em `dashboards/` como referência de schema. Preserve o formato JSON; nesta base, converter para YAML podia transformar a chave `y` em booleano.
5. Adicione o painel e sua referência ao layout. Confira x/y/width/height, sobreposição, altura do texto e legibilidade em resolução de trabalho.
6. Dê um nome curto e inglês claro. No “?”, explique o que mede, unidade, janela, escopo, fonte, quando investigar e limitações. “Average response time” é mais didático que “mean latency”.
7. Cadastre a cobertura em `panel-monitor-coverage.json`. Nem todo gráfico precisa gerar alerta; declare quando é apenas contexto.
8. Execute os testes, renderize o chart e publique em canário. Exporte novamente e compare a definição persistida, não apenas a mensagem de sucesso do comando.
9. Confira cada gráfico e filtro no navegador. API correta não garante legenda correta, nome legível ou layout sem vazios.

### Filtros e valores temporários

A variável usa Everything com regex `.*`; as consultas usam `=~`. O rótulo consultado deve existir naquela fonte: `cluster_name` no remote write pode corresponder a `k8s_cluster_name` após OTLP. Não basta trocar o nome visual do filtro.

Filtros dependentes precisam ser redefinidos depois de trocar o cluster. O backend de aplicações pode ter nome diferente do serviço instrumentado. O inventário de Ingress resolve a relação entre identificador interno Traefik e namespace/Service Kubernetes.

`saveVariables=false` evita persistir seleções exploratórias no dashboard. Alterar layout ou query continua sendo edição real. Esta opção não transforma um dashboard editável em modo somente leitura.

### Período e estimativas

Os totais acompanham o seletor superior com incrementos de um minuto e passo fixo. A implementação usa recursos do backend da versão validada; não é PromQL universal. Veja REFERENCIA-OPERACIONAL.md para a expressão exata e sua portabilidade.

Uma chamada não é amostrada individualmente pelo Prometheus: o contador é observado a cada scrape. Uma série criada já com valor 100 não tem uma amostra anterior que permita reconstruir aqueles 100 eventos. Faça aquecimento e linha de base em testes. Números sem K/M melhoram a leitura, mas não tornam a estimativa um registro de auditoria.

### Limitação gráfica identificada

No SUSE 2.10.2 testado, nomes de legendas podiam ser ordenados sem reordenar os índices da coluna Last. A solução remove essa coluna numérica, mantém nomes abaixo e preserva curvas/tooltips. Não “corrija” o valor da métrica para compensar um problema visual. Reavalie a coluna ao atualizar o produto.

## 7. Como validar CPU, memória e disco

CPU de Pod soma os containers regulares medidos. Um núcleo equivale a 1000 mCPU. Request é reserva para agendamento; limit é teto; uso é consumo medido. Um Pod com dois containers não deve ser contado duas vezes no card de configurações ausentes.

Working set de memória inclui mais que heap da JVM. RSS, working set, cache recuperável, MemAvailable e memória configurada da VM respondem a perguntas diferentes. Compare tempos próximos: leituras do kubelet, scrape e ingestão são assíncronas. Diferencie GB decimal de GiB binário.

No Harvester, o SO do host, virt-launcher/QEMU e SO convidado são camadas distintas. Uma VM configurada com 4 GiB pode mostrar MemTotal menor dentro do Linux. O valor reservado pelo Kubernetes não é a quantidade que a aplicação está consumindo.

Filesystems devem preservar dispositivo, tipo e mount relevante. Bind mounts não são capacidade adicional. /dev/loop0 pode representar um sistema imutável e não o volume que crescerá com os dados. Observe partições operacionais sem esconder a capacidade de dados do Harvester.

PV/PVC informa capacidade provisionada e binding. Uso real de filesystem depende do kubelet/CSI/guest agent. Um volume Block não tem percentual de filesystem aplicável. Capacidade provisionada, consumo do guest e espaço físico Longhorn com réplicas/snapshots não são equivalentes.

CPU scheduler delay do KVM indica espera para executar; não use automaticamente o nome VMware CPU Ready. Latência média de I/O divide tempo acumulado por operações concluídas. Disco sem operações não tem média de latência definida. A fila ponderada do host e a fila de disco virtual não são necessariamente a mesma medida.

## 8. Como criar e encaminhar um monitor

Copie uma regra semelhante em `monitors/` e crie um identifier estável. Defina query, comparação, limiar, janela, severidade, recurso da topologia e remediation. Acrescente o mesmo conteúdo ao catálogo. O teste de consistência evita publicar uma query enquanto a documentação descreve outra.

O `urnTemplate` precisa resolver um objeto existente. Um monitor pode executar sem erro e ainda produzir UNMAPPED se o identifier do Service estiver errado. Verifique avaliação agendada e associação, não só importação.

Para erros HTTP, esta base exige proporção acima de 5% e volume mínimo de 100 chamadas por janela, durante amostras observadas de cinco minutos. O mínimo evita que uma única chamada gere um alerta de 100%. As regras usam janelas próprias; o seletor do dashboard não muda a avaliação do monitor. Lacunas de dados reduzem o que a janela comprova; disponibilidade da coleta deve ser analisada separadamente.

Um limiar deve indicar ação. Considere baseline, objetivo do serviço, horário, replicação e impacto. Disk latency de 20 ms é um ponto inicial, não um SLA universal para SSD, disco mecânico e armazenamento remoto. Alertas nativos já cobrem diversas falhas de Pods; duplicá-los pode produzir ruído.

Com SMTP global configurado, crie uma notificação manual filtrada pelos monitores ou pela tag `sre-dashboards`. Selecione Critical e, quando necessário, Deviating. Teste o canal e depois um incidente controlado. O e-mail padrão “Ye Component” é fictício. O aceite real exige recurso correto, mensagem de abertura e recuperação recebida.

A mesma falha pode ser observada na aplicação e no ingress. No laboratório os dois alertas foram intencionais para validar camadas. No cliente, escolha roteamento, agrupamento e responsabilidade para evitar acionamentos duplicados. Não altere etcd, disco ou memória para forçar falhas sem plano de exercício aprovado.

## 9. Segurança, custo e desempenho

Permissões mínimas reduzem superfície, mas não tornam uma integração sem risco. HostNetwork e leitura da raiz do nó são acessos sensíveis. Revise admission policies, portas, TLS, egress e segredos; não abra uma exceção global de segurança para instalar um coletor.

Use allowlists de famílias e retenção proporcional à necessidade. A taxa de ingestão cresce aproximadamente com séries ativas divididas pelo intervalo de scrape; histogramas multiplicam séries pelos buckets e combinações de rótulos. Rotas dinâmicas, novos Pods e discos podem alterar essa ordem de grandeza.

Requests e limits reservam/capam recursos, mas limites pequenos podem causar throttling, OOM ou descarte de telemetria. O modo `observe` desta base não aplica os limites opcionais de amostras/séries; eles precisam de baseline antes de `enforce`, pois excedê-los pode falhar um scrape inteiro.

Filas são buffers finitos. A fila vmagent é medida em bytes; a fila OTel em requests. Reinício, falta de disco, expiração de retry ou limite de memória podem perder dados. Alertas que dependem do próprio servidor não substituem uma sonda externa para indisponibilidade do servidor.

Veja IMPACTO-E-SEGURANCA.md para a medição no laboratório. Ela não prova impacto zero nem inclui uma comparação A/B sem coletores. Faça canário e compare janelas representativas antes de ampliar. Consulte o sizing oficial do servidor para crescimento de ingestão, consultas e retenção.

## 10. Como evoluir com segurança

1. Faça uma mudança pequena e registre a hipótese, efeito esperado e rollback.
2. Valide origem e consulta antes da estética.
3. Execute testes de regressão e Helm render/lint; teste políticas no destino.
4. Instale em canário, observe logs, filas, perda de amostras, uso de recursos e fontes.
5. Compare definições persistidas e GUI; teste filtros e períodos.
6. Para alerta novo, valide topologia, conteúdo, abertura, recuperação e destinatário.
7. Versione apenas arquivos públicos essenciais e informe diferenças/limites no changelog.
8. Mantenha responsável por imagens, tokens, CAs, thresholds e compatibilidade de versões.

Dashboards são parte de uma operação SRE. SLOs, orçamentos de erro, probes externos, traces/logs, restauração de backups, escalonamento e resposta a incidentes precisam de decisão do cliente. A existência de uma métrica em outra ferramenta não basta para justificar custo e alerta adicional.

## Referências de estudo

- SUSE dashboards: https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/dashboards/dashboards.html
- SUSE monitores: https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/alerting/k8s-add-monitors-cli.html
- SUSE permissões: https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/setup/security/rbac/rbac_permissions.html
- SUSE notificações: https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/use/alerting/notifications/configure.html
- Helm estrutura e práticas: https://helm.sh/docs/chart_best_practices/
- Fleet: https://fleet.rancher.io/0.15/reference/ref-fleet-yaml
- Prometheus práticas de instrumentação: https://prometheus.io/docs/practices/instrumentation/
- Google SRE, quatro sinais: https://sre.google/sre-book/monitoring-distributed-systems/
- Grafana, RED: https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/
- Datadog, métricas para monitoramento: https://www.datadoghq.com/blog/monitoring-101-collecting-data/

As versões e evidências exatas do laboratório estão em RESULTADOS.md. As fontes orientam o desenho; não certificam automaticamente os charts customizados.

### Como interpretar os Pods próximos do limite

Os gauges destacam o maior percentual. Para CPU e memória, há uma contagem de Pods acima de 80% do limite e, logo abaixo, a lista somente desses Pods. Uma contagem zero significa que nenhum Pod elegível passou do limiar; falta de dados não é convertida em estado saudável. Apenas Pods com uso e limites positivos em todos os containers regulares são elegíveis. A média é de cinco minutos no fim do período selecionado.

Outros dois gráficos selecionam os cinco maiores consumidores absolutos de CPU (mCPU) e memória (bytes), independentemente de estarem acima de 80%. O grupo é escolhido no fim do período; as curvas mostram seu consumo real ao longo do tempo. Requests e limits dos mesmos Pods ajudam a comparar uso e configuração. Um Pod com 17,5% pode aparecer neste ranking, mas não na lista acima de 80%.

A versão 2.10.2 oferece gráficos de linha, barra, número, gauge e texto nos dashboards, sem widget de tabela nativa. As listas de estado foram compactadas e receberam um link para a consulta no Metrics Explorer. Ative **Table view** para ler nomes e valores em colunas. A tabela exibe o valor bruto da consulta: nos percentuais de limite, 0,8 equivale a 80% e 0,98 equivale a 98%. O link transporta os filtros; para investigar o passado, selecione novamente o período no Explorer. A coluna Last da legenda foi retirada por um defeito de associação entre nomes e valores nessa versão.

80% é um ponto para investigar, não uma recomendação automática de aumentar recursos. CPU requer correlação com throttling e latência; memória requer verificar RSS, cache, crescimento e OOM. Os monitores mantêm suas próprias janelas e critérios. O card de histórico limitado a 24 horas foi removido: confundia uma amostragem limitada com a retenção total do produto.

## Comparar um benchmark curto com o dashboard

O navegador calcula a taxa durante a execução do teste. O cálculo de taxa recente (retirado do dashboard para simplificar a leitura) calcula o incremento entre as duas últimas coletas, normalmente 30 segundos. Após o teste, duas coletas sem chamadas novas fazem essa taxa voltar a zero. A média de cinco minutos ainda inclui o teste. Exemplo: 200 chamadas em 1,49 segundo equivalem a cerca de 134 req/s no navegador, 6,67 req/s se concentradas em um intervalo de coleta de 30 segundos, e 0,67 req/s na janela de cinco minutos. Esses números medem janelas diferentes.

Para testar contagens: use uma aplicação de teste, faça uma chamada inicial para cada rota/método/código que será exercitado, aguarde pelo menos duas coletas e a ingestão, registre os counters, execute o teste e aguarde a ingestão antes de comparar os deltas. Uma série nova que aparece inicialmente com valor 10 não prova em qual instante essas dez chamadas aconteceram; `rate`/`irate` não podem reconstruir um incremento sem amostra anterior. Não faça esse aquecimento com falhas em aplicações de cliente; limite-o à aplicação de teste. Para hora e quantidade exatas de cada request, use access logs/traces. O p95 do histograma também é uma estimativa por faixas, não o percentil exato calculado pelo navegador.
