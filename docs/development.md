# Desenvolvimento

- `charts/`: cinco charts independentes prontos para instalar.
- `examples/`: cinco values mínimos.
- `components/`: fontes compartilhadas dos coletores e publicador; uso de desenvolvimento/migração.
- `scripts/build-charts.py`: gera cópias autocontidas, filtra dashboards/monitores e aplica schemas.
- `scripts/enhance-dashboards.py`: painéis SRE adicionais baseados no schema nativo exportado.
- `scripts/curate-dashboards.py`: titulos, explicacoes, formatos e organizacao dos 161 paineis; gera `docs/panel-guide.md`.
- `scripts/pack.sh`: fluxo do usuario (configure/check/install/status/remove), sem Python local.
- `tests/`: regressões do publicador, layout, recursos e isolamento dos módulos.

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/enhance-dashboards.py
python3 scripts/build-virtualization-dashboards.py
python3 scripts/curate-dashboards.py
python3 scripts/build-charts.py
python3 -m unittest discover -s tests -v
bash tests/helm-checks.sh
for module in virtualization traefik applications kubernetes imports; do
  helm lint "charts/suse-observability-$module" --strict -f "examples/$module.yaml"
  helm package "charts/suse-observability-$module" --destination /tmp/helm-packages
done
```

Não edite as cópias geradas em `charts/` diretamente. Altere as fontes em `components/` e gere novamente. Os cinco catálogos são disjuntos; um módulo nunca exclui regras do outro. O publicador verifica nomes/identificadores, recusa colisões com dashboards nativos e compara os objetos persistidos.

Os arquivos de configurações antigas em `tests/fixtures/legacy-profiles` servem somente para regressão; não são o fluxo de instalação. Os guias e PDFs antigos foram removidos para evitar procedimentos concorrentes. O histórico Git preserva as revisões anteriores.

A validação estática não prova deploy. A evidência de ambiente está em [lab-validation.md](lab-validation.md), com limites explícitos. Referências de desenho: [quatro sinais SRE](https://sre.google/sre-book/monitoring-distributed-systems/), [alertas por SLO](https://sre.google/workbook/alerting-on-slos/), [dashboards SUSE](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/dashboards/dashboards.html).

## Auditar as consultas pela API usada pelo produto

O backend pode aceitar sintaxe que a API do SUSE rejeita. Em um ambiente de teste com dados reais, valide também o caminho nativo. Use um token existente autorizado a ler métricas, sem gravá-lo no repositório:

```bash
read -r -s -p 'Token SUSE para leitura: ' SRE_AUDIT_TOKEN; echo
export SRE_AUDIT_TOKEN
python3 scripts/audit-queries.py --native --url "$OBS_URL" \
  --service-token-env SRE_AUDIT_TOKEN --range --output local/native-range.json
python3 scripts/audit-queries.py --native --url "$OBS_URL" \
  --service-token-env SRE_AUDIT_TOKEN --output local/native-filters.json
python3 scripts/audit-http-totals.py --native --url "$OBS_URL" \
  --service-token-env SRE_AUDIT_TOKEN --output local/native-http.json
unset SRE_AUDIT_TOKEN
```

Esses testes fazem somente leituras. A API interna `/api/metrics` foi conferida no SUSE 2.10.2 e pode mudar; não é um contrato público de integração. Os relatórios contêm nomes do ambiente e devem permanecer privados. Revise resultados vazios e faça a conferência visual: um HTTP 200 não prova que a métrica represente o que o título promete.
