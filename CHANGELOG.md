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
