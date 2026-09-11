# sre-kubevirt-telemetry

Chart customizado de coleta complementar. Configuracao em `values.yaml`, exemplos em `deploy/`. Instale uma release por origem/cluster, no namespace do Agent, reutilizando somente referencias de Secret.

Executa um unico OTel Collector para KubeVirt e envia OTLP gRPC. Nao e o chart oficial upstream. Antes crie a copia publica da CA no namespace do Agent e tenha o imagePullSecret. Nao instale outro Collector equivalente em paralelo.

Observe nao significa coleta sem filtros: a allowlist continua ativa, assim como limites de recursos e filas. Enforce deve ser habilitado somente depois do baseline. Em indisponibilidade longa do receptor pode haver perda de telemetria. Charts/containers novos exigem teste em lab e nao recebem suporte oficial automaticamente por usarem APIs documentadas.

Veja `docs/GUIA-HELM-FLEET.md` para pre-requisitos, comandos e criterios de aceite.
