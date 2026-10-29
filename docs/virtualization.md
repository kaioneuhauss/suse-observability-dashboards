# Install only SUSE Virtualization dashboards

The result is **four dashboards**: VM & Host Overview, VM Performance, Capacity Planning, and Storage & Backups. The same chart installs their collectors and seven monitors. You do not need the Kubernetes, Traefik, Applications or Imports charts.

> [!WARNING]
> Community project for labs and learning. **Not recommended for production and not an officially supported SUSE integration.** Alert thresholds need review; notifications are not configured by this chart.

This walkthrough starts with no dashboard components on the Harvester cluster. It uses a working SUSE Observability server. A completely new SUSE server needs its own license, storage, sizing, DNS and TLS setup: complete the [official server installation](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/kubernetes_install.html) first. In the existing lab, keep the server and its data.

**The short version:** prepare access once → fill in three settings → run Helm → open the four dashboards. Save YAML files with your text editor. No repository clone, Bash script, Python installation or Grafana is needed.

## 1. Write down these settings

| Setting | Example | Where to get it |
|---|---|---|
| Harvester kubeconfig | `/path/to/harvester.yaml` | Harvester → Support → Download KubeConfig |
| Context | `harvester` | The first command below |
| Agent namespace | `suse-observability` | Existing Agent release; use this namespace for a new installation in this guide |
| Cluster name | `my-harvester` | Exact Kubernetes StackPack integration name, not necessarily the context |
| SUSE URL | `https://observability.example.com` | The address used to open SUSE Observability |
| OTLP endpoint | `otlp-observability.example.com:443` | TLS gRPC endpoint on the SUSE server, separate from the UI URL |
| Ingestion Service Token | Private file | Kubernetes StackPack setup; sends metrics |
| Publishing Service Token | Private file | SUSE administrator; manages dashboards and monitors |
| Registry credentials | Private Docker `config.json` | Application Collection account with access to `dp.apps.rancher.io` |

