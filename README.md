# SUSE Observability dashboards

Pick a module, fill in its settings and install it with Helm. Each module adds its own dashboards and monitors. The modules that need extra metrics also install their collectors.

> [!WARNING]
> Community project for labs and learning. **Not recommended for production and not an officially supported SUSE integration.** Review the measurements and alert thresholds before relying on them. Notification channels are not configured by these charts.

You only need **Helm, kubectl and a text editor**. No repository clone, local Bash/Python scripts or Grafana installation. The examples below cover the first module, a second module, updates and removal.

**Start here:** choose a module → prepare its prerequisites → save its values file → run Helm → check fresh data. Follow only the sections for your module. Browser steps are needed to create integrations and obtain credentials; Helm and kubectl handle the Kubernetes installation.

Want to understand what each step does? Read the [configuration walkthrough](docs/configuration-guide.md). It explains the architecture, the lab configuration, every chart setting, dashboard creation and removal.

## 1. Choose what to install

| Module | Use it when you have | Dashboards | Monitors |
|---|---|---:|---:|
| [virtualization](#install-virtualization) | SUSE Virtualization / Harvester | 4: VMs, performance, capacity, storage & backups | 7 |
| [imports](#install-imports) | Harvester VM Import Controller | 1: VMware import progress and optional infrastructure performance | 3 |
| [kubernetes](#install-kubernetes) | Kubernetes / RKE2 | 2: cluster health and application resources | 21 |
| [traefik](#install-traefik) | Traefik with Prometheus metrics | 1: incoming traffic, errors and speed | 6 |
| [applications](#install-applications) | Applications already sending HTTP metrics | 1: application traffic, errors and speed | 2 |

**Only need SUSE Virtualization?** Complete steps 2–4, install option A, then check it in step 6. You can stop there. Imports is a separate, optional module. Coriolis is not included.

**Reading the dashboards:** VM Performance has separate Top 5 lists for CPU use, guest memory use and CPU waiting time. Resource lists show up to five entries (three in the compact storage health/old-backup cards); **Full names and values → Table view** shows the complete list and full identities. Each ranking uses the end of the selected period.

**Investigating a resource:** the Kubernetes resource guide includes **Investigate Pods**. Storage includes **Open PVCs** and **Open Pods**. Select the same cluster and namespace in that native list, then click the resource name to inspect it. These lists have their own filters. A panel can show several resources; its **Full names and values** link therefore keeps the complete metric table instead of guessing which Pod to open.

**Storage references:** `VM:` is a running VM matched through KubeVirt’s launcher-Pod mapping; `Pod:` is another measured consumer. `PVC:` means no active consumer was mapped, not proof that the volume is unused. The full table includes VM, Pod, PVC, volume, namespace and cluster when available.

In Kubernetes Cluster Health, **Unavailable application replicas** means configured application instances that are not available. For example, 3 configured and 2 available means 1 unavailable replica. The list below names the affected applications. A brief gap during an update can be normal; it does not mean data was lost. This panel belongs to the optional Kubernetes module.

**What “from zero” means here:** no dashboard components are installed yet. You still need an existing Harvester/Kubernetes cluster and a working SUSE Observability server. Server sizing, licensing, storage, DNS, certificates and application instrumentation are separate prerequisites. These charts do not create those platforms. For a new SUSE server, complete the [official server installation](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/kubernetes_install.html) first.

### Prepare only what your module needs

| Prerequisite | Needed for | How to configure it | Ready when |
|---|---|---|---|
| SUSE Observability server | Every module | Follow the server preparation below | You can log in through HTTPS |
| Kubernetes integration and official Agent | Virtualization, Imports, Kubernetes and Traefik; also recommended for application topology | Follow step 3 on each monitored cluster | Nodes and Pods appear in SUSE |
| Publishing Service Token | First installation of each module; not collector-only releases | Create the Secret in step 3 | The publisher has permission to manage dashboards and monitors |
| OTLP gRPC endpoint on the server | Virtualization; applications using a separate OTel collector | Follow [OTLP setup](docs/otlp.md) on the server cluster | DNS, TLS and the gRPC backend work; confirm ingestion after installation |
| Application Collection access | Virtualization collector image | Follow option A | The image pull Secret exists in the collector namespace |
| KubeVirt and Longhorn metrics | Virtualization | Follow option A | The collector discovers the targets and reports successful scrapes |
| VM Import Controller | Imports only | Follow option B | The import CRD exists and can be listed |
| Traefik Prometheus metrics | Traefik only | Follow option D | The metrics port and Service selector match your installation |
| Instrumented application and metric delivery | Applications only | Follow [application telemetry setup](docs/application-telemetry.md), then option E | The required HTTP metrics and labels exist in Metrics Explorer |

**OpenTelemetry is not a replacement for the Agent.** The Agent connects Kubernetes resources to SUSE. OpenTelemetry carries telemetry such as application metrics and traces. This project's Virtualization collector also uses OTLP. Kubernetes, Imports and Traefik use Prometheus remote write and do not require you to deploy another OTel collector. Installing an application dashboard does not instrument an application.

### If SUSE Observability is not installed yet

Do this on the **server cluster**, before installing anything from this repository:

1. Check the official [requirements and sizing](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/requirements.html) and [version compatibility](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/Compatibility%20Self%20Hosted.html). Obtain a license and the required registry access. Choose the storage class and enough free resources for the selected profile.
2. Follow the [official Helm installation](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/kubernetes_install.html). Keep its values and credentials in a private location. The server chart version is independent of this project's `1.8.0` charts.
3. Configure DNS, a valid certificate and [HTTPS ingress](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/ingress.html). For Virtualization or a separate application collector, also prepare the [OTLP endpoint](docs/otlp.md). The browser URL and OTLP gRPC address are different settings.
4. Open the SUSE URL, log in and confirm the server workloads are ready:

```sh
helm list --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability
kubectl get pods,pvc,ingress --kubeconfig /path/to/observability.yaml --context observability --namespace suse-observability
```

**Check:** the server release is deployed, its persistent storage is bound, workloads are ready and HTTPS works. Do not proceed while the server has unresolved storage, certificate or startup errors. An existing healthy server can be reused; do not reinstall it for these dashboards.

## 2. Write down your environment details

Replace these examples throughout the commands and YAML. Keep the files in a private folder outside Git.

| Fill in | Example | Where to find it |
|---|---|---|
| Kubeconfig file | `/path/to/cluster.yaml` | Download from Rancher or Harvester |
| Kubeconfig context | `my-cluster` | First command below |
| Agent namespace | `suse-observability` | Existing Agent release; use this for a new Agent in this guide |
| Integration name | `my-cluster` | Kubernetes StackPack in SUSE; may differ from the context |
| SUSE URL | `https://observability.example.com` | Address you use to open SUSE |
| OTLP endpoint, when required | `otlp-observability.example.com:443` | TLS gRPC endpoint on the server; used by Virtualization and separate application collectors |

Install [kubectl](https://kubernetes.io/docs/tasks/tools/) and [Helm 3 or 4](https://helm.sh/docs/intro/install/). Use a kubectl version compatible with your cluster. Check access and existing releases:

```sh
kubectl config get-contexts --kubeconfig /path/to/cluster.yaml
kubectl get nodes --kubeconfig /path/to/cluster.yaml --context my-cluster
helm list --all-namespaces --kubeconfig /path/to/cluster.yaml --kube-context my-cluster
```

**Check:** these are the intended nodes. If a module already exists, keep its release name, namespace, publishing identity and values file. The install command will update it. Do not install a second copy.

The examples use `suse-observability` to match the lab. Current Agent instructions may use `suse-observability-agent`. Follow your version's namespace and replace it consistently in the module commands. Secrets are local to a namespace. `my-cluster` is an example used for both context and integration name here; they can be different in your environment.

## 3. Prepare the Agent and credentials once

All modules in the same namespace reuse these prerequisites. Applications needs only the publishing credential and existing application metrics.

### Connect the cluster to SUSE

**Where:** run the following commands against the cluster you want to monitor: Harvester for VMs/imports, or your Kubernetes/RKE2 cluster for its workloads. Use the [official Kubernetes integration guide](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/k8s-quick-start-guide.html) and the commands generated by your own SUSE instance. Check the required cluster permissions and Pod security policy with the cluster administrator.

On Harvester, use one installation method: the Helm procedure below, or the [Harvester 1.8 Agent add-on](https://docs.harvesterhci.io/v1.8/advanced/addons/suse-observability-agent/). That add-on is experimental in the linked version. Keep an existing add-on under its current owner; do not install another Agent over it. Use documentation matching your Harvester version.

If the official Agent is already installed, keep it and use the checks below. Otherwise, open **SUSE Observability → StackPacks → Kubernetes → Add new instance**. Choose a unique integration name and obtain the ingestion Service Token. Save the token as `/private/ingestion-token.txt`, with no extra spaces or trailing newline.

Save `agent.yaml`, using the receiver URL from your instance:

```yaml
stackstate:
  cluster:
    name: my-cluster
  url: https://observability.example.com/receiver/stsAgent
```

Replace `AGENT_CHART_VERSION` with the version offered by your Kubernetes integration. Keep any additional values required by that integration/version.

If you need to inspect a version before using it, run `helm search repo suse-observability/suse-observability-agent --versions` after adding the repository below. Do not pick the newest version without checking server compatibility. `stackstate.cluster.name` identifies the cluster; `stackstate.url` is the Agent receiver, not the OTLP endpoint.

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

This is an administrator prerequisite: SUSE documents Service Token management through its CLI, while the Kubernetes/OpenTelemetry StackPacks issue ingestion credentials. A Kubernetes Secret only stores a token; it does not create SUSE permissions. To keep this installation Helm/kubectl-only, obtain the publishing token from the administrator before continuing. See the [credential explanation](docs/configuration-guide.md#3-understand-the-three-credentials).

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

**Where:** the Harvester cluster, in the same namespace as its Agent. **What you fill in:** integration name, SUSE URL and OTLP endpoint. The chart installs the collectors and publishes four dashboards and seven monitors.

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

For guest filesystem panels, the VM also needs a working QEMU guest agent. Follow the [Harvester guest-agent instructions](https://docs.harvesterhci.io/v1.8/vm/index/#installing-the-qemu-guest-agent) for your guest OS. This is separate from the SUSE Observability Agent installed on the cluster. The dashboard chart does not install software inside VMs; missing guest measurements remain empty.

Prepare registry access using [Application Collection authentication](https://docs.apps.rancher.io/get-started/authentication). In its web interface, create an access token or ask your organization administrator for a service account with access to the collector image. If you already have a working pull Secret in this namespace, reuse it.

Otherwise, save `/private/config.json` with your text editor, replacing the two placeholders with the registry username and access token/service-account secret:

```json
{"auths":{"dp.apps.rancher.io":{"username":"YOUR_REGISTRY_USERNAME","password":"YOUR_REGISTRY_TOKEN"}}}
```

This is a private credential file, not a chart values file. Keep it out of Git. An existing Docker configuration can also be used if it contains credentials for this registry, rather than only a local credential-helper reference. Create the Secret:

```sh
kubectl create secret generic application-collection \
  --type=kubernetes.io/dockerconfigjson --from-file=.dockerconfigjson=/private/config.json \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

**Check:** `application-collection` exists in the collector namespace. After installation, confirm the image actually pulls; a Secret alone does not prove access. Remove the temporary local credential file when done. The other dashboard modules do not require this Secret by default.

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

This rule allows TCP/9500 from this collector's namespace and Pod labels. Other policies can still grant additional access; the rule does not revoke it. The port also serves the Longhorn API. Do not add the first isolation policy blindly: it could block platform traffic. To skip storage collection, set `virtualization.longhorn.enabled: false`; storage panels will have no data.

Install:

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.8.0 --values virtualization.yaml \
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
  --version 1.8.0 --values imports.yaml \
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
  --version 1.8.0 --values kubernetes.yaml \
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
  --version 1.8.0 --values traefik.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability --wait --timeout 15m
```

**Check:** **Traefik · Incoming Traffic & Errors** appears and its collection panel is 1 for discovered targets.

<a id="install-applications"></a>

### E. Applications

The application must already send these metrics to SUSE. Traces alone are not enough. **Starting without application telemetry?** Follow [application telemetry setup](docs/application-telemetry.md) first: it covers instrumentation prerequisites, a separate collector installed with Helm, what to fill in, SDK configuration, checks and removal. It also explains when a newer Agent's built-in OTel gateway can be used. Neither path requires SUSE Virtualization. The new collector example has been rendered and checked, but was not deployed during the documentation update; verify fresh metrics before proceeding.

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
  --version 1.8.0 --values applications.yaml \
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
- Kubernetes: use the named Pod lists and **Full names and values → Table** to inspect every match, including entries outside the Top 5.
- Traefik/Applications: compare a known application's requests and errors. No traffic or missing data is not proof of availability.

**No data is not zero or healthy.** If Helm fails, inspect `kubectl get jobs` and `kubectl logs job/JOB_NAME` with the same kubeconfig, context and namespace. Check the publishing identity, DNS/TLS and ingestion credentials. Do not reinstall repeatedly to hide an error. See [validation and troubleshooting](docs/validation.md).

### Select a cluster, namespace and resource

1. Open **Cluster**. Keep **Include everything** enabled to see all measured clusters. To choose one, turn it off, click the input, then click the cluster name.
2. Open **Namespace**, turn off **Include everything** and select a namespace from that cluster. Repeat for VM, Application or Volume when that filter exists.
3. If the toolbar says **None**, nothing is selected. It does not mean "all". Select a value or enable **Include everything** again. A namespace list can be empty when Cluster is None.
4. When changing clusters, reset Namespace and the following filters to **Everything**, then select values from the new cluster. A selection from the previous cluster may not exist in the new one.
5. Read the names beside the values. Long names use an ellipsis in the middle, preserving the start and end. Click **Full names and values**, select **Table** and check the time range to read complete identities and every matching resource. Cards are a shortlist, not the complete incident list; abbreviated names are not unique identifiers.

**Why does Traefik show only one namespace?** Its Namespace filter lists namespaces with discovered Kubernetes Ingress backends in the selected cluster. It does not list every namespace that exists. Another namespace appears when its Ingress is discovered; useful request charts also need traffic through that Traefik instance, service metrics and successful collection. A Pod or ClusterIP Service alone does not create an Ingress. This chart's inventory covers standard Kubernetes Ingress, not every Traefik CRD/provider. Confirm the source with:

```sh
kubectl get ingress --all-namespaces --kubeconfig /path/to/cluster.yaml --context my-cluster
```

**Which Pod uses this volume?** Storage detail cards show a Running/Pending Pod association reported by the official Agent. For KubeVirt hotplug disks, it can identify the parent `virt-launcher` Pod; the direct mount belongs to its `hp-volume` child Pod. The full table includes `pod_name`, `pvc_namespace`, `pvc`, `volume` and `k8s_cluster_name`. A shared volume can have multiple consumer rows. A `PVC:` label means no unambiguous current Pod reference was matched; check whether the VM is stopped, the claim is unused or Pod telemetry is missing. It does not prove an orphaned volume. The overview still counts unique volumes. Never delete a volume based only on this list.

### Investigate the cause

Use the native resource page for Pod health, events, logs and related resources. These dashboards complement those screens. Application traces require instrumentation and OpenTelemetry delivery; installing a dashboard does not generate traces or execute repairs.

For a VM, distinguish virtualization errors (VM/VMI state, host, `virt-launcher`, PVC and Longhorn) from failures inside the guest OS. A Windows service error or an application exception needs guest/application telemetry. The current [SUSE Virtualization integration guide](https://documentation.suse.com/external-tree/en-us/cloudnative/suse-observability/latest/en/use/suse/suse-virtualization.html) describes a native Virtualization StackPack; availability depends on the server/Agent version. It was not listed in this lab's 2.10.2 catalog. Check compatibility before updating. For application tracing on Linux VMs, see the [official OpenTelemetry guide](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/otel/getting-started/getting-started-linux.html). No guest agent, new tracing pipeline or automatic remediation is installed by this project.

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
  --version 1.8.0 --values virtualization-second.yaml \
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

The publishing release owns the managed dashboards. From chart 1.7.0, updates patch existing dashboards and preserve their IDs by default. Definitions can still overwrite personal edits, so keep those in a separate copy. Explicit `replace` mode and uninstall/reinstall can change IDs. For chart versions older than 1.3.0, follow the [upgrade/removal notes](docs/lifecycle.md#moving-from-120-or-121).

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

The project does not remove Agent credentials, Traefik configuration, the import controller or the server's OTLP endpoint because other integrations may use them. If you installed the optional separate application collector only for this experiment, follow its [additional cleanup steps](docs/application-telemetry.md#7-remove-the-dashboard-and-optional-collector). To remove the **dedicated publishing Secret**, first confirm every release using it is gone, then run:

```sh
kubectl delete secret suse-observability-publisher-token \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

Skip that final command if the Secret is shared with anything else. Recreate it through step 3 when reinstalling.

## More details

The README covers the standard dashboard installation and removal. Environment-specific platform setup still belongs to its owner; linked guides cover those exceptions instead of assuming that every cluster uses the same DNS, CA, ingress or instrumentation.

- [Virtualization walkthrough](docs/virtualization.md) · [OTLP setup](docs/otlp.md) · [Common prerequisites](docs/prerequisites.md)
- [Configuration explained, step by step](docs/configuration-guide.md) · [Application telemetry setup](docs/application-telemetry.md)
- [Dashboard reading guide](docs/panel-guide.md) · [Metric definitions](docs/metric-contracts.md) · [Alerts](docs/alerts.md)
- [Validation](docs/validation.md) · [Lab results and limits](docs/lab-validation.md) · [Changelog](docs/changelog.md)

`examples/` contains small values files. `charts/` contains chart source; `helm/` contains the packages Helm downloads. `dev/` is only for maintainers. The Virtualization topics were inspired by [doccaz/harvester-extra-dashboards](https://github.com/doccaz/harvester-extra-dashboards).
