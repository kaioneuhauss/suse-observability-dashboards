# Evidência do laboratório — 26/10/2026

## Ambiente observado

| Plataforma | Versão observada |
|---|---|
| SUSE Observability | 2.10.2 |
| CLI de publicação | 3.3.6, SHA-256 conferido |
| Rancher Prime | 2.14.6 |
| Harvester | 1.8.2 |
| Longhorn | 1.11.2 |
| Kubernetes dos três clusters | RKE2 1.34.9 / 1.35.6 / 1.35.7 |
| Traefik RKE2 | 3.7.1 / chart 40.1.003 |

Essas versões são evidência deste laboratório, não uma matriz de suporte. O servidor, Agents e plataformas existentes foram preservados.

## O que foi executado

- Inventário inicial somente de leitura, propriedade Helm/Fleet e backups privados de values, manifests e conteúdo externo.
- Exportação dos cinco dashboards do projeto, dashboard nativo e 33 monitores antigos.
- Remoção confirmada dos cinco dashboards/33 monitores antigos pelo publicador.
- Desinstalação de `sre-platform-telemetry` nos três clusters, `kubevirt-otel-collector` no Harvester e `suse-observability-content` no central, incluindo seus Jobs hooks.
- Instalação com `helm install` das novas releases: Kubernetes/Traefik nos dois clusters RKE2, Virtualization no Harvester e quatro publicadores centrais.
- Publicação final de cinco dashboards do projeto e 34 monitores Enabled; dashboard nativo mantido com o mesmo ID.
- Correção real da coleta KubeVirt: o coletor anterior falhava por CA desatualizada; o novo inicializou com a CA vigente e passou a coletar dez VMs.
- Remoção da antiga cópia de CA após backup e confirmação de ausência de referências nos 19 Pods/workloads do namespace.

O backend e seu histórico de métricas não foram apagados. As duas aplicações de demonstração existentes foram preservadas, com sua remoção pendente de decisão específica.

## Validação concluída

- 42 testes locais aprovados: isolamento dos módulos, schemas, layout, publicador, recursos, aliases HTTP, CA e escopo da NetworkPolicy opcional.
- `helm lint`, renderização e dry-run nos APIs dos três clusters.
- 3.705 casos de consultas/filtros reais: zero erros de execução e zero casos com valores numéricos não finitos. 822 casos vazios exigem interpretação; incluem filtro inexistente, dados não aplicáveis e Longhorn bloqueado. Não são 3.705 comprovações de saúde.
- Após remover a dependência de `status_class`, nova auditoria do módulo de aplicações com 114 casos: zero erros e zero valores não finitos; 38 casos vazios, incluindo seleções sem séries e o filtro inexistente de controle.
- `up=1` para todos os grupos habilitados de host, etcd, Traefik, inventários e KubeVirt no momento do aceite. Dez VMs presentes; idade da métrica KubeVirt inferior a um intervalo de coleta na verificação final.
- Dez nós `Ready`, coletores novos prontos e oito Jobs centrais concluídos.
- Conferência visual de VMs e aplicações na interface, incluindo gauges com valores atuais, contagem de dez VMs, disponibilidade e atualidade de amostras.

## Limites e pendências

- **Longhorn:** nomes/unidades verificados no endpoint real. A coleta direta encontrou isolamento de rede. A regra restrita TCP/9500 foi preparada, mas não foi autorizada pela revisão automática; a coleta Longhorn foi desativada no laboratório enquanto se aguarda decisão. Os painéis de armazenamento não têm aceite de ingestão. Nenhuma NetworkPolicy Longhorn foi aplicada.
- **Credencial de publicação:** preservados os tokens restritos existentes. O caminho de cliente novo com role padrão precisa de validação das permissões da versão/organização.
- **CA:** inicialização com a CA atual e leitura restrita comprovadas; não foi provocada uma rotação da CA KubeVirt para testar o ciclo completo em produção.
- **Notificações:** publicação de monitores e consultas não comprovam entrega de e-mail/paging nem abertura/recuperação de todos os incidentes.
- **Aplicações:** contrato padrão validado com aplicações existentes. Aliases OTel passaram pelos testes de renderização; cada contrato alternativo precisa de aceite com suas métricas reais.
- **Resiliência:** não houve reboot, perda de host, failover, teste destrutivo de volume, teste de carga prolongado ou alteração de VMs.
- **Fleet/air gap:** não foram executados novos deploys nesses modos.

Backups completos, tokens e telemetria bruta permanecem fora deste repositório. Os charts e seus exemplos não contêm credenciais nem endereços privados do laboratório.
