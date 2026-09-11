# Matriz de solicitações e aceite

Esta matriz acompanha os pedidos desde a primeira revisão. “Validado” significa evidência no laboratório descrito em RESULTADOS.md; não é certificação de outro ambiente. Itens “em andamento” não devem ser apresentados como concluídos.

| Solicitação | Implementação / evidência | Situação |
|---|---|---|
| Valores inteiros sem K/M | Cards usam unidade none e zero casas; contadores continuam estimativas entre scrapes | Validado na API e GUI |
| Requisições por rota em disposição legível | Série por rota, legenda abaixo, largura ampliada; não grade de pequenos números | Validado na API e na revisão visual final |
| Aplicações com maior latência | Ranking p95 em Instrumented apps | Validado na API e na revisão visual final |
| Explicar mean latency | “Average response time”, exemplo 50/100/150 ms, diferenças de camadas e percentis | Validado nas descrições |
| Taxa recente e média de cinco minutos | Pedido posterior simplificou o Traefik: retirado recent samples; mantidos taxa e histórico de cinco minutos | Janelas explicadas; segundo teste de 425 chamadas conferido |
| Totais acompanharem período da barra | Soma de incrementos de um minuto, passo fixo; 1h/24h/48h/7d comparados a increase direto | 8/8 comparações exatas; acima de 7 dias ainda depende de teste |
| Pods não saudáveis e thresholds incompreensíveis | Contagem, nomes, namespace e motivo; ausência de linhas “Threshold 1/2” nesses estados | Validado; Job Failed real preservado |
| Reinícios e réplicas indisponíveis mais úteis | Destacar Pods/workloads afetados e ausência de eventos; cobertura nativa | Implementado e conferido na revisão da plataforma |
| Consumo de disco Harvester inconsistente | Separar partição persistente/dados; não somar bind mounts; uso compatível com fonte df | Validado por fonte |
| Excluir /dev/loop0, boot e partições de baixo valor operacional | Visão operacional exclui loop/OEM/boot/runtime/kubelet; preserva dados e persistência | Validado nas consultas |
| Validar todos os nós/VMs | Dez nós e dez SOs convidados; services via SSH independente | Validado; divergências temporais quantificadas |
| Validar PVs e PVCs | 113 PVCs, 114 PVs; vínculos e capacidades; 45 filesystems únicos contra kubelet | Validado; Block/sem mount não são zero uso |
| Saúde etcd além de disponibilidade | Líder, eleições, propostas, lag raft, WAL, commit, peer RTT e quota | 7/7 endpoints; RTT de membro único não se aplica |
| Traefik: identificar certificado e dias | Domínio/certificado e dias restantes, alertas 30/7 dias | Consultas e séries verificadas |
| Traefik: de onde vêm milhares de chamadas Rancher | Tráfego inclui API, agentes e health checks; detalhamento por backend, método e código; não equivale a visitas humanas | Medição de counters validada; não atribui causa individual sem logs |
| Filtro Traefik: Rancher presente, Harvester ausente | Coleta Rancher liberada em NetworkPolicy restrita; filtro baseado na fonte aplicável | 6/6 endpoints; filtros por API e GUI |
| Contagem de Pods sem requests/limits | Cada Pod Running contado uma vez se algum container regular não possui configuração | Contagens comparadas à API; inclui hotplug |
| Lista dos Pods e namespaces | Lista de afetados e contagem separada; exclui init/terminados conforme descrição | Validado na API e na revisão visual final |
| CPU em unidade clara | mCPU/millicores, 1000 mCPU = um núcleo; VM vCPU e uso diferenciados | Validado nos títulos e consultas |
| Uso de memória VM versus configuração | Guest MemTotal/MemAvailable, QEMU e requests/limits separados | Dez fontes do SO conferidas |
| Elasticsearch usando quase o limit | Working set ~3,99 GB versus request/limit 4 GiB; comparar também RSS e não confundir com heap | Diferença da fonte 0,077% na amostra |
| Gráficos de gauge para utilização | Gauges CPU, memória e filesystem com faixa e unidade explicadas | Implementado e visto na GUI |
| Espaços vazios e layout quebrado | Preservação JSON evita chave y virar true; larguras ampliadas | Definições persistidas comparadas |
| Fontes pequenas, nomes cortados | Cards em duas colunas, comparativos largos, legendas inferiores | Conferido nos painéis finais; nomes longos usam largura ampliada e legenda abaixo |
| Pedido de salvar ao mudar filtro | saveVariables=false; mudanças temporárias não alteram definição | Saída sem salvar conferida; editar widget ainda é alteração |
| “No data” em alguns gráficos | Classificar sem evento, não aplicável, série nova, sem estatística e falha de coleta | Auditorias registram vazios, sem substituição indiscriminada por zero |
| Erros 400/500: quando e qual aplicação | Séries por código/rota/backend e janela temporal; instrução de correlação com logs/traces | Testes 80x200/10x400/10x500 com deltas exatos |
| Motivo exato / request individual de erro | Não pode ser deduzido do contador; depende de access logs, trace/exceção e IDs | Limite documentado; não inventar causalidade |
| Revisar logs dos Pods de coleta | Logs atuais e anteriores, readiness, reinícios, scrape/remote write | 23 Pods Ready; ver timestamps e atualização final em RESULTADOS |
| Aplicar monitores via Helm | Um chart central com 33 STYs e catálogo, publicação finita e verificação persistida | Publicado; 33 avaliações sem erro/UNMAPPED |
| Alertas com recurso e problema identificáveis | Título cluster/namespace/recurso; limiar/janela e orientação por regra | Aplicação/Traefik dispararam; usuário confirmou e-mails reais |
| Teste de e-mail | Teste fictício de canal separado de disparo real e recuperação | Canal, abertura e recuperação recebidos e confirmados pelo destinatário |
| SMTP global / notificações manuais | Decisão expressa do usuário: não publicar canais no chart | Mantido; nenhum token novo de notificações criado |
| Thresholds didáticos em cada “?” | Cobertura dos 125 painéis, com razão para alertar ou apenas investigar | Ver ALERT-COVERAGE.md; pontos iniciais ajustáveis ao SLO |
| Filas “SUSE” pouco claras | “Telemetry waiting to be sent · bytes”; zero indica fila vazia | Fonte vmagent; não confundir com fila OTLP em requests |
| Indicadores avançados VM | KVM scheduler delay/wait, paginação/swap, tempo de disco, IOPS e fila de host | Métricas KubeVirt presentes; não equivalem automaticamente a VMware CPU Ready |
| Comparar referências SRE/Datadog/Grafana | RED/quatro sinais/USE; separar instrumentação, infraestrutura, storage e coleta | Referências primárias e limites no guia de estudo |
| Helm/Fleet simples e valores compartilhados | Três charts por responsabilidade; cinco dashboards em uma instalação central | Helm 3/4 e Fleet canário validados |
| Configuração Traefik via Rancher/RKE2 | Fragmentos para chartValues ou HelmChartConfig conforme gestão do cluster | Pré-requisito documentado; preservar dono e configurações existentes |
| Entender etcd e KubeVirt | Endpoint loopback etcd; scrape TLS KubeVirt e OTLP central explicados | Explicado no guia de estudo entregue |
| Explicar Secrets e necessidade real | Intake, publisher, registry e CA distintos; publisher é necessário para Helm recorrente | Não é credencial exclusiva do assistente |
| Organizar apenas arquivos essenciais | Charts, perfis, pré-requisitos, testes, docs; dados privados fora do ZIP/Git | Pacote consolidado com manifest SHA256; dados privados excluídos |
| README/dashboards em inglês; conversa em português | Textos dos dashboards e README em inglês claro | Mantido |
| Documento de cliente com passos copiáveis | Procedimento separado do material de estudo | Documento Markdown e PDF entregue |
| Documento de estudo detalhado | Estrutura Helm, criar charts/dashboards/monitores, princípios, fontes e decisões | Documento Markdown e PDF entregue |
| Publicar no GitHub público autorizado | Branch helm-fleet-v6 publicada; clonagem pública e 114 hashes conferidos; GitHub Actions Helm 3/4 passou | Validado; GitRepo leu a branch com zero clusters alvo e foi removido |
| Segurança e impacto nos clusters/SUSE | RBAC, mounts, TLS, imagem, recursos, filas, séries e carga observada | Relatório IMPACTO-E-SEGURANCA.md com consumo observado, limites e cenários; não promete impacto zero |
| Validação gráfica de cada painel/filtro | Matriz separada distingue API de interface e versões de layout | Todos os painéis percorridos; API em 117 caminhos e filtros GUI representativos; ver UI-VALIDATION.md |
| Usar só Chrome Kaio/neukaiosantos | Perfil conectado confirmado pelo usuário | Respeitado; sem navegador integrado para o aceite |
| Interromper a 2% / entregar parcial | Substituído por autorização posterior para continuar com resets | Um reset usado; sem compra de créditos |
| Bug adicional: valores Last trocados nas legendas | Defeito da versão SUSE confirmado no código público e GUI; removida coluna em 90 tabelas | Correção persistida; 29 testes passaram na versão final |

