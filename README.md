# SUSE Observability dashboards

Pick a module, fill in its settings and install it with Helm. Each module adds its own dashboards and monitors. The modules that need extra metrics also install their collectors.

> [!WARNING]
> Community project for labs and learning. **Not recommended for production and not an officially supported SUSE integration.** Review the measurements and alert thresholds before relying on them. Notification channels are not configured by these charts.

You only need **Helm, kubectl and a text editor**. No repository clone, local Bash/Python scripts or Grafana installation. The examples below cover the first module, a second module, updates and removal.

## 1. Choose what to install

| Module | Use it when you have | Dashboards | Monitors |
|---|---|---:|---:|
| [virtualization](#install-virtualization) | SUSE Virtualization / Harvester | 4: VMs, performance, capacity, storage & backups | 7 |
| [imports](#install-imports) | Harvester VM Import Controller | 1: VMware import progress and optional infrastructure performance | 3 |
| [kubernetes](#install-kubernetes) | Kubernetes / RKE2 | 2: cluster health and application resources | 21 |
| [traefik](#install-traefik) | Traefik with Prometheus metrics | 1: incoming traffic, errors and speed | 6 |
| [applications](#install-applications) | Applications already sending HTTP metrics | 1: application traffic, errors and speed | 2 |

**Only need SUSE Virtualization?** Complete steps 2–4, install option A, then check it in step 6. You can stop there. Imports is a separate, optional module. Coriolis is not included.

**What “from zero” means here:** no dashboard components are installed yet. You still need an existing Harvester/Kubernetes cluster and a working SUSE Observability server. Server sizing, licensing, storage, DNS, certificates and application instrumentation are separate prerequisites. These charts do not create those platforms. For a new SUSE server, complete the [official server installation](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/kubernetes_install.html) first.

## 2. Write down your environment details

Replace these examples throughout the commands and YAML. Keep the files in a private folder outside Git.

| Fill in | Example | Where to find it |
|---|---|---|
| Kubeconfig file | `/path/to/cluster.yaml` | Download from Rancher or Harvester |
| Kubeconfig context | `my-cluster` | First command below |
| Agent namespace | `suse-observability` | Existing Agent release; use this for a new Agent in this guide |
| Integration name | `my-cluster` | Kubernetes StackPack in SUSE; may differ from the context |
| SUSE URL | `https://observability.example.com` | Address you use to open SUSE |
| OTLP endpoint, Virtualization only | `otlp-observability.example.com:443` | TLS gRPC endpoint configured on the SUSE server |

Install [kubectl](https://kubernetes.io/docs/tasks/tools/) and [Helm 3 or 4](https://helm.sh/docs/intro/install/). Use a kubectl version compatible with your cluster. Check access and existing releases:

```sh
kubectl config get-contexts --kubeconfig /path/to/cluster.yaml
kubectl get nodes --kubeconfig /path/to/cluster.yaml --context my-cluster
helm list --all-namespaces --kubeconfig /path/to/cluster.yaml --kube-context my-cluster
```

**Check:** these are the intended nodes. If a module already exists, keep its release name, namespace, publishing identity and values file. The install command will update it. Do not install a second copy.

## 3. Prepare the Agent and credentials once

All modules in the same namespace reuse these prerequisites. Applications needs only the publishing credential and existing application metrics.

### Connect the cluster to SUSE

If the official Agent is already installed, keep it and use the checks below. Otherwise, open **SUSE Observability → StackPacks → Kubernetes → Add new instance**. Choose a unique integration name and obtain the ingestion Service Token. Save the token as `/private/ingestion-token.txt`, with no extra spaces or trailing newline.

Save `agent.yaml`, using the receiver URL from your instance:

```yaml
stackstate:
  cluster:
    name: my-cluster
  url: https://observability.example.com/receiver/stsAgent
```

Replace `AGENT_CHART_VERSION` with the version offered by your Kubernetes integration. Keep any additional values required by that integration/version.

```sh
helm repo add suse-observability https://charts.rancher.com/server-charts/prime/suse-observability
helm repo update suse-observability
helm upgrade --install suse-observability-agent suse-observability/suse-observability-agent \
  --version AGENT_CHART_VERSION --values agent.yaml \
  --set-file stackstate.apiKey=/private/ingestion-token.txt \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --create-namespace --wait --timeout 15m
```

The field is called `apiKey` but accepts the ingestion Service Token. Helm stores these values in release Secrets; restrict access to the namespace. Do not enable another Agent through a Harvester add-on as well.

Check the Agent, integration name and ingestion Secret **without printing its credential**:

```sh
kubectl get pods --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
kubectl get configmap suse-observability-agent-cluster-name \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability \
  -o jsonpath='{.data.STS_CLUSTER_NAME}{"\n"}'
kubectl get secret suse-observability-agent-secrets \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability \
  -o go-template='{{range $key, $value := .data}}{{$key}}{{"\n"}}{{end}}'
```

**Check:** Agent Pods are ready, you know the integration name, and the Secret contains `STS_API_KEY`. Nodes and Pods must appear in SUSE. Use that integration name as `clusterName` below. With a custom Agent release, find the equivalent ConfigMap/Secret in its configuration.

### Create the publishing Secret

For Applications without an Agent in this cluster, first check that the publishing namespace exists with `kubectl get namespace suse-observability --kubeconfig /path/to/cluster.yaml --context my-cluster`. Only if it is absent, create it:

```sh
kubectl create namespace suse-observability \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

Ask the SUSE administrator for a **Service Token allowed to read, create, update and delete dashboards and monitors**. The ingestion credential cannot publish dashboards. See [SUSE Service Tokens](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/security/k8s-service-tokens.html).

Save it as `/private/publisher-token.txt`, containing only the token, without a trailing newline. Create the Secret once:

```sh
kubectl create secret generic suse-observability-publisher-token \
  --from-file=serviceToken=/private/publisher-token.txt \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

**Check:** the Secret is created in the Agent namespace. If it already exists, reuse the existing publisher identity; do not replace it. Store credentials in your approved secret store and remove the temporary local token files when done.

<details>
<summary>Different Secret names or a private certificate authority?</summary>

Add overrides to each module's values file when needed:

```yaml
ingestion:
  existingSecret: your-agent-secret
  secretKey: STS_API_KEY
auth:
  dashboards:
    existingSecret: your-dashboard-publisher-secret
    serviceTokenKey: serviceToken
  monitors:
    existingSecret: your-monitor-publisher-secret
    serviceTokenKey: serviceToken
```

Keep the identity that owns existing dashboards; another token can receive 403 even with similar permissions. `mode: content` and Applications do not need ingestion credentials.

For a private CA, create its Secret:

```sh
kubectl create secret generic observability-ca --from-file=ca.crt=/private/ca.crt \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

For Virtualization, add:

```yaml
content:
  publisher:
    caSecret: observability-ca
telemetry:
  remoteWrite:
    caSecret: observability-ca
virtualization:
  otlp:
    caSecret: observability-ca
```

Applications needs only `content.publisher`. Kubernetes/Traefik need `content.publisher` and `telemetry.remoteWrite`. Imports needs `content.publisher` and `imports.remoteWrite`. Keep certificate verification enabled.

</details>

## 4. Add the dashboard repository

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

**Check:** Helm confirms the repository was updated. Do this once on your computer. Collectors need DNS and network access to SUSE and their image registries. Publishing Jobs run on Linux amd64, download the pinned official SUSE CLI over HTTPS and verify its checksum.

## 5. Install the module you chose

Save YAML using your text editor. The defaults use the Secret names from step 3. Keep each module's own values file. **Use only the option you need; installing every module is not required.**

<a id="2-fill-in-your-settings--harvester-example"></a>
<a id="install-virtualization"></a>

### A. SUSE Virtualization

Before installing, check the Harvester services and public CA:

```sh
kubectl get service kubevirt-prometheus-metrics --namespace harvester-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get configmap kubevirt-ca --namespace harvester-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get service longhorn-backend --namespace longhorn-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get networkpolicy --namespace longhorn-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

**Check:** services and CA exist. The collector refreshes the public KubeVirt CA automatically. The nodes must allow Linux host collectors with host networking and read-only host mounts.

Create an Application Collection image-pull Secret from your private Docker authentication file, if it does not already exist:

```sh
kubectl create secret generic application-collection \
  --type=kubernetes.io/dockerconfigjson --from-file=.dockerconfigjson=/private/config.json \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

Your account must have access to `dp.apps.rancher.io`. Obtain the authentication file through your registry's credential setup. The other modules do not require this Secret by default.

The SUSE server also needs a reachable **OTLP gRPC endpoint with a valid TLS certificate**. This is separate from its UI URL. If it is missing, complete [Set up OTLP access](docs/otlp.md) on the **SUSE server cluster**, then return here. That guide includes the server Helm values and commands; DNS and certificate issuance depend on your infrastructure. Do not point the collector at the UI hostname unless it really serves OTLP.

Save `virtualization.yaml` with these three settings:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
  otlpEndpoint: otlp-observability.example.com:443
```

Only if existing policies already isolate Longhorn managers and block collection, add:

```yaml
virtualization:
  longhorn:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

This allows TCP/9500 only from this collector's namespace and Pod labels. The port also serves the Longhorn API. Do not add the first isolation policy blindly: it could block platform traffic. To skip storage collection, set `virtualization.longhorn.enabled: false`; storage panels will have no data.

Install:

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.5.0 --values virtualization.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Check:** Helm reports `deployed`. Open the four **Virtualization** dashboards in SUSE. Continue to step 6.

<a id="install-imports"></a>

### B. Imports — a complete second-module example

Suppose Virtualization is already installed and you now want to follow VMware imports. **Keep `obs-virtualization` installed.** Reuse the Agent, namespace, credentials and Helm repository. Create a separate `imports.yaml` and install a separate release called `obs-imports`.

VM Import Controller must be enabled. Check:

```sh
kubectl get crd virtualmachineimports.migration.harvesterhci.io \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get virtualmachineimports.migration.harvesterhci.io --all-namespaces \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

If its existing add-on is disabled, enable `spec.enabled` while preserving the other fields:

```sh
kubectl edit addons.harvesterhci.io vm-import-controller --namespace harvester-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

Follow the [Harvester VM Import guide](https://docs.harvesterhci.io/v1.8/advanced/addons/vmimport/) for source/target preparation and actual imports. Enabling the add-on does not start a migration. Save `imports.yaml`:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
imports:
  performance:
    enabled: true
```

`performance.enabled: true` adds CPU, memory and network measurements for the controller and shared image services. It grants read-only Nodes and `nodes/metrics` access over TLS/10250, with a 512 MiB writer memory limit. These shared services are **not per-VM transfer progress, throughput or ETA**. Set it to `false` for inventory only, without kubelet access. No vCenter credentials are read.

```sh
helm upgrade --install obs-imports obs-dashboards/suse-observability-imports \
  --version 1.5.0 --values imports.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Check:** the new dashboard **Virtualization · VMware Import Progress** appears alongside the existing four. Both releases remain listed. This module also works without the Virtualization chart, after the common prerequisites.

<a id="install-kubernetes"></a>

### C. Kubernetes / RKE2

Requires the official Agent and Linux nodes that allow host networking and read-only host mounts. Save `kubernetes.yaml`:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
```

**Virtualization already installed on this cluster?** Add `mode: content` at the top of this file. It reuses Virtualization's host and Pod inventory collectors; installing both sets would duplicate data and conflict on host ports.

```sh
helm upgrade --install obs-kubernetes obs-dashboards/suse-observability-kubernetes \
  --version 1.5.0 --values kubernetes.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Check:** the two **Kubernetes** dashboards appear. With `mode: content`, no extra collector workloads are expected.

etcd collection is off by default. If your administrator confirms `http://127.0.0.1:2381/metrics` is available on nodes labeled `node-role.kubernetes.io/etcd=true`, add `telemetry.etcd.enabled: true` as nested YAML to the release owning host collection and repeat its install command. The chart does not expose that port. Without collection, etcd panels and monitors have no samples; this is not a healthy result.

**Installing Virtualization after Kubernetes?** First add `mode: content` to `kubernetes.yaml` and repeat its command. This removes the duplicated host collectors. Then install Virtualization. There will be a collection gap until Virtualization is ready. Keep both values files.

<a id="install-traefik"></a>

### D. Traefik

Traefik must already expose Prometheus metrics internally. The default collector finds `app.kubernetes.io/name=rke2-traefik` in `kube-system`, port 9100.

<details>
<summary>Enable metrics on an existing RKE2 Traefik installation</summary>

Check the owner and current configuration:

```sh
kubectl get helmchart,helmchartconfig --namespace kube-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

For a directly managed RKE2 installation, merge these values into `spec.valuesContent` of the existing `rke2-traefik` HelmChartConfig using `kubectl edit`. **Preserve its other settings.** If none exists, save `traefik-metrics.yaml`:

```yaml
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: rke2-traefik
  namespace: kube-system
spec:
  valuesContent: |-
    metrics:
      prometheus:
        entryPoint: metrics
        addEntryPointsLabels: true
        addServicesLabels: true
    ports:
      metrics:
        port: 9100
        expose:
          default: false
```

```sh
kubectl apply --filename traefik-metrics.yaml \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

For Rancher/Fleet ownership, change the owning chart values instead. For a standalone Helm installation, merge the metrics/ports blocks into its existing values and upgrade Traefik using its installed chart version. This can restart Traefik; check application access afterward. Metrics stay internal. See [RKE2 configuration](https://docs.rke2.io/helm/) and [Traefik metrics](https://doc.traefik.io/traefik/observability/metrics/prometheus/).

</details>

Save `traefik.yaml`:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
```

For another namespace/selector, add `telemetry.traefik.namespace`, `selector`, `port` and `targetPort` using the real workload settings; see the [Traefik example](docs/traefik.md#3-fill-in-your-settings).

```sh
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.5.0 --values traefik.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Check:** **Traefik · Incoming Traffic & Errors** appears and its collection panel is 1 for discovered targets.

<a id="install-applications"></a>

### E. Applications

The application must already send these metrics to SUSE. Traces alone are not enough. Instrumentation is application-specific; follow the [SUSE OpenTelemetry guide](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/setup/otel/getting-started/getting-started-k8s.html).

| Signal | Expected metric / labels |
|---|---|
| Requests | `http_server_requests_total` |
| Duration histogram in seconds | `http_server_request_duration_seconds_bucket`, `_sum`, `_count` |
| Identity | `cluster_name`, `service_name`, `namespace` |
| HTTP details | `http_route`, `http_response_status_code` |

Check those names in Metrics Explorer. Use normalized routes, such as `/orders/{id}`. For a different contract, use [the application metric overrides](docs/applications.md#optional-different-metric-names); the chart cannot infer it.

Save `applications.yaml`:

```yaml
observability:
  url: https://observability.example.com
```

```sh
helm upgrade --install obs-applications obs-dashboards/suse-observability-applications \
  --version 1.5.0 --values applications.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Check:** **Applications · Traffic, Errors & Speed** appears. This module publishes content only; it has no collector Pods and does not need an ingestion Secret.

## 6. Check the installation

```sh
helm list --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability
kubectl get deployment,daemonset,pods \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

**Expected:** your releases are `deployed` and their collectors are ready. Successful publishing Jobs disappear automatically. Failed Jobs remain for investigation.

| Release / mode | Collector workloads expected |
|---|---|
| `obs-virtualization`, all | Deployment `obs-virtualization`, Deployment `obs-virtualization-pods`, DaemonSet `obs-virtualization-node` |
| `obs-imports`, all | Deployment `obs-imports-imports` |
| `obs-kubernetes`, all | Deployment `obs-kubernetes-pods`, DaemonSet `obs-kubernetes-node` |
| `obs-traefik`, all | Deployment `obs-traefik-traefik`; no host DaemonSet |
| Applications or any `content` release | None |

In SUSE, open **Dashboards → All**, choose your module and select the cluster. Allow a few minutes for fresh samples. Check collection first, then compare a known resource with the source:

- Virtualization: compare running VM names with Harvester. Storage details identify the PVC namespace, PVC and Longhorn volume.
- Imports: compare retained import records with kubectl. No active imports means performance is infrastructure activity, not an active transfer test.
- Kubernetes: use the named Pod lists and **Open values table → Table** to inspect every match, including entries outside the first 10.
- Traefik/Applications: compare a known application's requests and errors. No traffic or missing data is not proof of availability.

**No data is not zero or healthy.** If Helm fails, inspect `kubectl get jobs` and `kubectl logs job/JOB_NAME` with the same kubeconfig, context and namespace. Check the publishing identity, DNS/TLS and ingestion credentials. Do not reinstall repeatedly to hide an error. See [validation and troubleshooting](docs/validation.md).

### What about alerts?

The charts install **39 monitors** across all five modules. Virtualization includes VM pressure, collection failures and degraded/faulted PVC-backed Longhorn volumes. Imports includes failed/invalid records, inventory failure and optional performance collection failure. The Kubernetes, Traefik and Applications modules add their own checks.

They are starting points, not complete incident coverage. Virtualization alone does not include Kubernetes host-memory/etcd monitors. Backup age, missing backups, import duration and bandwidth need your own recovery/performance policies. Not every graph should create an alert. See [alert coverage and limits](docs/alerts.md).

Open **Monitors** in SUSE and review the `SRE ·` rules. Notification channels/routing must be configured separately in SUSE. A published monitor is not proof that an email or other notification reaches someone.

## 7. Add the same module to another cluster

Each module's dashboards and monitors are published **once per SUSE instance**. They already have cluster selectors. To add another cluster, prepare its Agent and ingestion Secret, copy the module's values file and set its new integration name plus:

```yaml
mode: telemetry
```

For example, save `virtualization-second.yaml` with `mode: telemetry`, the second cluster's `clusterName`, SUSE URL and OTLP endpoint. Create its image-pull Secret and check Longhorn access as in option A. Install only collectors there:

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.5.0 --values virtualization-second.yaml \
  --kubeconfig /path/to/second-cluster.yaml --kube-context second-cluster \
  --namespace suse-observability --wait --timeout 15m
```

This release needs no publishing token. It adds the second cluster to the existing filters after metrics arrive. Keep a record of **which cluster/release owns publication**. Removing that publishing release removes the shared dashboards for every source cluster. Removing a telemetry release removes only that cluster's collectors. Applications has no telemetry mode. See [multiple clusters](docs/multiple-clusters.md) for central publication.

## 8. Update or reinstall

Keep each values file and any optional settings you added. To change configuration, edit the appropriate file and repeat **that module's** install command. To adopt a new version, update the repository, review its changelog and change `--version` explicitly. An uninstall followed by the same install command is a reinstall.

Before a change, save the output of this command in a private file using your editor (replace the release name for other modules):

```sh
helm get values obs-virtualization \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability
```

The publishing release owns the managed dashboards: Helm updates can replace their definitions and IDs. Keep personal edits in a separate dashboard copy. For chart versions older than 1.3.0, follow the [upgrade/removal notes](docs/lifecycle.md#moving-from-120-or-121).

## 9. Remove one module or all modules

### Remove only an additional module

For example, to remove Imports and keep Virtualization:

```sh
helm uninstall obs-imports \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Check:** `obs-imports` disappears from `helm list`; its dashboard and three monitors are removed. The four Virtualization dashboards remain. VM Import Controller and import records remain too.

### Remove all installed modules

First list your releases with the command in step 6. Run **only** the commands for releases you actually installed, on the cluster and namespace where each one lives. Keep the publishing Secret and SUSE API available until removal finishes.

```sh
helm uninstall obs-imports \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
helm uninstall obs-applications \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
helm uninstall obs-traefik \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
helm uninstall obs-kubernetes \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
helm uninstall obs-virtualization \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

Each command also works for removing that module individually. **One dependency to remember:** Kubernetes in `content` mode reuses Virtualization collectors. If you remove Virtualization but keep Kubernetes, first remove Virtualization, then change `kubernetes.yaml` to `mode: all` and repeat its install command. This restores host collection with a brief gap.

For multiple clusters, remove telemetry releases on their own clusters first. Remove the publishing release only when no source cluster still needs its shared dashboards.

### Confirm removal

```sh
helm list --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability
kubectl get deployment,daemonset,jobs \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

**Expected:** the selected releases and their collector workloads are gone; their managed dashboards and monitors disappear from SUSE. Old metric history remains until normal retention expires. Applications, VMs, PVCs, volumes, the SUSE server and official Agents stay in place. Shared Secrets and platform prerequisites also stay in place. **Do not delete the namespace.**

If uninstall fails, inspect the remaining Job and fix API access, TLS or token ownership, then repeat the same command. Do not bypass cleanup with `--no-hooks`. With custom `lifecycle.deleteOnUninstall: false`, remote dashboards intentionally remain; see [lifecycle recovery](docs/lifecycle.md#3-if-removal-fails).

The project does not remove Agent credentials, Traefik configuration, the import controller or the server's OTLP endpoint because other integrations may use them. To remove the **dedicated publishing Secret**, first confirm every release using it is gone, then run:

```sh
kubectl delete secret suse-observability-publisher-token \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

Skip that final command if the Secret is shared with anything else. Recreate it through step 3 when reinstalling.

## More details

The README covers the standard dashboard installation and removal. Environment-specific platform setup still belongs to its owner; linked guides cover those exceptions instead of assuming that every cluster uses the same DNS, CA, ingress or instrumentation.

- [Virtualization walkthrough](docs/virtualization.md) · [OTLP setup](docs/otlp.md) · [Common prerequisites](docs/prerequisites.md)
- [Dashboard reading guide](docs/panel-guide.md) · [Metric definitions](docs/metric-contracts.md) · [Alerts](docs/alerts.md)
- [Validation](docs/validation.md) · [Lab results and limits](docs/lab-validation.md) · [Changelog](docs/changelog.md)

`examples/` contains small values files. `charts/` contains chart source; `helm/` contains the packages Helm downloads. `dev/` is only for maintainers. The Virtualization topics were inspired by [doccaz/harvester-extra-dashboards](https://github.com/doccaz/harvester-extra-dashboards); these are native SUSE dashboards.
