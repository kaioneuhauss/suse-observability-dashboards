# Development

This page is for changing the project itself. **Users installing the charts do not need these tools or scripts.** The installation workflow is documented in the [README](../README.md) and uses kubectl and Helm.

## Repository layout

- `charts/`: five ready-to-install charts.
- `helm/`: packaged releases and `index.yaml`, served as the public Helm repository.
- `examples/`: minimal values files.
- `dev/components/`: shared collector and publisher sources; not a separate installation path.
- `dev/scripts/`: chart generation, dashboard editing and optional metric audits.
- `dev/tests/`: publisher, layout, metric contracts, module isolation and package integrity checks.

Edit shared sources in `dev/components/`, then regenerate the charts. Do not edit generated copies in `charts/` directly. Dashboard curation also generates `docs/panel-guide.md`.

Run development commands from the repository root.

## Build and check

```sh
python3 -m pip install -r dev/requirements-dev.txt
python3 dev/scripts/enhance-dashboards.py
python3 dev/scripts/build-virtualization-dashboards.py
python3 dev/scripts/curate-dashboards.py
python3 dev/scripts/build-charts.py
python3 -m unittest discover -s dev/tests -v
bash dev/tests/helm-checks.sh
```

When changing a release, bump its version in the builder and package the updated charts before running the package integrity test. The catalogs are disjoint: one module must not delete another module's content. The publisher checks identifiers, rejects collisions with native dashboards and compares the persisted definition.

## Publish chart packages

Never overwrite an existing version with different contents. Keep previous packages so users can remove or roll back that exact release. For example:

```sh
helm package charts/suse-observability-virtualization --destination helm
helm package charts/suse-observability-traefik --destination helm
helm package charts/suse-observability-applications --destination helm
helm package charts/suse-observability-kubernetes --destination helm
helm package charts/suse-observability-imports --destination helm
helm repo index helm
```

Commit the sources, packages and index together. CI checks package hashes and compares the current package with its source. After publication, check `helm repo update`, `helm search repo` and `helm pull --version` against the public URL. Packaging follows the [Helm repository format](https://helm.sh/docs/topics/chart_repository/).

The old combined profiles in `dev/tests/fixtures/legacy-profiles` are regression fixtures. They are not installation instructions. The former installer helper was removed; keep end-user guides on the direct Helm workflow.

## Optional metric audits

Backend acceptance does not prove that the SUSE API accepts the same syntax. In a test environment with real metrics, also check the native API. Use an authorized read token supplied through a private environment variable; never commit it:

```sh
python3 dev/scripts/audit-queries.py --native --url https://observability.example.com \
  --service-token-env SRE_AUDIT_TOKEN --range --output local/native-range.json
python3 dev/scripts/audit-queries.py --native --url https://observability.example.com \
  --service-token-env SRE_AUDIT_TOKEN --output local/native-filters.json
python3 dev/scripts/audit-http-totals.py --native --url https://observability.example.com \
  --service-token-env SRE_AUDIT_TOKEN --output local/native-http.json
```

These are read-only checks. `/api/metrics` is an internal API checked on SUSE 2.10.2, not a stable public integration contract. Reports contain environment names and should remain private. Review empty results and check the UI: HTTP 200 is not proof that a panel measures what its title says.

Static checks do not prove a deployment, failover or notification delivery. Record what actually ran and what did not in [Lab validation](../docs/lab-validation.md). Design references: [SRE monitoring signals](https://sre.google/sre-book/monitoring-distributed-systems/), [SLO alerts](https://sre.google/workbook/alerting-on-slos/) and [SUSE dashboards](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/dashboards/dashboards.html).
