# Validação visual — 11/09/2026

Inspeção no Chrome conectado, perfil Kaio (`neukaiosantos`), SUSE Observability 2.10.2. Foram percorridos os 131 painéis finais: 125 de métricas e seis textos. Os painéis de métricas visitados terminaram em estado de sucesso, sem erro de consulta ou mensagem genérica de falha. A inspeção usa DOM e capturas de tela, além dos testes da API.

| Dashboard | Painéis | Evidência visual |
|---|---:|---|
| Kubernetes Platform Health | 41 | Todos percorridos; gauges, Pods afetados, réplicas/reinícios, discos/PVCs, etcd e coleta. Harvester e namespace testados; saída sem pedido de salvar. |
| Workload Resource Efficiency | 23 | Painéis anteriores percorridos, com nova conferência dos modificados: contagens e listas somente acima de 80%, ranking de cinco consumidores absolutos separado. Contagens, nomes, requests/limits, working set/RSS e throttling. Filtro Observability + suse-observability conferido. |
| Instrumented apps | 14 | Todos percorridos; rotas, erros e latência. Request Lab selecionado e resultados do teste conferidos; nenhuma consulta foi alterada depois dessa passagem. |
| Traefik Ingress Health | 21 | Todos percorridos após simplificação. Filtro oferece Observability e Rancher; Harvester ausente. Rancher + cattle-system + rancher mostrou tráfego, totais e latência. Saída sem salvar. |
| Harvester VM & Host Health | 32 | Todos percorridos; CPU/memória configuradas e medidas, guest/QEMU, scheduler, paginação, filesystem, disco e coleta. Dez VMs listadas no seletor; services mostrou CPU e memória do guest. |

As revisões posteriores preservaram painéis já inspecionados e revalidaram os modificados. As cinco definições persistidas foram exportadas e comparadas com os arquivos locais. O texto introdutório do Traefik foi encurtado para caber sem rolagem interna. A reconciliação pode trocar IDs: reabra pela lista de dashboards em vez de usar uma aba antiga.

## Filtros e período

- A auditoria automatizada percorreu 117 caminhos de filtros descobertos, combinações múltiplas representativas e cluster inexistente. A revisão final executou 3.452 casos, sem erros ou valores não finitos; 715 respostas vazias por instante/escopo, discriminadas na auditoria. Painéis removidos posteriormente deixam de gerar consultas. Não foi testado o conjunto de todas as combinações arbitrárias de múltipla seleção na GUI.
- Na interface foram testadas seleções representativas de cluster, namespace, aplicação e VM. As opções vêm da fonte aplicável; Traefik não oferece Harvester. Depois de trocar um filtro pai, redefina os dependentes para Everything. None significa nenhuma seleção e pode corretamente mostrar No data.
- Totais de aplicação/Traefik em 1h, 24h, 48h e 7d foram comparados à fonte com fim alinhado; 8/8 comparações exatas. A GUI foi usada com 1h e 7d. Períodos acima de sete dias não receberam o mesmo aceite e exigem teste no destino.
- Os filtros temporários não alteraram a definição nem pediram salvamento ao sair. Editar widgets continua sendo uma alteração real.
- O fim do período pode permanecer no instante da consulta anterior. Após um benchmark, aguarde coleta/ingestão e clique Refresh. O segundo benchmark do usuário teve delta exato de 425 respostas; o print anterior ainda não o incluía.

## Estados que não devem virar zero

Um etcd de membro único não produz RTT entre peers. PVC Block ou sem filesystem montado não tem percentual de filesystem. Disco sem operações não tem latência média definida. Séries recém-criadas não têm baseline para recuperar chamadas anteriores à primeira amostra. Uma falha de coleta não comprova zero consumo ou zero erros. Esses limites são explicados nos painéis e nos guias.

O modo Everything foi percorrido sem mensagens No data nos painéis de métricas das passagens registradas. Isso não significa que toda seleção ou qualquer período deva conter dados. Vazio por não aplicabilidade foi conferido separadamente nas fontes e auditorias.

## Limitação gráfica da versão instalada

SUSE Observability 2.10.2 pode associar a coluna Last da legenda ao nome de outra série após ordenar rótulos. A coluna foi removida; curvas, cores, tooltip e cards permanecem. Listas usam legendas inferiores em painéis compactos, com altura suficiente para evitar sobreposição. Os nomes completos aparecem ao expandir “+ more”. Retratos de fim de período aparecem como linhas constantes; a descrição informa esse comportamento. Não há widget de tabela nativa nesta versão. Os links de detalhes abrem a consulta filtrada no Metrics Explorer, onde Table view mostra nomes e valores. O link filtrado por Observability foi testado. Valores de razão nessa tabela são brutos: 0,8 = 80%. Não são eventos HTTP individuais.

Na revisão 29, foram observados 0 Pods acima de 80% de CPU e 12 de memória no escopo Everything. Filtrando Observability, a tabela mostrou somente Pods desse cluster. São retratos de validação, não valores fixos esperados.
