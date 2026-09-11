# SUSE Observability content

Publishes the selected dashboards and monitors once in the central cluster. Two finite Helm hook Jobs use the SUSE API, then verify saved content.

1. Prepare [publisher access](../../prerequisites/PUBLISHER.md).
2. Copy [the short values profile](../../deploy/central/values.yaml) and set your SUSE URL and existing Secret names.
3. Follow [installation step C](../../README.md#c-dashboards-and-monitors-once-in-the-central-cluster).

Both Jobs may reference one approved Secret. Existing installations may retain separate owner credentials. `monitors.include: []` selects all project rules; use catalog slugs for a subset. Notifications remain manually configured in SUSE.

Root `values.yaml` contains complete defaults. `config/values.yaml` is the previous Fleet/lab example. The short profile is an override file, not a replacement for root defaults.

`helm uninstall` alone does not remove dashboards/monitors from SUSE. Run the [explicit deletion procedure](../../docs/UNINSTALL.md) first when that is your intent.
