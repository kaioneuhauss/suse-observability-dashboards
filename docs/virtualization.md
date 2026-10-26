# SUSE Virtualization / Harvester

Use this module for VM performance, host capacity, Longhorn storage and backup records. It installs four dashboards, five monitors and the collectors they need. It does not require any other module.

This is a community lab integration, **not recommended for production**.

<a id="before-installing"></a>

## 1. Check the requirements

Complete the [common setup](prerequisites.md). Install this module on **Harvester, in the Agent's namespace**. Three extra items are needed:

### OTLP endpoint

Your SUSE server needs an OTLP gRPC endpoint with TLS, such as `otlp-observability.example.com:443`. This is separate from the web UI address. If it is missing, follow [Set up OTLP access](otlp.md) with the administrator of the SUSE server.

### Collector image access

The default collector image comes from `dp.apps.rancher.io`. It needs an Application Collection account and a registry Secret named `application-collection` in the release namespace.

If your administrator provides a Docker authentication file for that registry, create the Secret with:

```sh
kubectl create secret generic application-collection \
  --type=kubernetes.io/dockerconfigjson --from-file=.dockerconfigjson=/private/config.json \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
```

The file must be a valid Docker config containing credentials for `dp.apps.rancher.io`. A Secret in another namespace is not accessible here. If the Secret already exists, reuse it. For an approved registry mirror, set `virtualization.image.repository`, `tag` and `imagePullSecrets` in your values file.

### KubeVirt and Longhorn access

Check the existing endpoints:

```sh
kubectl get service kubevirt-prometheus-metrics --kubeconfig /path/to/harvester.yaml --context harvester --namespace harvester-system
kubectl get configmap kubevirt-ca --kubeconfig /path/to/harvester.yaml --context harvester --namespace harvester-system
kubectl get service longhorn-backend --kubeconfig /path/to/harvester.yaml --context harvester --namespace longhorn-system
kubectl get networkpolicy --kubeconfig /path/to/harvester.yaml --context harvester --namespace longhorn-system
```

The chart reads and refreshes the public KubeVirt CA automatically. No manual certificate copy is needed. It does not read private keys or change KubeVirt.

If existing NetworkPolicies block Longhorn metrics, see the optional setting below. Do not enable it just because no policies exist.

## 2. Add the repository

Add the repository if you have not done it yet:

```sh
helm repo add obs-dashboards https://raw.githubusercontent.com/kaioneuhauss/suse-observability-dashboards/main/helm
helm repo update obs-dashboards
```

**Expected result:** Helm confirms the repository is available.

## 3. Fill in your settings

Save this as `virtualization.yaml`, replacing the three values:

```yaml
clusterName: my-harvester
observability:
  url: https://observability.example.com
  otlpEndpoint: otlp-observability.example.com:443
```

`clusterName` must match the Agent's integration name. Use your actual kubeconfig, context and Agent namespace below:

## 4. Install the module

This command installs the module and waits for it to finish. Keep the values file for updates and reinstalls.

```sh
helm upgrade --install obs-virtualization obs-dashboards/suse-observability-virtualization \
  --version 1.3.0 --values virtualization.yaml \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports `STATUS: deployed`. Successful publishing Jobs are removed automatically.

## 5. Check the result

```sh
kubectl get pods,jobs --kubeconfig /path/to/harvester.yaml --context harvester \
  --namespace suse-observability --selector app.kubernetes.io/instance=obs-virtualization
kubectl logs deployment/obs-virtualization --container collector --since=5m \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace suse-observability
kubectl get virtualmachineinstances --all-namespaces --kubeconfig /path/to/harvester.yaml --context harvester
```

**Expected result:** collector Pods are ready. The publishing Jobs may already be gone; that is normal after success.

Open **Virtualization · VM & Host Overview**. Select the cluster and compare **Running VMs** with the running instances returned by kubectl. Check that the collection status panels show `1` for the expected targets. Guest memory depends on balloon statistics; guest filesystem data needs QEMU Guest Agent. A stopped VM has no current resource usage.

The [dashboard guide](virtualization-dashboards.md) explains the four views. For removal, use [Update, remove and reinstall](lifecycle.md).

## Optional: allow Longhorn metrics through an existing policy

Only use this when Longhorn managers are **already isolated** and you want to allow the collector to reach TCP/9500. Add to `virtualization.yaml`, then repeat the Helm install command:

```yaml
virtualization:
  longhorn:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

The rule allows the collector's Pod labels **and** its namespace together. With the example release, only `obs-virtualization` / `sre-kubevirt-telemetry` Pods in `suse-observability` match. Existing policies stay in place. Port 9500 also serves the Longhorn API, so this is access to that port, not an HTTP path restriction.

Creating the first ingress policy on previously unrestricted managers can block other traffic. If that is your situation, have the platform administrator design the policy first. To skip Longhorn collection, use `virtualization.longhorn.enabled: false`; its panels will have no data.

Check the applied rule when enabled:

```sh
kubectl get networkpolicy obs-virtualization-longhorn-metrics -o yaml \
  --kubeconfig /path/to/harvester.yaml --context harvester --namespace longhorn-system
```

## Optional: other dashboards on Harvester

Install [Imports](imports.md) to follow VMware imports. To add the [Kubernetes dashboards](kubernetes.md), use `mode: content`; Virtualization already collects the host and Pod data. Do not install a second host collector on the same ports.

## 6. Remove this module

Keep the publishing Secret available. The following command removes this release and, in the default mode, its managed dashboards and monitors:

```sh
helm uninstall obs-virtualization \
  --kubeconfig /path/to/harvester.yaml --kube-context harvester \
  --namespace suse-observability --wait --timeout 15m
```

**Expected result:** Helm reports the release was uninstalled. Your applications, VMs, volumes, SUSE server, official Agent and shared Secrets remain. Do not delete the namespace. A `telemetry` release only removes its collectors.

To reinstall, repeat step 4 with the same values file. If removal fails, follow [the removal guide](lifecycle.md#3-if-removal-fails) before retrying. Older versions need the [upgrade step](lifecycle.md#moving-from-120-or-121) first.
