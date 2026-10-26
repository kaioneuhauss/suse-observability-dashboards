# Desenvolvimento

- `charts/`: cinco charts independentes prontos para instalar.
- `examples/`: cinco values mínimos.
- `components/`: fontes compartilhadas dos coletores e publicador; uso de desenvolvimento/migração.
- `scripts/build-charts.py`: gera cópias autocontidas, filtra dashboards/monitores e aplica schemas.
- `scripts/enhance-dashboards.py`: painéis SRE adicionais baseados no schema nativo exportado.
- `tests/`: regressões do publicador, layout, recursos e isolamento dos módulos.

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/enhance-dashboards.py
python3 scripts/build-virtualization-dashboards.py
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
