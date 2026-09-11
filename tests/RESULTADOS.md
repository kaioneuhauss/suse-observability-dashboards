# Validação da versão 6 — 11/09/2026

## Ambiente e alcance

Testes executados no laboratório existente, com SUSE Observability 2.10.2, CLI 3.3.6, Helm 4.1.1 e Helm 3.19.0. Clusters: Observability (6 nós, RKE2 1.34.9), Rancher (3 nós, RKE2 1.35.5), Harvester (1 nó, Kubernetes 1.35.7). Traefik 3.7.1 e 3.6.12 nos dois clusters RKE2; Harvester usa NGINX e não deve aparecer no filtro Traefik.

Esta é evidência de laboratório, não certificação SUSE nem homologação de outro cliente. As medições mudam com o tempo. Não foi realizada uma instalação de SUSE Observability do zero.

## Correções confirmadas

- O parser YAML do Helm alterava a chave `y` do layout para `true`. As cinco definições agora usam JSON preservado e comparação integral após publicação.
- Filtros temporários não são persistidos (`saveVariables=false`). Alterar filtros e sair deixou de exigir salvar nos fluxos testados. Editar widgets, posições ou definições continua sendo alteração real.
- A coleta do Traefik no Rancher estava bloqueada por NetworkPolicy. A liberação foi restrita aos coletores e à porta de métricas. Os seis endpoints Traefik ficaram saudáveis.
- A allowlist do KubeVirt descartava métricas de espera de CPU, paginação, swap e disco. Foi ampliada com seleção explícita de famílias.
- O inventário original não expunha requests/limits de três Pods hotplug do Harvester. O novo inventário consulta somente Pods, com RBAC de leitura, paginação, validade dos dados e limite de objetos.
- Bind mounts de um mesmo dispositivo não são somados como discos distintos. A visão operacional exclui boot, OEM, runtime e mounts do kubelet; métricas brutas e monitores continuam cobrindo outros filesystems graváveis.
- Cards maiores, títulos curtos, identificação de Pods/workloads, unidades e descrições de interpretação; HTTP 4xx e 5xx separados por aplicação, código e janela temporal.

## Código, charts e Fleet

- 29 testes automatizados passaram: publicação, ownership, rejeição de operação insegura, restauração limitada, normalização de definição, coordenadas, parser de recursos Kubernetes, paginação e consistência entre catálogo, STYs e cobertura dos painéis.
- `helm lint --strict` e `helm template` reais passaram para os três charts e os cinco perfis, com Helm 3 e 4. Casos negativos rejeitaram intervalo de scrape inadequado, NetworkPolicy sem confirmação, remoção sem confirmação, monitor inexistente e batch inválido.
- Os três bundles foram empacotados com Fleet CLI 0.15.4 e os valores extraídos foram renderizados. É necessário informar `values.yaml` antes do perfil em `valuesFiles`; sem isso, o empacotamento podia perder os defaults.
- Um Bundle Fleet canário, com publicador em modo `plan`, convergiu Ready 1/1 no cluster selecionado. Os dois Jobs terminaram. O Bundle e Jobs temporários foram removidos.
- O teste Fleet não comprova leitura da branch pelo GitRepo: a branch v6 ainda precisa ser publicada. Não use Helm manual e Fleet para gerenciar simultaneamente a mesma release.
- Publicação real central: 5 dashboards e 33 monitores verificados pela API. Os 38 monitores nativos e o dashboard nativo Kubernetes Cluster foram preservados. Helm 3 também executou upgrade real.

## Coletores e fontes

Na verificação de encerramento, os 23 Pods de coleta estavam Ready, com zero reinícios. Quarenta logs de containers/publicadores foram consultados nos últimos cinco minutos, sem erro operacional; a busca textual encontrou apenas o nome do monitor `failed proposals` numa linha de sucesso.

Targets confirmados: node OS 10/10, etcd 7/7, Traefik 6/6, inventário de Pods 3/3 e endpoints KubeVirt 5/5. PSI não é suportado pelos kernels observados; a visão usa métricas disponíveis de paginação e fila de I/O, sem inventar PSI.

