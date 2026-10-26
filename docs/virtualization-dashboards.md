# Como usar os dashboards de Virtualization

O chart Virtualization publica quatro dashboards. O módulo opcional Imports acrescenta um quinto, específico para importação VMware. Todos usam o formato nativo do SUSE Observability.

## Visão geral de VMs e hosts

Comece pela saúde e atualidade da coleta, quantidade de instâncias observadas e utilização de CPU, memória e filesystem. Compare o guest com o host antes de atribuir um problema à VM. Memória disponível no guest, RSS do QEMU, memória configurada e memória disponível no host respondem a perguntas diferentes.

Use os filtros de cluster, namespace e VM para investigar uma instância. Painéis de host e Longhorn estão explicitamente identificados como escopo de cluster: selecionar uma VM não transforma uma medida do host em consumo daquela VM.

## VM Contention

Responde: **a VM está demandando recursos ou esperando por eles?**

- CPU em uso junto com espera na fila do scheduler ajuda a separar demanda de contenção. A espera é uma média por vCPU, em segundos por segundo convertidos para porcentagem; não é contabilidade idêntica ao CPU Ready do VMware.
- Espera por I/O e latência média por disco ajudam a localizar gargalos de armazenamento. Disco ocioso não tem latência média definida.
- Memória utilizável, major page faults e atividade estimada de swap ajudam a investigar pressão no guest. O driver balloon e a versão do guest influenciam a disponibilidade dessas estatísticas.

Não habilita PSI nem muda configuração do kernel. As métricas disponíveis no KubeVirt instalado são suficientes para esse conjunto inicial.

## Capacity & Sizing

Responde: **quanto está alocado e qual demanda foi observada?**

- vCPUs configuradas e RAM configurada consideram apenas VMs com VMI em execução. CPU configurada = cores × sockets × threads.
- A razão vCPU/CPU do host usa CPUs lógicas. Não é porcentagem de utilização nem recomendação universal de overcommit.
- MemAvailable do host considera todos os processos e cache recuperável.
- p95 e pico de demanda usam o histórico disponível das últimas 24 horas. O pico de CPU é o maior valor da média de cinco minutos; não captura todo pico curto.
- A contagem de amostras ajuda a perceber histórico incompleto. Uma instalação recente não fornece 24 horas completas só porque o gráfico está configurado assim.
- O orçamento N-1 é apenas um limite superior: RAM total dos hosts menos RAM do maior host menos RAM configurada dos guests em execução. Não desconta overhead, reservas, restrições de placement ou armazenamento; resultado positivo não certifica HA. Em um host único não existe capacidade sobrevivente.

Faça recomendações de tamanho somente após observar ciclos representativos e requisitos da aplicação. O projeto não redimensiona VMs automaticamente.

## Storage & Protection

Responde: **o armazenamento está saudável e existem evidências de proteção?**

- Robustness e attachment são estados rotulados 0/1, não códigos de severidade. `unknown` em volume detached não equivale a volume saudável nem a falha confirmada.
- Latência Longhorn chega em nanossegundos e é exibida em milissegundos; IOPS já chega como taxa. A latência do guest pode incluir esperas adicionais e não precisa coincidir com a do Longhorn.
- Capacidade provisionada, uso físico, capacidade lógica agendada de réplicas e tamanho de snapshots são mostrados separadamente. Não devem ser somados como se fossem a mesma medida.
- Último backup, ausência de backup e idade superior a sete dias são sinais de revisão. Sete dias é uma janela explícita do painel, não um RPO acordado.
- O estado do backup usa os códigos do Longhorn 1.11.2 documentados no painel. Timestamps e estados não comprovam acesso ao destino, consistência da aplicação ou restauração testada.

O filtro é por volume Longhorn e inclui PVCs que não são discos de VMs. O dashboard não calcula automaticamente uma cobertura de backup por aplicação e não apresenta snapshots como espaço seguramente recuperável.

## VMware Imports (opcional)

Use o [módulo Imports](imports.md) para fases, falhas, discos prontos e intervalos registrados pelo VM Import Controller. Ele acompanha importação de VMware para Harvester, separadamente das métricas de live migration entre hosts.

## Referência e adaptação

A organização dos temas contenção, capacidade e proteção foi inspirada em [harvester-extra-dashboards, de doccaz](https://github.com/doccaz/harvester-extra-dashboards), revisão `e40bb3d751f0b2f0afa765ab7cf0a3afc4767c8d` (Apache-2.0). Este projeto implementa seus próprios painéis nativos SUSE; não importa os JSONs Grafana nem exige instalar Prometheus/Grafana adicional. Fórmulas, unidades e limites foram confrontados com as versões e fontes descritas nos [contratos de métricas](metric-contracts.md).
