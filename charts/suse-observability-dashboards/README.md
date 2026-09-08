# suse-observability-dashboards

Publish five native SUSE Observability dashboards from a ConfigMap through a finite Helm hook Job. Install once per SUSE instance. The metrics must already be collected; this chart is not a Grafana installation.

Follow [installation and credentials](../../README.md#4-publish-the-dashboards-once). Use [config/dashboards.values.yaml](../../config/dashboards.values.yaml) as your starting template.

## Main values

| Value | Default | Meaning |
| --- | --- | --- |
| `observability.url` | Required | SUSE management API base URL |
| `auth.existingSecret` | `suse-observability-dashboard-token` | Publishing token Secret in release namespace |
| `auth.serviceTokenKey` | `serviceToken` | Secret field |
| `runner.caSecret` / `caKey` | Empty / `ca.crt` | Optional CA to verify SUSE |
| `runner.cli.version` | `3.3.6` | Tested CLI version |
| `runner.cli.downloadUrl` | Pinned Linux x86-64 archive | CLI downloaded by the hook |
| `runner.activeDeadlineSeconds` | `300` | Job deadline |
| `runner.ttlSecondsAfterFinished` | `86400` | Completed Job retention |
| `dashboards.enabled` | `true` | Enable publication |
| `dashboards.includeTraefik` | `true` | Include the Traefik dashboard |
| `dashboards.legacyNames` | Declared aliases in values | Old names considered during reconciliation |
| `traefikMetrics.enabled` | `false` | Legacy collection option; keep disabled and use the telemetry chart |

See [values.yaml](values.yaml) for image, resource and pod metadata options. The Job needs network access to the CLI download and SUSE API; default binaries require x86-64. A CA Secret must contain the public certificate bundle, not a private key.

## Upgrade and ownership

The hook runs after install and upgrade. With the validated CLI, applying an existing ID did not reliably replace the full Perses definition. The publisher therefore finds managed names or declared aliases, deletes that matching dashboard and creates the complete source definition. **IDs can change and manual edits are overwritten.** Export these dashboards before an upgrade if those edits must be preserved.

The chart is the source of truth for its managed names. Avoid duplicate dashboards with identical names. It does not intend to replace unrelated built-in dashboards. Verify the persisted definitions after publication.

Helm rollback alone does not run the publishing hook. Reapply the prior chart through `helm upgrade` or restore exported definitions. Uninstall removes Kubernetes resources but does not automatically remove SUSE dashboard objects.

## Customize

Edit [presentation-en.yaml](tools/presentation-en.yaml) for titles/descriptions and [generate_dashboards.py](tools/generate_dashboards.py) for queries, units or layout. Run the generator from the repository, review its YAML changes and validate before upgrading. Generated definitions are already included for first-time installation.
