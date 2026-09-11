# Small values files for a new installation

Copy the profile you need, change the example names/URLs, and pass it to Helm with `-f`. These files override the chart's complete `values.yaml`; they do not replace it. Requests and limits stay configured in the chart defaults.

| Profile | Chart | Install where |
|---|---|---|
| `cluster/values.yaml` | `sre-platform-telemetry` | Each Kubernetes cluster, including the server cluster if monitored |
| `harvester/values.yaml` | `sre-platform-telemetry` | Harvester; replaces the cluster profile for this target |
| `virtual-machines/values.yaml` | `sre-kubevirt-telemetry` | Harvester, once |
| `central/values.yaml` | `suse-observability-content` | Central SUSE server cluster, once |

The cluster profiles start with optional etcd and Traefik collection disabled. After the relevant [prerequisites](../prerequisites/README.md), enable the collectors that exist in your environment. Leaving one disabled means its metrics will not appear. Omit dashboards/monitors whose data sources you do not deploy.

For multiple downstream clusters, keep one local copy per target, for example `local/production/values.yaml` and `local/staging/values.yaml`. Use the exact Agent integration name, not necessarily your kubectl context name.

`local/` is ignored by Git. Keep credentials in Kubernetes Secrets or your vault. Files in `charts/*/config/` are the previous lab/Fleet examples; you do not need to edit them for the simple manual installation. Fleet uses only the files selected by its `valuesFiles`; see [Fleet setup](../docs/FLEET.md).

Start with the [installation steps](../README.md#3-install-the-charts).