- Capacidade de RAM: 10/10 nós coincidiram com a fonte do SO.
- Filesystems: 58 observações de mounts tiveram capacidade idêntica à fonte; incluem bind mounts duplicados, tratados na consulta.
- 113 PVCs e 114 PVs inventariados. Os 113 PVCs estavam Bound; referência do PV, UID/namespace/nome e capacidade conferidos. Há PV adicional sem claim vinculada; isto não significa erro de coleta.
- 45 filesystems únicos de PVCs tiveram capacidade comparada ao kubelet. Volumes Block, não montados ou sem estatística do driver não possuem percentual de filesystem válido. O dashboard distingue falta dessa medição de zero uso.
- Recursos de containers ativos: CPU request 187, memória request 186, CPU limit 142 e memória limit 143, todos coincidentes com a API Kubernetes.
- Working set: 346 comparações. Seis divergiram acima de 10% ao comparar amostras coletadas em instantes diferentes; no alinhamento temporal de ±90 segundos, três coincidiram exatamente e as demais ficaram dentro de 1,15%. Não é uma promessa de igualdade byte a byte entre amostras assíncronas.
- Elasticsearch: aproximadamente 3,99 GB de working set, com request e limit de 4 GiB; diferença em relação à fonte de 0,077%. GB decimal e GiB binário não são equivalentes. Request não é uso; working set não é somente heap/RSS.
- Harvester: a partição de dados tinha aproximadamente 774 GiB usados e 1.706 GiB de capacidade. A partição persistente tinha aproximadamente 56 GiB usados e 147 GiB de capacidade. A diferença anterior era de partição, não justificava somar mounts repetidos.
- As dez VMs tiveram a fonte do SO conferida: nove nós Kubernetes via mounts do coletor/kubelet e a VM `services` por SSH. Nesta última, MemTotal e capacidade das duas partições coincidiram exatamente com KubeVirt; diferenças de amostras assíncronas foram 0,0052% em memória disponível, 0,048% em memória usada estimada e 0,0106% em bytes usados de vda3. A partição de boot coincidiu também no uso. Nenhuma credencial SSH está no pacote.

## Testes controlados de requisições

Request Lab: 100 chamadas, cinco concorrentes, atraso solicitado de 75 ms: 80 respostas HTTP 200, dez HTTP 400 e dez HTTP 500. Os deltas no cliente, contador da aplicação, soma dos contadores Traefik e métricas ingeridas pelo SUSE coincidiram exatamente: 80/10/10.

O teste durou 1,788 s, com 55,928 req/s durante o teste. Média cliente 89,099 ms, aplicação 75,524 ms e Traefik 76,845 ms. São camadas e períodos distintos. O dashboard de cinco minutos dilui um teste curto; `irate` ainda mede entre scrapes, não instantaneamente. Nove chamadas de aquecimento, fora da linha de base, explicaram 109 chamadas na janela do dashboard.

Brasil Dados API: duas séries de 100 respostas válidas. O primeiro teste criou uma série Traefik nova cujo primeiro valor coletado já era 100; `increase` não reconstrói chamadas anteriores à primeira amostra. Após estabelecer a linha de base, o segundo teste confirmou cliente 100, aplicação 100 e delta Traefik ingerido 100 (contador de 100 para 200). A implementação do procedimento explica aquecer rota/código, esperar a coleta e só então medir.

## Consultas e filtros

- 3.389 consultas por combinação de filtros (range query para painéis dependentes do período): zero erros e zero valores não finitos.
- 631 consultas históricas de uma hora: zero erros e zero valores não finitos.
- Todos os painéis com Everything retornaram dados na auditoria principal; um cluster inexistente não retornou falsos zeros.
- Foram percorridos os caminhos de valores individuais descobertos nos filtros, seleções múltiplas representativas e Everything nos níveis superiores. Não é uma prova de todas as combinações arbitrárias, datas futuras ou subconjuntos possíveis.
- 658 resultados da auditoria principal e 146 históricos vazios foram mantidos explícitos. Incluem escopos sem a tecnologia, ausência de eventos, séries novas e fontes sem estatística. Não converter tudo em zero.
- No Harvester de membro único, RTT entre peers etcd pode ficar vazio: não há outro membro com tráfego entre peers. No Rancher sem PVCs, os gráficos de uso de PVC não se aplicam. Nem toda VM/volume fornece estatística de filesystem via guest agent.

