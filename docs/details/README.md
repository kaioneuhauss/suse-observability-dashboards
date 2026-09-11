# Technical details

Start with the [customer procedure](../GUIA-HELM-FLEET.md) or [short study guide](../GUIA-ESTUDO.md). Use this directory when you need to understand or change the implementation.

| Topic | Document |
|---|---|
| Chart internals, metric sources, query design and customization | [Implementation reference](IMPLEMENTATION.md) |
| Restricted publisher roles, ownership, backup, CA/SAN checks | [Operations reference](OPERATIONS.md) |
| Complete configuration examples and original lab deployment | [Deployment reference](DEPLOYMENT-REFERENCE.md) |
| CPU, memory, storage, retention, formulas and security boundaries | [Detailed measurements](MEASUREMENTS.md) |
| Which panels have which monitors | [Alert coverage](../ALERT-COVERAGE.md) |
| Every request and recorded validation | [Acceptance matrix](../../tests/MATRIZ-SOLICITACOES.md) |

The original lab examples use its cluster names and two restricted publisher identities. They are reference material, not fields every new client must reproduce. For a new installation, use the short `deploy/*/values.yaml` profiles and the [one-token setup](../../prerequisites/PUBLISHER.md) if the client's access policy allows that default role.