Replace the example paths, context and namespace in **every** command. Install [kubectl](https://kubernetes.io/docs/tasks/tools/) and [Helm 3 or 4](https://helm.sh/docs/intro/install/) on your computer.

```sh
kubectl config get-contexts --kubeconfig /path/to/harvester.yaml
kubectl get nodes --kubeconfig /path/to/harvester.yaml --context harvester
helm list --all-namespaces --kubeconfig /path/to/harvester.yaml --kube-context harvester
```

**Check:** these are the intended Harvester nodes. Note whether `suse-observability-agent` or `obs-virtualization` already exists. An existing release is updated, not a fresh installation. Keep the existing Agent; do not install another one.

If these four dashboards already exist in the same SUSE instance, use `mode: telemetry` for the new Harvester cluster. They already have a cluster selector. Publish them only once; see [multiple clusters](multiple-clusters.md).

## 2. Connect Harvester to SUSE Observability

**Already connected?** Check the Agent and cluster name below, then go to step 3.

For a new connection, open **SUSE Observability → StackPacks → Kubernetes → Add new instance**. Give the cluster a unique name. Create the ingestion Service Token and save it as `/private/ingestion-token.txt`, with no extra spaces or trailing newline. Keep private files outside Git.

Use the Agent chart version and receiver URL offered by your SUSE instance. The receiver usually ends with `/receiver/stsAgent`. Save `agent.yaml`:

```yaml
stackstate:
  cluster:
    name: my-harvester
  url: https://observability.example.com/receiver/stsAgent
```

Add the official repository and install the Agent. Replace `AGENT_CHART_VERSION` with the version from the integration instructions. If they include additional version-specific values, keep those too.

```sh
helm repo add suse-observability https://charts.rancher.com/server-charts/prime/suse-observability
helm repo update suse-observability
helm upgrade --install suse-observability-agent suse-observability/suse-observability-agent \
  --version AGENT_CHART_VERSION --values agent.yaml \
  --set-file stackstate.apiKey=/private/ingestion-token.txt \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --create-namespace --wait --timeout 15m
```

The legacy field is named `apiKey`, but accepts the ingestion **Service Token**. A publishing token is a separate credential. Helm stores Agent values in its release Secrets; restrict access to the namespace.

Check the Agent and the name used for telemetry:

```sh
kubectl get pods --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl get configmap suse-observability-agent-cluster-name \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability \
  -o jsonpath='{.data.STS_CLUSTER_NAME}{"\n"}'
kubectl get secret suse-observability-agent-secrets \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability \
  -o go-template='{{range $key, $value := .data}}{{$key}}{{"\n"}}{{end}}'
```

**Check:** Agent Pods are ready, the returned name is `my-harvester`, and the Secret has an `STS_API_KEY` key. The cluster's nodes and Pods must appear in SUSE before continuing. Custom release/Secret names may differ; [common setup](prerequisites.md) explains the overrides. This is a direct Helm installation; do not add a second Agent through the experimental Harvester add-on.

## 3. Prepare dashboard publishing, image access and OTLP

Ask the SUSE administrator for a Service Token that can **read, create, update and delete dashboards and monitors**. Keep using the same publishing identity on updates and removals. Creating a Kubernetes Secret does not grant those SUSE permissions. Token provisioning is an administrator prerequisite; see [Service Tokens](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/security/k8s-service-tokens.html).

Save it as `/private/publisher-token.txt` without a trailing newline. Save the Application Collection Docker authentication file as `/private/config.json`. Create the two Secrets in the Agent namespace:

```sh
kubectl create secret generic suse-observability-publisher-token \
  --from-file=serviceToken=/private/publisher-token.txt \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl create secret generic application-collection \
  --type=kubernetes.io/dockerconfigjson --from-file=.dockerconfigjson=/private/config.json \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

**Check:** kubectl confirms both Secrets were created. If they already exist, reuse them; do not replace another installation's credentials. These credentials stay outside the values file.

<a id="before-installing"></a>
The SUSE server must accept OTLP gRPC over TLS. If it does not have an endpoint, follow [Set up OTLP access](otlp.md) **on the SUSE server cluster**, then return here. DNS must resolve from Harvester and the TLS certificate must cover that hostname. Harvester needs outgoing HTTPS/443 to the SUSE UI/API, remote-write endpoint, OTLP endpoint and image registries.

Check the native services and public certificate used by this chart:

```sh
kubectl get service kubevirt-prometheus-metrics --namespace harvester-system \
  --kubeconfig /path/to/harvester.yaml --context harvester
kubectl get configmap kubevirt-ca --namespace harvester-system \
  --kubeconfig /path/to/harvester.yaml --context harvester
kubectl get service longhorn-backend --namespace longhorn-system \
  --kubeconfig /path/to/harvester.yaml --context harvester
kubectl get networkpolicy --namespace longhorn-system \
  --kubeconfig /path/to/harvester.yaml --context harvester
```

**Check:** the services and CA exist. The chart refreshes the public KubeVirt CA automatically. It does not read private keys.

If existing policies already isolate Longhorn managers and block this collector, add the optional values in step 4. The collector needs TCP/9500. Do not create the first isolation policy blindly: it can block existing platform traffic. The port also serves the Longhorn API; a NetworkPolicy restricts the port, not just `/metrics`.

## 4. Fill in three values

Save `virtualization.yaml`:

```yaml
clusterName: my-harvester
observability:
  url: https://observability.example.com
  otlpEndpoint: otlp-observability.example.com:443
```

Use the integration name from step 2. `otlpEndpoint` has **no** `https://` prefix. Default Secret names match step 3. Optional settings only when applicable:

```yaml
# Add only if Longhorn managers are already isolated by existing policies.
virtualization:
  longhorn:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

This grants access to the collector's namespace **and** Pod labels together. With this example, only the `obs-virtualization` collector in `suse-observability` matches. To omit Longhorn instead, use `virtualization.longhorn.enabled: false`; storage panels will have no data.

## 5. Install the chart

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.8.0 --values virtualization.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Check:** Helm reports `STATUS: deployed`. The chart creates the collectors and publishes four dashboards plus seven monitors. Successful publishing Jobs disappear automatically. Keep this values file and the same release name for future updates.

## 6. Confirm that the numbers make sense

```sh
kubectl get deployment/obs-virtualization deployment/obs-virtualization-pods daemonset/obs-virtualization-node \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl logs deployment/obs-virtualization --container collector --since=5m \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl get virtualmachineinstances --all-namespaces \
  --kubeconfig /path/to/harvester.yaml --context harvester
```

Open **Dashboards → Virtualization · VM & Host Overview**, select the cluster and click **Refresh**. Allow a few minutes for samples; CPU rates need more than one sample.

- **Running VMs:** compare with instances in the `Running` phase above, not all VM definitions.
- **Can we collect virtualization metrics?:** expected targets report `1`. A ready Pod does not prove the source is reachable.
- **Memory:** guest usage, assigned memory and VM process memory are different measurements. Balloon statistics must be available for guest memory.
- **Filesystems:** QEMU Guest Agent must be installed and running inside the guest. Missing measurements are not zero used space.
- **Capacity:** the 24-hour panels need real history. Selecting 24 hours does not create missing samples.
- **Storage:** compare volume names and health with Harvester/Longhorn. A backup record does not prove a successful restore.

For empty panels, failed jobs or certificate errors, use [Check the installation](validation.md). The [dashboard guide](virtualization-dashboards.md) explains each view. No import is needed to validate these four dashboards.

## 7. Remove only this module

Keep the publishing token until removal completes. Use the exact release, cluster and namespace from installation:

```sh
helm uninstall obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**What happens:** Helm first removes this release's managed SUSE dashboards and monitors, then its collectors, RBAC, ConfigMaps and optional Longhorn allow policy. A `mode: telemetry` release removes only collectors. The server, official Agent, applications, VMs, volumes, history and shared Secrets remain. **Do not delete the namespace.**

Check removal:

```sh
helm list --namespace suse-observability \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester
kubectl get deployment/obs-virtualization deployment/obs-virtualization-pods daemonset/obs-virtualization-node \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

**Check:** the release is absent; the three named workloads return `NotFound`. In the default installation, the four managed dashboards disappear. If cleanup fails, keep the Secret and follow [removal troubleshooting](lifecycle.md#3-if-removal-fails); do not bypass the cleanup hooks.

To repeat the test from zero, keep the prerequisites and run step 5 again. That is a clean dashboard installation; reinstalling Harvester, the Agent or the SUSE server is unnecessary and is outside this cleanup.

## Optional: VMware imports

Imports are separate. Add [the Imports chart](imports.md) only if you use VM Import Controller. Its optional performance collection shows CPU, memory and per-interface receive/transmit rates for the controller and shared image services. It does not report per-VM transferred bytes, ETA or Coriolis metrics.