## Monitores e alertas

Os 33 monitores foram publicados, consultados e avaliados pelo SUSE sem erros nem métricas sem associação à topologia. As 33 consultas também retornaram números finitos. Consulte `docs/ALERT-COVERAGE.md` para a cobertura de cada um dos 125 painéis de métricas, o recurso associado, limiar e orientação.

Exemplos observados durante a revisão: WAL etcd do Harvester p99 em aproximadamente 14,72 ms, acima do limiar inicial de 10 ms; working set do container Kafka em aproximadamente 96,59% do limit; uma previsão anterior de ocupação do PVC Kafka em 96 h ficou ativa e depois deixou de exceder o limiar. Previsão não significa disco já cheio. Estes resultados precisam de investigação operacional, não de exclusão do alerta.

Os monitores nativos cobrem prontidão de Pods/nós, réplicas, reinícios, OOM e CPU throttling. Monitores de uso ajudam a investigar; limite de CPU ausente ou uso alto isolado não implica necessariamente indisponibilidade. Limiares de 20 ms para disco e 3 s para p95 HTTP são pontos iniciais, ajustáveis ao baseline/SLO.

A criação e avaliação de monitores não comprovam entrega de notificações. O teste padrão de e-mail do SUSE foi enviado e o destinatário confirmou o recebimento. O conteúdo “Ye Component/ye-cluster” é fictício e prova somente o canal SMTP. Uma regra manual, restrita à tag `sre-dashboards`, foi habilitada; os dois monitores HTTP dispararam para Request Lab, e o destinatário confirmou o recebimento dos e-mails reais. A recuperação também foi avaliada no SUSE e o destinatário confirmou os e-mails de encerramento. Por decisão do usuário, SMTP e notificações serão configurados manualmente; somente os monitores pertencem ao chart. O token publicador possui permissões de monitores, mas não executa `sts monitor run`; não foi ampliado para administrador.

## Aceites ainda dependentes do destino

1. Ajustar deduplicação e escalonamento no cliente: o laboratório recebeu os dois monitores, aplicação e Traefik, para a mesma falha controlada. Canal, abertura e recuperação foram confirmados.
3. No cliente, ajustar e testar os seletores Fleet antes de direcionar o GitRepo aos clusters. A branch pública foi validada; o teste de leitura sem alvos não substitui rollout do cliente.
4. Homologar numa instalação nova, com CA, registro privado, versões, storage drivers e políticas do cliente. A imagem opcional do publicador em Dockerfile não foi construída nem verificada em registro privado neste laboratório.
5. Não foram provocados perda de quorum etcd, disco cheio, OOM ou falhas de produção para disparar cada alerta. A avaliação real e os testes controlados de aplicação não substituem um exercício de falhas aprovado.

Os arquivos privados de evidência, tokens, kubeconfigs e logs detalhados ficaram fora do pacote. A validação visual está registrada separadamente em `tests/UI-VALIDATION.md`.

## Verificação de totais por período

Os totais agora somam incrementos de um minuto, com passo fixo de um minuto, ao longo do período selecionado. Essa implementação passou pela API real SUSE para 1, 24, 48 e 168 horas. Alternativas com `[1i]` e aritmética direta `start()/end()` foram rejeitadas pela API SUSE e retiradas. A integração de taxas foi substituída para evitar dependência do tamanho visual do gráfico. Consulte a referência operacional para os limites e o método final. Não extrapolar essa validação para 30 dias ou qualquer backend.

Os dois monitores HTTP inicialmente apresentaram quatro estados sem mapeamento após a primeira avaliação; o formato dos Services foi corrigido e a verificação posterior confirmou 33 avaliações e zero estados sem mapeamento.

A revisão de totais com passo fixo passou novamente por 3.389 casos na API SUSE: zero erros, 658 resultados vazios e zero valores não finitos. Os vazios variam com o instante consultado e o escopo. Consulte UI-VALIDATION.md para os pontos ainda não concluídos na interface.

