# Evidência do laboratório — 26/10/2026

## Ambiente observado

| Plataforma | Versão observada |
|---|---|
| SUSE Observability | 2.10.2 |
| CLI de publicação | 3.3.6, SHA-256 conferido |
| Rancher Prime | 2.14.6 |
| Harvester | 1.8.2 |
| Longhorn | 1.11.2 |
| KubeVirt | 1.7.4 |
| VM Import Controller | 1.8.2 |
| Kubernetes dos três clusters | RKE2 1.34.9 / 1.35.6 / 1.35.7 |
| Traefik RKE2 | 3.7.1 / chart 40.1.003 |

Essas versões são evidência deste laboratório, não uma matriz de suporte. O servidor, Agents e plataformas existentes foram preservados.

## O que foi executado

- Inventário inicial somente de leitura, propriedade Helm/Fleet e backups privados de values, manifests e conteúdo externo.
- Exportação dos cinco dashboards do projeto, dashboard nativo e 33 monitores antigos.
- Remoção confirmada dos cinco dashboards/33 monitores antigos pelo publicador.
- Desinstalação de `sre-platform-telemetry` nos três clusters, `kubevirt-otel-collector` no Harvester e `suse-observability-content` no central, incluindo seus Jobs hooks.
- Instalação com `helm install` das novas releases: Kubernetes/Traefik nos dois clusters RKE2, Virtualization no Harvester e quatro publicadores centrais; depois, instalação independente do módulo Imports na origem e no central.
- Publicação final de nove dashboards do projeto (197 consultas de métricas) e 34 monitores Enabled; dashboard nativo mantido com o mesmo ID.
- Correção real da coleta KubeVirt: o coletor anterior falhava por CA desatualizada; o novo inicializou com a CA vigente e passou a coletar dez VMs.
- Remoção da antiga cópia de CA após backup e confirmação de ausência de referências nos 19 Pods/workloads do namespace.

O backend e seu histórico de métricas não foram apagados. As aplicações de demonstração `brasil-dados` e `request-lab` foram preservadas por decisão explícita do responsável; a limpeza abrange somente os componentes dos dashboards.

## Validação concluída

- 53 testes locais aprovados: isolamento dos módulos, schemas, layout e geração repetível, publicador, recursos, aliases HTTP, CA, NetworkPolicy e exporter VMIC (paginação, falha/staleness, campos ausentes, privacidade, fases e timestamps).
- `helm lint` dos cinco charts, renderização e dry-run nos APIs de destino. Novos recursos de Virtualization/Imports passaram por dry-run no Harvester e central antes da aplicação.
- Auditoria abrangente de **7.346 casos de consultas/filtros**, sem erros de execução ou valores não finitos. 2.030 casos vazios foram contabilizados separadamente: incluem controle de cluster inexistente, escopos sem dados e métricas não aplicáveis.
- Auditoria histórica de seis horas: **831 casos**, zero erros/valores não finitos, 213 vazios. Cobre Everything, clusters individuais e multisseleção representativa; não todas as combinações arbitrárias possíveis.
- Após as correções dos totais HTTP: nova auditoria de todos os filtros de aplicações (**114 casos**) e Traefik (**459 casos**), sem erros/valores não finitos. Após corrigir o escopo de capacidade, suas nove consultas foram reexecutadas com dados, incluindo Everything restrito ao Harvester.
- **45 consultas / 18 verificações de invariantes HTTP**, aprovadas. O mesmo período foi avaliado em passos de 60, 300 e 900 segundos. Na janela de diagnóstico, o total correto foi 31.104 requisições nas três resoluções; antes, caía indevidamente para 6.252 e 2.053. Também foi corrigida a soma por rota que congelava o último minuto. Essa comparação detectou erros que um simples teste de sintaxe não encontrava.
- **34 consultas de monitores**, todas executadas com séries atuais e sem erro. Isso não representa 34 testes de disparo/recuperação.
- `up=1` nos alvos KubeVirt e Longhorn após liberação; `harvester_import_inventory_up=1`. Dez nós Ready e todos os Pods ativos dos módulos prontos nos três clusters; nove Jobs centrais de publicação concluídos.
- Conferência visual de unidades, valores e filtros na interface SUSE, além da consulta direta ao backend.

### Valores confrontados com as APIs de origem

