# Multiple clusters

You do not need a dashboard copy for each cluster. Publish each module once per SUSE Observability instance. Its filters will show the clusters sending data.

| Mode | What it installs | Where it runs |
|---|---|---|
| `all` (default) | Collectors, dashboards and monitors | First monitored cluster |
| `telemetry` | Collectors only | Other monitored clusters |
| `content` | Dashboards and monitors only | One central publishing cluster |

Applications always uses `content`. Keep one publishing release per module and SUSE instance. Two `all` releases would both manage the same external dashboards.

## 1. Add another monitored cluster

If you already installed Traefik with `all` on your first cluster, save this as `traefik-second.yaml`:

```yaml
mode: telemetry
clusterName: second-cluster
observability:
  url: https://observability.example.com
```

Install on the second cluster, using the Agent's namespace and ingestion Secret there:

```sh
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.6.0 --values traefik-second.yaml \
  --kubeconfig /path/to/second-cluster.yaml --kube-context second-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** the collectors are ready and no publishing Jobs run.

No publishing token is needed on this cluster. Follow the module's normal checks; the cluster will appear in dashboard filters when its metrics arrive. For Virtualization, also include `observability.otlpEndpoint` and complete its registry/network prerequisites.

## 2. Optional: keep publishers on a central cluster

Use `mode: telemetry` in every source cluster. For each central module, save a file like `traefik-content.yaml`:

```yaml
mode: content
observability:
  url: https://observability.example.com
```

Create the publishing Secret in the central namespace, then install:

```sh
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.6.0 --values traefik-content.yaml \
  --kubeconfig /path/to/central.yaml --kube-context central \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports `deployed` and the dashboard appears in SUSE. No collector Pods remain in this central release. Successful publishing Jobs are removed automatically.

A central publisher does not need an Agent, ingestion Secret, `clusterName`, KubeVirt CA or OTLP endpoint. Its namespace must exist; if creating a dedicated one, use `kubectl create namespace` with that central kubeconfig and context before creating its Secret.

Use a separate values file per module and destination. Keep the same release name and namespace when updating. To remove everything, uninstall each source collector and delete the central content once, following [removal](lifecycle.md).

## 3. Remove a module from multiple clusters

Run the module's `helm uninstall` command once in each source cluster, using its own kubeconfig, context and namespace. Then run it once for the central publisher. Keep the central publishing token available until that last command succeeds. [Full removal steps](lifecycle.md).

**Expected result:** source collectors are gone and the central dashboard is removed. Other modules and monitored workloads stay in place.

## Already using Fleet?

The charts can be referenced by Fleet, but the tutorial here uses Helm directly. Do not let Fleet and a manual Helm installation manage the same release. Any Fleet setup needs its own target and ownership checks; it was not deployed as part of this lab validation.
