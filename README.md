# SUSE Observability dashboards

Choose a module, fill in a small YAML file and install it with Helm. Each module includes its own dashboards and monitors. Collectors are included where extra metrics are needed.

These charts publish dashboards **to SUSE Observability**. They collect data **from** the cluster you choose to monitor; the Virtualization module reads SUSE Virtualization (Harvester). The charts do not install either platform.

> [!WARNING]
> Community project, **not an officially supported SUSE Observability integration** and **not recommended for production without target-environment acceptance**. A successful installation in this lab does not certify another environment. Complete the [production acceptance checks](docs/sre-review.md#production-acceptance) before operational use, including backup restore and notification delivery.

You need **Helm, kubectl and a text editor** for these module installations. You do not need local scripts, Python, Grafana or a repository clone. For a new SUSE Observability instance, an administrator uses the SUSE Observability `sts` CLI once to create the dedicated publishing role/token; browser steps create the official integrations and obtain ingestion credentials.

| Name used here | What it means |
|---|---|
| **SUSE Observability** | The server, browser interface, metrics API and destination for dashboards and monitors. |
| **SUSE Virtualization (Harvester)** | The virtualization cluster whose VMs, hosts and Longhorn storage you want to observe. |
| **SUSE Observability Agent** | The official Agent installed in a monitored Kubernetes or Harvester cluster. It is separate from this project's optional collectors. |
| **Project Helm chart** | One of the optional dashboard modules listed below; it can install a collector and publish content to SUSE Observability. |

## 1. Choose your modules

| Module | What it shows | Dashboards / monitors |
|---|---|---|
| **virtualization** | SUSE Virtualization (Harvester) VMs, hosts, performance, capacity, storage and backups | 4 / 7 |
| **imports** | VMware imports into SUSE Virtualization via VM Import Controller, plus optional importer CPU, memory and network use | 1 / 3 |
| **kubernetes** | Cluster health and application resource use | 2 / 21 |
| **traefik** | Incoming traffic, HTTP errors and response times | 1 / 6 |
| **applications** | HTTP traffic, errors and response times from instrumented applications | 1 / 2 |

Only want dashboards for SUSE Virtualization? Install **virtualization**. Imports is optional and independent. Coriolis is not included.

## 2. Prepare the prerequisites once

<a id="prepare-only-what-your-module-needs"></a>
<a id="if-suse-observability-is-not-installed-yet"></a>
<a id="connect-the-cluster-to-suse"></a>

**Starting from zero? Follow [Prepare your environment](docs/prerequisites.md) in order.** It explains what to configure, where to run each command and how to check the result:

| Order | What to prepare | Needed for | Instructions |
|---|---|---|---|
| 1 | Cluster access, Helm and kubectl | All modules | [Access checks](docs/prerequisites.md#1-check-access-to-your-clusters) |
| 2 | SUSE Observability server, storage, license, DNS and HTTPS | All modules | [Server setup and official installation](docs/prerequisites.md#2-prepare-the-suse-observability-server) |
| 3 | SUSE Observability OTLP endpoint | Virtualization and applications using OTLP | [OpenTelemetry setup](docs/prerequisites.md#3-prepare-opentelemetry-on-the-server) |
| 4 | SUSE Observability Kubernetes integration and Agent on the monitored cluster | Virtualization, Imports, Kubernetes and Traefik | [Agent on Harvester or Kubernetes](docs/prerequisites.md#4-connect-harvester-or-kubernetes-to-suse-observability) |
| 5 | Publishing credential stored in a Kubernetes Secret | Releases that publish dashboards | [Create the Secret](docs/prerequisites.md#5-prepare-the-publishing-credential) |
| 6 | Registry access, metrics endpoints and required network access | Depends on the module | [Module checks](docs/prerequisites.md#6-check-the-module-specific-prerequisites) |

**Keep working prerequisites.** Reinstalling dashboards does not require reinstalling the SUSE Observability server, its official Agent, SUSE Virtualization (Harvester) or your applications. These charts do not create those platforms or instrument an application.

Fill in these details before continuing. Keep values and credential files in a private folder outside Git:

| Replace in this guide | Your value |
|---|---|
| `/path/to/cluster.yaml` | Kubeconfig of the cluster where this release will run |
| `my-cluster` in commands | Context listed by `kubectl config get-contexts --kubeconfig /path/to/cluster.yaml` |
| `clusterName: my-cluster` in YAML | Exact name of the cluster's Kubernetes integration in SUSE Observability; it can differ from the context |
| `suse-observability-agent` | Current default namespace of the official SUSE Observability Agent and the namespace used by the commands below. If your Agent already uses `suse-observability`, replace the namespace in **every** command and Secret check. Do not install a second Agent. |
| `https://observability.example.com` | SUSE Observability browser/API URL |
| `otlp-observability.example.com:443` | SUSE Observability TLS/gRPC endpoint, without `https://`; Virtualization only |

The short examples below use the default Secret names: `suse-observability-agent-secrets` for ingestion, `suse-observability-publisher-token` for publication, and `application-collection` for the Virtualization image. [Custom names and private CAs](docs/prerequisites.md#7-custom-secret-names-or-private-certificates) are optional overrides.

## 3. Install your first module

**Already installed?** Keep the existing release placement, `mode` and complete saved values. Use [update/removal](#7-update-remove-or-reinstall) instead of replacing an existing configuration with a minimal first-install example.

**Where:** the cluster you want to monitor, in the Agent's namespace (`suse-observability-agent` in this new-install example). The default installs collectors and publishes content together. For an environment with several clusters and publishers kept on the Observability cluster, use the complete [central publication procedure](docs/multiple-clusters.md#2-keep-publishers-on-the-observability-cluster) instead; do not run both approaches for the same module.

Add the repository once:

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

**Expected:** Helm updates the repository successfully. Save only the YAML files for the modules you want.

<a id="2-fill-in-your-settings--harvester-example"></a>
<a id="install-virtualization"></a>

### SUSE Virtualization

Save **`virtualization.yaml`**:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
  otlpEndpoint: otlp-observability.example.com:443
```

If the prerequisite check confirmed that existing policies isolate Longhorn managers, add this to the same file. Helm will create and later remove the collector's policy for you:

```yaml
virtualization:
  longhorn:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

Do not enable it on an unisolated Longhorn installation: its first ingress policy could block platform traffic. See the [network checks](docs/network-access.md).

Install:

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.8.0 --values virtualization.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability-agent --wait --timeout 15m
```

**Expected:** `STATUS: deployed`, ready collectors and four **Virtualization** dashboards. Continue with [step 5](#5-check-that-it-works). If these are the only dashboards you need, you are done after those checks.

<a id="install-kubernetes"></a>

### Kubernetes / RKE2

Save **`kubernetes.yaml`**:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
```

```sh
helm upgrade --install obs-kubernetes obs-dashboards/suse-observability-kubernetes \
  --version 1.8.0 --values kubernetes.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability-agent --wait --timeout 15m
```

**Expected:** two Kubernetes dashboards. If Virtualization already collects host/Pod metrics on this cluster, add **`mode: content`** to this file first to avoid duplicate host collectors. If installing Virtualization after Kubernetes, change Kubernetes to `mode: content` and rerun its command before installing Virtualization. [Optional etcd collection](docs/kubernetes.md) requires an existing local metrics endpoint; it is off by default.

<a id="install-traefik"></a>

### Traefik

Complete [Traefik metrics preparation](docs/traefik.md) first. Save **`traefik.yaml`**:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
```

```sh
helm upgrade --install obs-traefik obs-dashboards/suse-observability-traefik \
  --version 1.8.0 --values traefik.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability-agent --wait --timeout 15m
```

**Expected:** **Traefik · Incoming Traffic & Errors**. Defaults discover RKE2 Traefik in `kube-system`, port 9100. A different namespace, selector or port needs the overrides in the linked guide.

<a id="install-applications"></a>

### Instrumented applications

Complete [application telemetry setup](docs/application-telemetry.md) first. Traces alone do not provide the HTTP metrics this dashboard requires. Save **`applications.yaml`**:

```yaml
observability:
  url: https://observability.example.com
```

```sh
helm upgrade --install obs-applications obs-dashboards/suse-observability-applications \
  --version 1.8.0 --values applications.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability-agent --wait --timeout 15m
```

**Expected:** **Applications · Traffic, Errors & Speed**. This module publishes content only. It does not create collectors, instrument applications or generate traffic. See the [required HTTP metrics and labels](docs/applications.md).

## 4. Add a second module

<a id="install-imports"></a>

Example: you installed Virtualization and now want **Imports**. Keep the first release installed. Reuse the Agent, Secrets and Helm repository. Each module has its own values file and release name.

Check that VM Import Controller is enabled using the [Imports prerequisites](docs/imports.md). Save **`imports.yaml`**:

```yaml
clusterName: my-cluster
observability:
  url: https://observability.example.com
imports:
  performance:
    enabled: false
```

```sh
helm upgrade --install obs-imports obs-dashboards/suse-observability-imports \
  --version 1.8.0 --values imports.yaml \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability-agent --wait --timeout 15m
```

**Expected:** **Virtualization · VMware Import Progress** appears alongside the four existing dashboards. Imports also works as the first module. The same approach adds any other module: save its own file and run its own command.

The example starts with inventory only, which does not need kubelet access. To add importer and shared image-service CPU, memory and network activity, first complete the [optional performance prerequisites](docs/imports.md#optional-cpu-memory-and-network-during-imports), then set `performance.enabled: true` and rerun the same Helm command. This is **not per-VM transfer speed, percentage or ETA**.

## 5. Check that it works

Use the same kubeconfig, context and namespace as the installation:

```sh
helm list --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability-agent
kubectl get deployment,daemonset,pods \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent
```

| Installed module, with collectors | Expected workloads |
|---|---|
| Virtualization | Deployments `obs-virtualization`, `obs-virtualization-pods`; DaemonSet `obs-virtualization-node` |
| Imports | Deployment `obs-imports-imports` |
| Kubernetes | Deployment `obs-kubernetes-pods`; DaemonSet `obs-kubernetes-node` |
| Traefik | Deployment `obs-traefik-traefik` |
| Applications or any `mode: content` release | No collector workloads |

With optional etcd collection enabled, also expect `obs-virtualization-etcd` or `obs-kubernetes-etcd` on the eligible etcd nodes.

1. Confirm every installed release is **deployed** and its expected collectors are ready. Successful publishing Jobs disappear automatically.
2. Open **SUSE Observability → Dashboards → All**. Confirm the dashboards from your selected modules exist.
3. Select your **Cluster**, then **Namespace** and resource. **Everything** selects all values; **None** selects nothing. Reset dependent filters when switching clusters.
4. Allow a few minutes for fresh samples and rate calculations. A newly started collector can briefly have empty rankings before enough samples arrive. Check collection indicators, then compare a known VM, Pod, volume, import record or application against its source. Data older than the installation does not prove the new collector works.
5. Open **Monitors** and inspect the module's `SRE ·` rules. Review thresholds and configure [notification channels](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/alerting/notifications/configure.html) if you want notifications.

**No data is not zero or healthy.** A stopped VM has no current resource usage; a guest filesystem needs QEMU Guest Agent; an idle import is not a transfer test. Not every panel has an alert. See [alert coverage](docs/alerts.md) and [using filters, resource lists and native investigation](docs/dashboard-use.md).

If installation fails:

```sh
kubectl get jobs --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent
kubectl logs job/JOB_NAME --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent
```

Replace `JOB_NAME` with the failed Job. Check credentials, DNS, TLS and permissions before retrying the same Helm command. [More checks and troubleshooting](docs/validation.md).

## 6. Add another cluster or keep publication central

You need **one publication per module per SUSE Observability instance**, not a dashboard copy for every cluster.

- **Another source cluster:** prepare its Agent and ingestion Secret, save new module values with `mode: telemetry`, and run the module command with that cluster's context. No publisher token is needed there.
- **Publish from the cluster hosting SUSE Observability:** install each source with `mode: telemetry`, then publish each module once with `mode: content` on the server cluster. One shared `content.yaml` can serve all five publishers when their common settings are identical.

Follow [the complete commands, placement table and removal procedure](docs/multiple-clusters.md). This is the arrangement used in the three-cluster validation. Record which release owns publication: uninstalling it removes that module's shared dashboards for every source cluster.

## 7. Update, remove or reinstall

### Update a module

Edit its saved YAML and rerun its **same install command**. Keep the release name, namespace and publishing identity. To change versions, update the repository, review the [changelog](docs/changelog.md) and change `--version` explicitly. Normal updates preserve dashboard IDs; an uninstall/reinstall creates new IDs and can invalidate bookmarks. Managed dashboards can overwrite manual edits; keep personal copies separately.

### Remove only an additional module

To remove Imports and keep Virtualization:

```sh
helm uninstall obs-imports \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability-agent --wait --timeout 15m
```

**Expected:** its collectors, dashboard and three monitors are gone. Virtualization, VM Import Controller and import records remain. A `telemetry` release removes only collectors; shared content remains until its publishing release is removed.

### Remove every installed module

First list releases using step 5. Run **only the lines for modules installed in that cluster and namespace**. Keep SUSE Observability and the publishing Secret available until cleanup finishes:

```sh
helm uninstall obs-imports --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability-agent --wait --timeout 15m
helm uninstall obs-applications --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability-agent --wait --timeout 15m
helm uninstall obs-traefik --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability-agent --wait --timeout 15m
helm uninstall obs-kubernetes --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability-agent --wait --timeout 15m
helm uninstall obs-virtualization --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability-agent --wait --timeout 15m
```

For several clusters, remove source releases in each source namespace, then the central publishers as shown in [multi-cluster removal](docs/multiple-clusters.md#3-remove-a-module-or-start-again). **Do not delete the namespace, PVCs or platform releases.** Helm removes the project's owned resources and managed content; existing applications, VMs, volumes, Agents, server and metric history stay in place.

### Check removal and reinstall

```sh
helm list --kubeconfig /path/to/cluster.yaml --kube-context my-cluster --namespace suse-observability-agent
kubectl get deployment,daemonset,pods --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent
```

**Expected:** the removed releases and their collectors are absent. Refresh **Dashboards → All** and **Monitors**; their managed content should also be gone. The native Kubernetes dashboard and unrelated content remain. If a cleanup hook fails, keep the credentials and follow [cleanup troubleshooting](docs/lifecycle.md); do not bypass it with `--no-hooks`.

To start again, keep the working prerequisites and saved files, run the same install commands, then repeat step 5. [Optional cleanup of dedicated Secrets and prerequisites](docs/lifecycle.md) is separate; never remove a Secret still used by the Agent or another module.

## More detail

- [Configuration walkthrough: what each setting does](docs/configuration-guide.md)
- [Dashboard measurements and limitations](docs/metric-contracts.md)
- [Every panel explained](docs/panel-guide.md)
- [SRE review of all nine dashboards and production acceptance](docs/sre-review.md)
- [What was actually tested in the lab](docs/lab-validation.md)

The installation uses the published charts. `charts/` contains their sources, `helm/` their packages, `examples/` small values files, `docs/` the guides and `dev/` maintainer tools. You do not need the maintainer tools to install or remove a module.
