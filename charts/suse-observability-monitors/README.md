# suse-observability-monitors

Publish and verify 24 native SUSE monitors using a ConfigMap and a finite Helm hook Job. Install once per SUSE instance, after the required telemetry and Kubernetes topology exist.

Follow [installation](../../README.md#5-publish-the-monitors-once) and [publishing credentials](../../docs/PREREQUISITES.md#publishing-credentials). Start with [config/monitors.values.yaml](../../config/monitors.values.yaml).

## Values

| Value | Default | Meaning |
| --- | --- | --- |
| `observability.url` | Required | SUSE management API base URL |
| `auth.existingSecret` | `suse-observability-monitor-token` | Existing publishing token Secret |
| `auth.serviceTokenKey` | `serviceToken` | Secret field |
| `runner.image` | `python:3.12-alpine` | Publishing runner |
| `runner.downloadUrl` | CLI 3.3.6 Linux x86-64 archive | Pinned CLI download |
| `runner.caSecret` / `caKey` | Empty / `ca.crt` | Optional public CA bundle for SUSE |

## Permissions and lifecycle

The validated server requires `get-monitors`, `create-monitors`, `update-monitors` and `delete-monitors`. The import endpoint requires the three write permissions together, even though this Job does not delete monitors. Settings permissions and an administrator role are not required for this publisher.

These permissions apply to monitors across the instance; they are not restricted by repository name. The script limits what it applies. It preserves existing identifiers by exact name, fails on duplicate names and compares persisted definitions after import. A successful run reports `persisted_monitors: 24`.

The hook runs after install/upgrade, with a ten-minute deadline and one-day completed-Job TTL. It needs HTTPS access to the CLI download and SUSE API. Uninstall does not delete monitor objects already stored in SUSE. Reapply previous source through `helm upgrade` to restore earlier definitions.

## Customize and verify

Edit [scripts/generate-alerts.py](../../scripts/generate-alerts.py), then regenerate the catalog and STY files. The generated [catalog](../../alerts/catalog.json) includes the query, threshold, severity, description, remediation and topology mapping. Condition duration is expressed in PromQL windows rather than an unsupported `for` field.

Review thresholds against your workloads. TLS and Ingress mappings assume a Traefik DaemonSet; adapt them for Deployments or multiple ingress controllers. VM guest memory is associated with the hosting node and includes the VM identity in its title.

Confirm Enabled state and component association in SUSE. Notification channels and delivery tests are separate configuration. Successful Helm publication does not prove that an email or webhook reaches a recipient.
