# Prepare your environment

Do this once before installing your first module. If an item is already set up, check it and move on. You only need kubectl and Helm on your computer. Save the YAML examples with your usual text editor.

For the complete guided installation, start with the [README prerequisite map](../README.md#prepare-only-what-your-module-needs). For the reason behind every setting, use the [configuration walkthrough](configuration-guide.md). This page is the common preparation checklist.

> [!WARNING]
> These charts are for labs and learning. They are not recommended for production or covered by official SUSE support.

## 1. Check access to your cluster

Install [kubectl](https://kubernetes.io/docs/tasks/tools/) and [Helm](https://helm.sh/docs/intro/install/) for your operating system. Use a kubectl version compatible with your cluster. The charts are checked with Helm 3 and 4.

Download the cluster's kubeconfig from Rancher or Harvester. Keep it in a private location outside this repository. Find the context name:

```sh
kubectl config get-contexts --kubeconfig /path/to/cluster.yaml
kubectl get nodes --kubeconfig /path/to/cluster.yaml --context my-cluster
```

In all examples, replace `/path/to/cluster.yaml` and `my-cluster` with those details. `--context` is for kubectl; `--kube-context` is the equivalent Helm option. Your account needs permission to install the chart's workloads and RBAC resources.

**Expected result:** you can list the nodes in the intended cluster.

## 2. Check SUSE Observability and the Agent

Open your SUSE Observability URL and confirm you can log in. If the server is not installed, follow the [README server preparation](../README.md#if-suse-observability-is-not-installed-yet), including sizing, licensing, persistent storage, the official Helm installation, DNS and TLS checks. These dashboard charts do not size or install the server.

Virtualization, Imports, Kubernetes and Traefik use the official Agent integration. Follow the [README Agent installation](../README.md#connect-the-cluster-to-suse) and your instance's Kubernetes StackPack instructions. They contain the settings for your version. Do not install a second Agent if one already exists. The [Harvester 1.8 Agent add-on](https://docs.harvesterhci.io/v1.8/advanced/addons/suse-observability-agent/) is documented as experimental. Applications content only needs existing compatible HTTP metrics and publisher access; its telemetry setup is described [separately](application-telemetry.md).

Find the Agent's namespace, then check its Pods and integration name:

```sh
helm list --all-namespaces --kubeconfig /path/to/cluster.yaml --kube-context my-cluster
kubectl get pods --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
kubectl get configmap suse-observability-agent-cluster-name \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability \
  -o jsonpath='{.data.STS_CLUSTER_NAME}{"\n"}'
```

Use the returned name as `clusterName`. If the ConfigMap has a custom name, get the integration name from the Agent's configuration or the Kubernetes integration in SUSE. Do not substitute the kubeconfig context unless both names actually match.

Use the Agent's existing namespace for the collectors. It may be `suse-observability-agent` instead of `suse-observability`. Replace the namespace in every command if needed. Wait until the cluster's nodes and Pods appear in SUSE before continuing.

**Expected result:** the Agent is running, its cluster name is known and the cluster appears in SUSE.

## 3. Check the ingestion Secret

The charts reuse the Agent's ingestion credential. The default is Secret `suse-observability-agent-secrets`, key `STS_API_KEY`. Check the key names without printing the credential:

```sh
kubectl get secret suse-observability-agent-secrets \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability \
  -o go-template='{{range $key, $value := .data}}{{$key}}{{"\n"}}{{end}}'
```

If your names differ, add this to your module's values file:

```yaml
ingestion:
  existingSecret: your-agent-secret
  secretKey: your-ingestion-key
```

The applications module and `mode: content` do not need this Secret. Do not replace the Agent's credential just to install a dashboard.

**Expected result:** the Secret contains `STS_API_KEY`, or you recorded its custom name and key.

## 4. Create the publishing Secret

Ask your SUSE administrator for a **Service Token allowed to read, create, update and delete dashboards and monitors**. The Agent's ingestion token cannot do this. Token issuance and permissions belong to SUSE Observability, not Kubernetes; these charts cannot create that access for you. See [SUSE Service Tokens](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/security/k8s-service-tokens.html).

Save the token in a private file, for example `/private/publisher-token.txt`. The file must contain only the token, without a trailing newline. Keep it out of Git and restrict who can read it. Then create the Secret:

```sh
kubectl create secret generic suse-observability-publisher-token \
  --from-file=serviceToken=/private/publisher-token.txt \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
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

## 5. Check the requirements for your module

| Module | What else is needed |
|---|---|
| [Virtualization](virtualization.md) | OTLP gRPC endpoint, collector image access, KubeVirt and Longhorn metrics |
| [Imports](imports.md) | VM Import Controller and its CRD on Harvester |
| [Traefik](traefik.md) | Prometheus metrics enabled on your existing Traefik |
| [Applications](applications.md) | HTTP metrics already arriving in SUSE with the expected names and labels |
| [Kubernetes](kubernetes.md) | Linux nodes; permission to run host collectors; etcd metrics only if you enable them |

Pods need DNS and HTTPS access to SUSE and the configured image registries. Publishing Jobs also download the pinned SUSE CLI and verify its SHA-256. Their default image runs on Linux amd64. The CLI runs inside the Job; you do not install it locally.

No application metrics yet? Use [application telemetry setup](application-telemetry.md). It distinguishes SDK push, Prometheus scraping and existing telemetry. The current Agent gateway documentation does not apply automatically to older Agent charts such as the lab's `1.2.14`.

For a private CA, create a Secret from your CA certificate:

```sh
kubectl create secret generic observability-ca --from-file=ca.crt=/private/ca.crt \
  --kubeconfig /path/to/cluster.yaml --context my-cluster --namespace suse-observability
```

Then add the relevant settings to your values file. This example is for Virtualization:

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

Applications only uses `content.publisher`; Traefik and Kubernetes use `content.publisher` and `telemetry.remoteWrite`. Imports uses `content.publisher` and `imports.remoteWrite`. Keep certificate verification enabled.

You are ready to follow the [installation example](../README.md#2-fill-in-your-settings--harvester-example) or the guide for your chosen module.
