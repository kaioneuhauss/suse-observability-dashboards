# Prepare your environment

Complete these steps once, in order. If something already works, check it and reuse it. The dashboard installation then needs only a small values file and one Helm command per module. The example uses the current official Agent namespace, `suse-observability-agent`; the SUSE Observability server itself remains in `suse-observability`.

> [!WARNING]
> This is a community project, not an officially supported SUSE Observability integration. Use official, version-compatible instructions for the SUSE Observability server and Agent. Complete the [production acceptance checks](sre-review.md#production-acceptance) before operational use.

**Two places are involved:** the **server cluster** runs SUSE Observability; the **monitored cluster** runs SUSE Virtualization (Harvester) VMs or other Kubernetes workloads. They can be the same cluster. Commands explicitly name their target. Save YAML and private credentials with your text editor; no local scripts are required.

## 1. Check access to your clusters

Install [kubectl](https://kubernetes.io/docs/tasks/tools/) and [Helm 3 or 4](https://helm.sh/docs/intro/install/). Use a kubectl version compatible with the Kubernetes server. Download each kubeconfig from Rancher or Harvester and store it privately.

```sh
kubectl config get-contexts --kubeconfig /path/to/cluster.yaml
kubectl get nodes --kubeconfig /path/to/cluster.yaml --context my-cluster
helm list --all-namespaces --kubeconfig /path/to/cluster.yaml --kube-context my-cluster
```

**Expected:** the nodes belong to the intended cluster. Record its context, Agent namespace and existing release names. Your account must be allowed to install the selected module's workloads and RBAC resources. If Fleet or a Harvester add-on owns a prerequisite, change its owning configuration rather than installing a competing release.

## 2. Prepare the SUSE Observability server

Do this on the **server cluster**, before installing anything from this repository:

1. Check the official [requirements and sizing](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/requirements.html) and [version compatibility](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/Compatibility%20Self%20Hosted.html). Obtain a license and the required registry access. Choose the storage class and enough free resources for the selected profile.
2. Follow the [official Helm installation](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/kubernetes_install.html). Keep its values and credentials in a private location. The server chart version is independent of this project's `1.8.0` charts.
3. Configure DNS, a valid certificate and [HTTPS ingress](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/ingress.html). For Virtualization or a separate application collector, also prepare the [OTLP endpoint](otlp.md). The browser URL and OTLP gRPC address are different settings.
4. Open the SUSE Observability URL, log in and confirm the server workloads are ready:

```sh
helm list --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability
kubectl get pods,pvc,ingress --kubeconfig /path/to/observability.yaml --context observability --namespace suse-observability
```

**Check:** the server release is deployed, its persistent storage is bound, workloads are ready and HTTPS works. Do not proceed while the server has unresolved storage, certificate or startup errors. An existing healthy server can be reused; do not reinstall it for these dashboards.

The official installation page evolves. Follow the instructions for the **server chart version you selected**; current `suseObservability.*` settings are not a reason to replace a working older server's values. Keep the server and dashboard chart versions separate.

## 3. Prepare OpenTelemetry on the server

**Needed for:** Virtualization metrics and applications that send OTLP. Kubernetes, Imports and Traefik collectors use Prometheus remote write and can skip this step when no application collector uses OTLP.

1. Open **SUSE Observability → StackPacks → OpenTelemetry** and complete the integration instructions offered by your instance when setting up application telemetry. Keep its ingestion credential private. This is separate from the Kubernetes Agent integration and the publishing token.
2. On a self-hosted server, expose the existing collector through a valid TLS/gRPC ingress. Follow **[Set up OTLP access](otlp.md)**: check the server Service, prepare DNS/certificate, save the ingress values, apply them with Helm using the installed server version, and verify the route. Do not install another server collector just for these dashboards.
3. Record an endpoint such as `otlp-observability.example.com:443`. It is not automatically the same as the browser URL. Do not add `https://` to the Virtualization gRPC setting.

**Expected before installation:** the OTLP hostname resolves to the correct ingress, its certificate covers that hostname, and its backend is the server's gRPC Service. **Expected after installation:** fresh metrics arrive without TLS/authentication/export errors. An Ingress resource alone is not proof of ingestion.

The Virtualization chart reuses the official Kubernetes Agent's ingestion Secret. Application instrumentation has a separate [guided setup](application-telemetry.md). See SUSE Observability's [OTLP protocol and endpoint documentation](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/otel/otlp-apis.html). Keep certificate verification enabled.

## 4. Connect Harvester or Kubernetes to SUSE Observability

**Where:** run the following commands against the cluster you want to monitor: Harvester for VMs/imports, or your Kubernetes/RKE2 cluster for its workloads. Use the [official Kubernetes integration guide](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/k8s-quick-start-guide.html) and the commands generated by your own SUSE Observability instance. Check the required cluster permissions and Pod security policy with the cluster administrator.

On Harvester, first install the [SUSE Virtualization StackPack](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/suse/suse-virtualization.html) in your SUSE Observability instance if you want its native VM topology and navigation. Use one Agent installation method: the official Helm procedure, or the [Harvester 1.8 Agent add-on](https://docs.harvesterhci.io/v1.8/advanced/addons/suse-observability-agent/). That add-on is experimental in the linked version. Keep an existing add-on under its current owner; do not install another Agent over it. Use documentation matching your Harvester version.

If the official Agent is already installed, keep it and use the checks below. Otherwise, open **SUSE Observability → StackPacks → Kubernetes → Add new instance**. Choose a unique integration name and obtain the ingestion Service Token. **Use the Agent chart version and receiver URL shown by that instance**, since they vary with the server version. Save the token as `/private/ingestion-token.txt`, with no extra spaces or trailing newline.

Save `agent.yaml`, using the receiver URL from your instance:

```yaml
stackstate:
  cluster:
    name: my-cluster
  url: https://observability.example.com/receiver/stsAgent
```

For a **new Harvester integration**, the current [official SUSE Virtualization procedure](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/suse/suse-virtualization.html) also enables the Agent's OpenTelemetry resource integration. If the Agent chart version offered by your SUSE Observability instance supports these fields, merge them into the same `agent.yaml` (do not create a second file with another `otel:` block):

```yaml
otel:
  enabled: true
  k8sResourceCollector:
    integrations:
      suseVirtualization: true
      rancher: true
```

Use the version-specific values shown by SUSE Observability. This resource integration helps native VM topology; the project's Virtualization chart separately scrapes KubeVirt/Longhorn measurements. If you also add official KubeVirt ServiceMonitors, check that the same endpoints are not ingested twice under the same metric labels. Existing older Agents should be checked before changing their OTel settings.

Replace `AGENT_CHART_VERSION` with the version offered by your Kubernetes integration. Merge any additional values required by its generated command into `agent.yaml`. The current official default namespace is `suse-observability-agent`; this lab's older Harvester Agent uses `suse-observability`. Use **one namespace consistently** for that cluster's Agent, ingestion Secret and dashboard releases. The chart cannot read a Secret from another namespace.

If you need to inspect a version before using it, run `helm search repo suse-observability/suse-observability-agent --versions` after adding the repository below. Do not pick the newest version without checking server compatibility. `stackstate.cluster.name` identifies the cluster; `stackstate.url` is the Agent receiver, not the OTLP endpoint.

```sh
helm repo add suse-observability https://charts.rancher.com/server-charts/prime/suse-observability
helm repo update suse-observability
helm upgrade --install suse-observability-agent suse-observability/suse-observability-agent \
  --version AGENT_CHART_VERSION --values agent.yaml \
  --set-file stackstate.apiKey=/private/ingestion-token.txt \
  --kubeconfig /path/to/cluster.yaml --kube-context my-cluster \
  --namespace suse-observability-agent --create-namespace --wait --timeout 15m
```

The field is called `apiKey` but accepts the ingestion Service Token. Helm stores these values in release Secrets; restrict access to the namespace. Do not enable another Agent through a Harvester add-on as well.

Check the Agent, integration name and ingestion Secret **without printing its credential**:

```sh
kubectl get pods --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent
kubectl get configmap suse-observability-agent-cluster-name \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent \
  -o jsonpath='{.data.STS_CLUSTER_NAME}{"\n"}'
kubectl get secret suse-observability-agent-secrets \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent \
  -o go-template='{{range $key, $value := .data}}{{$key}}{{"\n"}}{{end}}'
```

**Check:** Agent Pods are ready, you know the integration name, and the Secret contains `STS_API_KEY`. Nodes and Pods must appear in SUSE Observability. Use that integration name as `clusterName` below. With a custom Agent release, find the equivalent ConfigMap/Secret in its configuration.

**Applications only:** this Agent is recommended for Kubernetes topology, but the content chart itself only needs a publisher and compatible application metrics. It does not create those metrics.

## 5. Prepare the publishing credential

**Where:** the namespace of the release that publishes content. For the simplest installation this is the monitored cluster's Agent namespace. With [central publication](multiple-clusters.md#2-keep-publishers-on-the-observability-cluster), create it only on the server cluster; source collectors do not need publishing access.

Check the namespace with `kubectl get namespace suse-observability-agent --kubeconfig /path/to/cluster.yaml --context my-cluster`. The Agent command above creates it. If you are installing only the Applications content module and have no Agent, create it before creating Secrets:

```sh
kubectl create namespace suse-observability-agent \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

The publisher needs a **different Service Token** with `get/create/update/delete` on dashboards and monitors. The Agent's ingestion token cannot do this. Token issuance and permissions belong to SUSE Observability, not Kubernetes; `kubectl create secret` cannot create SUSE Observability permissions. An SUSE Observability administrator can create a dedicated role and token with the [official `sts` CLI](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/cli/cli-sts.html). This is a **one-time server administration prerequisite**, not a local installer script. With an admin `sts` session connected to your SUSE Observability URL, run:

```sh
sts rbac create-subject --subject sre-dashboard-publisher
sts rbac grant --subject sre-dashboard-publisher --permission get-dashboards
sts rbac grant --subject sre-dashboard-publisher --permission create-dashboards
sts rbac grant --subject sre-dashboard-publisher --permission update-dashboards
sts rbac grant --subject sre-dashboard-publisher --permission delete-dashboards
sts rbac grant --subject sre-dashboard-publisher --permission get-monitors
sts rbac grant --subject sre-dashboard-publisher --permission create-monitors
sts rbac grant --subject sre-dashboard-publisher --permission update-monitors
sts rbac grant --subject sre-dashboard-publisher --permission delete-monitors
sts rbac describe-permissions --subject sre-dashboard-publisher
sts service-token create --name sre-dashboard-publisher --roles sre-dashboard-publisher
```

**Check:** the role has exactly those eight permissions. The last command prints the token **once**; copy it directly into your approved secret store and the private file below. Do not put it in Git, screenshots or chat. If your SUSE Observability version requires an additional permission, confirm it from the Job's 403 response and the [official permission list](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/security/rbac/rbac_permissions.html); do not grant `stackstate-admin` to the publisher. If you already have managed dashboards, reuse their existing publishing identity rather than creating a new one.

Save the token in a private file, for example `/private/publisher-token.txt`. The file must contain only the token, without a trailing newline. Keep it out of Git and restrict who can read it. Then create the Secret:

```sh
kubectl create secret generic suse-observability-publisher-token \
  --from-file=serviceToken=/private/publisher-token.txt \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent
```

This avoids putting the token in the command line or your values file. One Secret can serve all modules in this namespace. If it already exists, reuse it after checking its purpose. Keep the token in your approved secret store and remove the temporary file when done.

**Already have managed dashboards?** Keep the existing publisher identity. For installations with separate dashboard and monitor Secrets, add:

```yaml
auth:
  dashboards:
    existingSecret: suse-observability-dashboard-token
  monitors:
    existingSecret: suse-observability-monitor-token
```

Both use key `serviceToken` by default. A different identity can receive 403 even with similar permissions because it does not own the existing dashboard.

**Expected result:** the publishing Secret exists in the namespace where Helm will publish the dashboards. Skip this step for collector-only (`telemetry`) releases.

**Why is an administrator involved?** Kubernetes Secrets store credentials; they do not create SUSE Observability roles. Once this one-time credential exists, installing and removing this project's modules uses Helm and kubectl only. The chart runs its pinned CLI inside the publishing Job. See [credential roles and ownership](configuration-guide.md#3-understand-the-three-credentials).

## 6. Check the module-specific prerequisites

### Virtualization: services, registry and network access

Run on **Harvester**:

```sh
kubectl get service kubevirt-prometheus-metrics --namespace harvester-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get configmap kubevirt-ca --namespace harvester-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
kubectl get service longhorn-backend --namespace longhorn-system \
  --kubeconfig /path/to/cluster.yaml --context my-cluster
```

**Expected:** all three resources exist. The chart discovers KubeVirt targets and refreshes the public CA automatically. You do not export certificates by hand. Linux host collection uses host networking and read-only host mounts; cluster admission must permit it.

Prepare registry access using [Application Collection authentication](https://docs.apps.rancher.io/get-started/authentication). In its web interface, create an access token or ask your organization administrator for a service account with access to the collector image. If you already have a working pull Secret in this namespace, reuse it.

Otherwise, save `/private/config.json` with your text editor, replacing the two placeholders with the registry username and access token/service-account secret:

```json
{"auths":{"dp.apps.rancher.io":{"username":"YOUR_REGISTRY_USERNAME","password":"YOUR_REGISTRY_TOKEN"}}}
```

This is a private credential file, not a chart values file. Keep it out of Git. An existing Docker configuration can also be used if it contains credentials for this registry, rather than only a local credential-helper reference. Create the Secret:

```sh
kubectl create secret generic application-collection \
  --type=kubernetes.io/dockerconfigjson --from-file=.dockerconfigjson=/private/config.json \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent
```

**Check:** `application-collection` exists in the collector namespace. After installation, confirm the image actually pulls; a Secret alone does not prove access. Remove the temporary local credential file when done. The other dashboard modules do not require this Secret by default.

Then follow **[Network access and Longhorn policies](network-access.md)**. If Longhorn is already isolated, enable its scoped policy in your values file; the chart creates it during installation and removes it during uninstall. No standalone policy file is needed. Existing platform policies must remain in place.

Guest filesystem panels additionally need [QEMU Guest Agent inside the VM](https://docs.harvesterhci.io/v1.8/vm/index/#installing-the-qemu-guest-agent). This is different from the SUSE Observability cluster Agent. Powered-off VMs have no current usage. Do not interpret absent guest metrics as zero.

### Other modules

| Module | Configure before installation | Ready when |
|---|---|---|
| Imports | [VM Import Controller and optional performance access](imports.md) | Import CRD exists; TLS/10250 is reachable if performance is enabled |
| Kubernetes | [Host metrics and optional etcd](kubernetes.md) | Linux host collectors are permitted; etcd endpoint exists if enabled |
| Traefik | [Enable internal Prometheus metrics](traefik.md) and [check policies](network-access.md#4-traefik-and-other-restrictions) | Correct namespace, selector and metrics port are known |
| Applications | [Instrument and send application telemetry](application-telemetry.md) | Required HTTP metrics and labels are present in SUSE Observability |

Do not enable etcd collection just to fill an empty panel. Confirm the existing endpoint first; the chart does not expose or reconfigure etcd. Imports performance measures shared infrastructure, not per-VM transfer speed.

## 7. Custom Secret names or private certificates

Skip this section when the default names and public certificates work.

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
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability-agent
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

## 8. Ready to install

You should now know your context, namespace, integration name, SUSE Observability URL and (when needed) OTLP endpoint. The required Secrets are in the release's namespace. No plaintext credential belongs in a chart values file or Git.

Return to **[install your first module](../README.md#3-install-your-first-module)**, or follow **[central publication](multiple-clusters.md#2-keep-publishers-on-the-observability-cluster)** for the three-cluster layout. After installation, check actual collection and fresh data; successful prerequisite commands alone do not validate the complete path.