O aceite distingue consultas, interface, fonte das métricas e entrega de alertas. Um teste de laboratório não certifica todas as combinações possíveis em outro cliente.

| Pedido adicional | Evidência | Situação |
|---|---|---|
| Tags de monitores por dashboard | 33 monitores com sre-dashboards e tags dashboard-applications/platform/traefik/resources/harvester; correção de migração no publicador | Persistência conferida após revisão 21 |
| Quantificar CPU/RAM/disco e otimizar | Dez amostras dos coletores, comparação histórica do servidor, PVCs/retention/6101 séries; relatório IMPACTO-E-SEGURANCA.md | Medido; baseline causal anterior indisponível |
| Requests e limits em todos os componentes | Defaults em todos os containers, schemas obrigatórios e testes de render/casos inválidos | 29 testes locais passaram |

| Últimos pedidos | Evidência | Situação |
|---|---|---|
| Separar Pods acima de 80% do ranking dos cinco maiores consumidores | Contagens CPU/memória e listas só acima de 80%; ranking separado por consumo absoluto com histórico | API e GUI validadas; link filtrado de detalhes testado |
| Remover histórico enganoso limitado a 24h | Card retirado do Traefik | Implementado |
| Explicar diferença entre benchmark e dashboards | Deltas 400x200 + 25x503 = 425; janela de scrape, média 5min e Refresh explicados | Validado; primeiro nascimento de série não tem baseline |
| Resumir dashboard Traefik | 21 painéis; removidos recent samples, média redundante do período e contador de aplicações | Validado na interface |