| Comparação | Resultado observado |
|---|---|
| VMIs em execução | 10 na API e no dashboard |
| Topologia de CPU dessas VMs | 50 vCPUs em ambos; cores × sockets × threads |
| RAM guest configurada dessas VMs | 107.374.182.400 bytes (100 GiB) em ambos |
| CPUs lógicas do host | 32 em ambos |
| Volumes Longhorn | 184 em ambos |
| Robustness ativa | 41 healthy, 1 degraded, 142 unknown, correspondência exata |
| Timestamps de último backup | 184 valores conferidos; 183 sem backup registrado e 1 com timestamp; não é cobertura de proteção de VMs |
| Capacidade lógica provisionada Longhorn | 10.668.803.620.864 bytes em ambos; não é uso físico |
| Registros VMIC | 8, todos `virtualMachineRunning`, em ambos |
| Capacidade lógica de discos importados | 254.476.812.288 bytes em ambos |
| Discos e intervalos VMIC por registro | Correspondência exata com condições/timestamps dos oito objetos |
| Requests/limits dos containers | 772 campos comparados: 318 Observability, 148 Rancher, 306 Harvester; zero divergências ou campos faltantes |

### Longhorn: autorização e resultado

Após autorização explícita do responsável, foi aplicada `obs-virtualization-longhorn-metrics` em `longhorn-system`. A regra seleciona managers `app: longhorn-manager`, usa **um único peer com namespaceSelector e podSelector juntos**, e permite somente TCP/9500 de `obs-virtualization` / `sre-kubevirt-telemetry` no namespace `suse-observability`. As regras nativas existentes foram preservadas. O manifesto aplicado foi conferido novamente, e o alvo passou a `up=1` com métricas de volumes, disco, I/O, snapshots e backups ingeridas.

Existe um volume previamente criado com robustness degraded e falha de agendamento de réplica (`disks are unavailable`). O estado exibido corresponde à API Longhorn; não é erro da consulta. Não foram alteradas réplicas, placement, volumes ou dados para deixar o dashboard verde. A capacidade de um host único não foi tratada como HA.

### Casos vazios explicados

Com Everything, os painéis de idade/última condição de importações **ativas** ficam vazios porque os oito registros estão concluídos. A latência Longhorn de leitura pode ficar vazia em janelas sem IOPS de leitura; o denominador/filtro impede inventar uma latência para disco ocioso. Filtros de volumes detached não têm I/O atual. Filtros inexistentes não produzem zeros de saúde. Essas ausências não foram contadas como aprovação de disponibilidade.

## Limites e pendências

- **VMIC:** validação ao vivo feita sobre oito registros concluídos existentes. Fases ativas/falhas e indisponibilidade do inventário passaram por testes locais; não foi iniciada uma importação VMware nova, desligada uma VM ou simulado um erro de transferência.
- **Coriolis:** removido do escopo por decisão do responsável; a VM permaneceu parada.
- **Histórico:** p95 de 24 horas e backup metadata não comprovam dia completo, RPO, restauração ou consistência de aplicação. Não houve restauração de backup.
- **Métricas:** valores e contratos foram conferidos nas versões observadas. Medidas dinâmicas continuam sujeitas a resolução de coleta, lacunas e precisão dos exporters; não se promete exatidão irrestrita para todo workload/versão futura.
- **Credencial de publicação:** preservados os tokens restritos existentes. O caminho de cliente novo com role padrão precisa de validação das permissões da versão/organização.
- **CA:** inicialização com a CA atual e leitura restrita comprovadas; não foi provocada uma rotação da CA KubeVirt para testar o ciclo completo em produção.
- **Notificações:** publicação de monitores e consultas não comprovam entrega de e-mail/paging nem abertura/recuperação de todos os incidentes.
- **Aplicações:** contrato padrão validado com aplicações existentes. Aliases OTel passaram pelos testes de renderização; cada contrato alternativo precisa de aceite com suas métricas reais.
- **Resiliência:** não houve reboot, perda de host, failover, teste destrutivo de volume, teste de carga prolongado ou alteração de VMs.
- **Fleet/air gap:** não foram executados novos deploys nesses modos.

Backups completos, tokens e telemetria bruta permanecem fora deste repositório. Os charts e seus exemplos não contêm credenciais nem endereços privados do laboratório.
