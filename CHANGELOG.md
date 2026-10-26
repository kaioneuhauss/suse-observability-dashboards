# Módulos 1.2.0 — revisão de leitura e instalação

- Nove dashboards em inglês, organizados por perguntas práticas e seções de leitura.
- Revisão de 161 painéis: títulos, explicações iniciais, unidade, precisão e papel no diagnóstico.
- Contagens inteiras; taxas e percentuais mantêm a precisão apropriada sem arredondar os dados de origem.
- Visão geral de VMs reduzida; performance, capacidade e storage têm visões dedicadas.
- Estados de volumes resumidos por quantidade; códigos de backup e fases de importação com nomes legíveis.
- Histórico de erros Traefik por intervalo efetivo, preservando as estimativas de contadores.
- Consultas HTTP compatíveis com o parser SUSE, auditadas pela API nativa e em três resoluções.
- Correção de links herdados que podiam abrir a consulta de outro painel.
- `scripts/pack.sh` oferece configure/check/install/status/remove com destino explícito e backup na remoção.
- Nome da integração descoberto a partir do Agent; configuração mínima preserva Secrets existentes.
- README e pré-requisitos reescritos para instalação, verificação, remoção e repetição do procedimento.
- Versões, evidências e limites de validação em `docs/lab-validation.md`.

## Módulos 1.1 / Imports 1.0

- Três visões adicionais de Virtualization e módulo independente VM Import Controller.
- Validação de unidades Longhorn/KubeVirt e totais HTTP por resolução de consulta.
- Coriolis fora do escopo desta entrega.

# Módulos 1.0.0 — 26 de outubro de 2026

- Quatro charts independentes: Virtualization, Traefik, Aplicações e Kubernetes.
- Values mínimos, modos all/telemetry/content e catálogos de conteúdo disjuntos.
- Remoção dos guias/PDFs concorrentes; um procedimento por módulo.
- Sincronização da CA pública KubeVirt com RBAC limitado e sem cópia manual.
- Coleta Longhorn opcional, com NetworkPolicy restrita somente por opção explícita.
- p99, conexões, disponibilidade por requisição, orçamento de erro, atualidade das amostras e saúde da coleta.
- Layout de triagem compacto e contratos HTTP configuráveis sem depender de status_class.
- 34 monitores; novo monitor de falha de coleta Virtualization.
- Instalação limpa nos três ambientes, testes de regressão e consultas reais; limites em docs/lab-validation.md.

## Histórico

Os procedimentos da versão 6 foram substituídos. Consulte a revisão `c059f58` no Git para recuperar o pacote anterior e suas evidências históricas.