Após a publicação final das linhas do tempo e descrições (Helm revisão 17), a auditoria pela API SUSE foi repetida: 3.389 casos, zero erros, 658 vazios e zero valores não finitos. Os 29 testes locais e os checks Helm 3/4 passaram.

Comparação independente do algoritmo final: aplicação e Traefik, cada um com janelas de 1, 24, 48 e 168 horas, tiveram igualdade exata entre soma de incrementos de um minuto e aumento direto do contador na mesma janela (8/8 comparações). As consultas usaram fim fixo e alinhado ao minuto, dois minutos no passado para permitir ingestão. Isso valida a aritmética; não recupera eventos anteriores à primeira amostra.

## Correção de associação nas legendas

A revisão visual encontrou um defeito no componente de legendas da versão 2.10.2: o payload de nomes é ordenado alfabeticamente, mas a coluna de resumos usa o índice do array original de pontos. Na latência, “Average” era associado ao número do p95 e vice-versa; na taxa, “Five-minute average” e “Latest sample interval” estavam invertidos na coluna Last. Os cartões e as consultas não tinham essa troca.

O código público instalado (`Kst`/legenda e pontos do TimeSeriesChart) confirmou a causa. A versão do pacote retira colunas numéricas das 90 legendas em tabela, mantendo nomes, curvas e tooltips; não altera os valores das consultas para compensar um defeito de apresentação. Um teste de regressão impede reintroduzir essa coluna nesta base. A atualização do SUSE deve ser avaliada com teste antes de reabilitá-la.


## Recursos e validação depois das otimizações

Foram medidos 23 Pods/38 containers adicionais, em dez amostras espaçadas por 30s. O relatório docs/IMPACTO-E-SEGURANCA.md contém reservas, limites, uso observado, crescimento dos PVCs, retenção e cenários de dimensionamento. Não existe baseline controlado anterior à primeira instalação; a diferença histórica do servidor não pode ser atribuída somente aos charts.

Todos os containers dos três charts têm requests/limits de CPU e memória. Schemas rejeitam ausência/zero; a suíte final de 29 testes inclui renderização de todos os perfis, casos inválidos e migração idempotente de tags. Helm 3/4 passaram.

Removidos somente loadavg/time/stat do node-exporter, cujas famílias já eram descartadas. Rollouts de plataforma: Observability revisão 5, Harvester revisão 5, Rancher revisão 7. Durante o rollout Rancher, um arquivo antigo de values desabilitou a NetworkPolicy de métricas e provocou timeouts; o perfil atual foi reaplicado. O teste Helm às 19:10 UTC confirmou HTTP válido nos três endpoints. A API confirmou novamente 23/23 alvos saudáveis e 10/10 coletores de nós saudáveis. Houve lacuna de coleta nesse intervalo; não foi mascarada como zero tráfego.

A revisão 21 do conteúdo persistiu as tags por dashboard em 33 monitores, mantendo seus IDs. O publicador agora compara tags do catálogo, aceita migração das tags antigas do projeto e rejeita identidades/tags estranhas. Os totais HTTP ficaram amarelos quando positivos, sem classificar criticidade apenas pelo número absoluto.

No navegador, o filtro Request Lab mostrou 1079 respostas e 120 HTTP 5xx no período do teste de abertura/recuperação: 359 respostas 200 + 120 respostas 500 + 600 respostas 200. Houve uma conexão reiniciada pelo peer no cliente durante a fase inicial; sua causa exata não foi determinada. Ela não foi contabilizada como uma resposta HTTP concluída. As 600 chamadas de recuperação não tiveram falha de transporte.


A auditoria posterior à recuperação e à revisão 22 executou novamente 3389 consultas/filtros: zero erros, 653 vazios e zero casos não finitos. A quantidade de vazios depende do instante e escopo. Na janela posterior de cinco minutos, 42 logs de containers/publicadores/testes foram lidos: zero erros encontrados, zero falhas ao obter logs e nenhum container Running não pronto.

O monitor de memória apresentou estados UNMAPPED transitórios relativos a Pods substituídos durante o rollout. Após expirar a janela histórica, a avaliação atual apresentou 133 estados associados, zero múltiplas associações e zero UNMAPPED. Isso foi distinguido de um erro permanente de URN. Não foram ocultados os sinais reais de pressão de memória.

## Últimas alterações solicitadas

Adicionadas duas listas de Pods: cinco maiores percentuais de uso do limite, mais todos acima de 80%. As 74 novas combinações de consulta/filtro responderam sem erros ou valores não finitos. Foram observados cinco Pods na lista de CPU e 12 na de memória na amostra; essa contagem varia. A memória dos Pods virt-launcher descreve o processo que hospeda a VM, não o uso do SO convidado. Removido o card “Available history” limitado a 24 horas. O pacote contém agora 129 painéis, dos quais 123 são métricas e seis são textos de orientação.

No teste adicional do usuário (200 chamadas em 1,49 s), a série Traefik HTTP 200 cresceu de 1044 para 1237 às 19:43:30 UTC: 193 respostas incluindo tráfego além das 190 respostas 200 do benchmark. A taxa recente chegou a 6,433 req/s e depois voltou a zero; a média de cinco minutos chegou a 0,6433 req/s. A série 503 nasceu no mesmo scrape já com 10 e não tinha baseline anterior; a taxa dessa série ficou zero. Não é possível atribuir as três chamadas 200 adicionais sem logs individuais. O procedimento agora explica aquecimento/baseline e a diferença entre taxa do teste, intervalo de scrape e média de cinco minutos.

A simplificação final do Traefik removeu a taxa recente, a média do período e a contagem de aplicações. Restam 21 painéis no Traefik e 129 no conjunto (123 de métricas). Os quatro indicadores principais distinguem explicitamente total do período e taxas/latências de cinco minutos. No segundo teste do usuário, counters aumentaram exatamente 400 respostas 200 e 25 respostas 503 (425 chamadas). O print anterior com 194 ainda não incluía esse teste; é necessário atualizar o fim do período após a ingestão.

## Aceite visual final

Os 129 painéis da revisão 25 foram percorridos na interface (123 métricas, seis textos). Recursos e Traefik foram revisitados após as últimas mudanças; os demais mantiveram as consultas e gráficos já inspecionados. Ver UI-VALIDATION.md para filtros, versões e limites, incluindo períodos acima de sete dias e combinações arbitrárias. Cinco definições persistidas comparadas aos arquivos locais.

## Última revisão de leitura e publicação

A revisão 29 separou a contagem e os nomes dos Pods acima de 80% do limite dos rankings de cinco maiores consumidores absolutos de CPU/memória. Esses rankings mostram o histórico real do grupo escolhido no fim do período. O pacote passa a 131 painéis: 125 de métricas e seis textos.

A auditoria final executou 3.452 consultas/filtros: zero erros, 715 resultados vazios e zero casos não finitos. As cinco definições persistidas coincidiram integralmente com os JSONs locais. Os 29 testes e os checks Helm passaram. Nos últimos cinco minutos de logs conferidos, 42 containers/publicadores/testes tiveram zero linhas de erro, zero falhas de leitura e nenhum container Running sem prontidão.

O link relativo dos painéis precisou usar `./#/metrics?...`: a navegação interna `/#/metrics?...` descartava a consulta. O link corrigido foi aberto no Chrome com filtro Observability, e a tabela trouxe somente os Pods desse cluster. A altura das listas foi conferida para evitar sobreposição com os títulos. Consulte UI-VALIDATION.md para a abrangência visual e as limitações.

## Publicação pública e leitura Fleet

Branch `helm-fleet-v6` publicada em `kaioneuhauss/suse-observability-dashboards`. O commit de conteúdo `faa5fc312536dbfcc20d0090b610da61f5284d88` passou no GitHub Actions com Helm 3.19.0 e 4.1.1 (run 34643767587). Uma clonagem HTTPS pública, sem a deploy key, coincidiu com os 114 hashes do manifesto.

O GitRepo temporário `suse-v6-public-fetch-canary` leu esse mesmo commit, atingiu Ready=True/GitJob Current e gerou um Bundle com 48 arquivos. Seu seletor não correspondia a nenhum cluster: 0/0 destinos, sem instalar release concorrente. O GitRepo foi removido após o teste. Essa evidência complementa o Bundle canário anterior em modo plan; não representa uma instalação limpa de toda a plataforma em um novo cliente.
