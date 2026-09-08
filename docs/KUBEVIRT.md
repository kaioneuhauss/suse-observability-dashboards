# KubeVirt collection on Harvester

[Back to installation](../README.md#3-install-kubevirt-collection-on-harvester)

Install this collector **once in the Harvester Kubernetes cluster**, not inside every VM. It discovers KubeVirt metrics through EndpointSlices, verifies HTTPS certificates and sends metrics to SUSE using OTLP gRPC. The separate platform telemetry chart collects the physical host's OS and etcd metrics.

## 1. Check the Service and public CA

Use the `SRE_HRV_KCFG` and `SRE_HRV_CTX` variables from the README:

```bash
kubectl get service kubevirt-prometheus-metrics \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace harvester-system -o yaml
kubectl get endpointslices \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace harvester-system \
  --selector kubernetes.io/service-name=kubevirt-prometheus-metrics
kubectl get configmap kubevirt-ca \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace harvester-system -o jsonpath='{.data.ca-bundle}' \
  > /tmp/kubevirt-ca.pem
openssl x509 -in /tmp/kubevirt-ca.pem -noout -subject -issuer -dates
```

The CA must come from the target Harvester installation. Adjust discovery if the namespace, Service, labels or ConfigMap differ.

The baseline has four component identities. Verify them in your environment rather than disabling TLS checks:

| Component | Expected certificate name in this template |
| --- | --- |
| virt-api | `virt-api.harvester-system.svc` |
| virt-controller | `virt-controller.harvester-system.svc` |
| virt-handler | `virt-handler.harvester-system.svc` |
| virt-operator | `kubevirt-operator-webhook.harvester-system.svc` |

For each component, choose a pod and check the advertised metrics port. Example for virt-api:

```bash
kubectl get pods --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace harvester-system --selector kubevirt.io=virt-api -o wide
SRE_KV_POD="$(kubectl get pods \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace harvester-system --selector kubevirt.io=virt-api \
  -o jsonpath='{.items[0].metadata.name}')"
kubectl port-forward "pod/$SRE_KV_POD" \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace harvester-system 18443:8443
```

In another terminal:

```bash
export SRE_KV_DNS="virt-api.harvester-system.svc"
openssl s_client -connect 127.0.0.1:18443 \
  -CAfile /tmp/kubevirt-ca.pem \
  -servername "$SRE_KV_DNS" -verify_hostname "$SRE_KV_DNS" \
  -verify_return_error </dev/null
curl --fail --silent --show-error --cacert /tmp/kubevirt-ca.pem \
  --resolve "$SRE_KV_DNS:18443:127.0.0.1" \
  "https://$SRE_KV_DNS:18443/metrics" --output /tmp/kubevirt-metrics.txt
```

Require successful certificate verification and HTTP 200. Stop the tunnel with Ctrl+C, then repeat for the other component names and any replicas with different certificates. Testing one randomly selected Service endpoint does not verify all component certificates.

## 2. Configure values and Secrets

```bash
cp config/kubevirt.values.yaml config/local/kubevirt.values.yaml
```

Edit these values in `config/local/kubevirt.values.yaml`:

| Value | Set it to |
| --- | --- |
| `config.exporters.otlp_grpc/suse-observability.endpoint` | Your SUSE OTLP gRPC `hostname:443`, without `https://`; not the remote-write URL |
| `config.processors.resource.attributes[0].value` | Exact Harvester integration name, replacing `HARVESTER_CLUSTER_NAME` |
| Each scrape job's `tls_config.server_name` | Verified certificate name for that component |
| Discovery namespace and Service selector | Actual KubeVirt namespace and Service labels |
| `imagePullSecrets` | Your SUSE Application Collection pull Secret |

The image and chart versions are different: the baseline uses upstream chart **0.165.0** and SUSE Collector image **0.156.0-k8s-13.1**. Do not substitute an upstream core image without verifying that it contains the receivers, processors, exporter and authentication extension used here.

Create the namespace and ingestion Secret:

```bash
kubectl create namespace open-telemetry \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --dry-run=client -o yaml | kubectl apply \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" -f -

umask 077
SRE_KEY_FILE="$(mktemp)"
read -r -s -p "SUSE ingestion API key: " SRE_INPUT_KEY
printf '\n'
printf '%s' "$SRE_INPUT_KEY" > "$SRE_KEY_FILE"
unset SRE_INPUT_KEY
kubectl create secret generic open-telemetry-collector \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace open-telemetry --from-file=API_KEY="$SRE_KEY_FILE"
rm -f "$SRE_KEY_FILE"
unset SRE_KEY_FILE
```

For the default SUSE image, prepare your authenticated Docker configuration outside this repository and create the registry Secret:

```bash
kubectl create secret generic application-collection \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace open-telemetry --type=kubernetes.io/dockerconfigjson \
  --from-file=.dockerconfigjson=/PATH/dockerconfig.json
```

Reuse valid Secrets during upgrades. The ingestion key and registry credentials are different secrets.

## 3. Render and install through Helm

The chart creates the public-CA ConfigMap through `extraManifests`. Do not create that ConfigMap separately. The CA checksum triggers a pod update when the bundle changes.

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update open-telemetry

helm template kubevirt-otel-collector open-telemetry/opentelemetry-collector \
  --version 0.165.0 --namespace open-telemetry \
  --values config/local/kubevirt.values.yaml \
  --set-file 'extraManifests[0].data.ca-bundle=/tmp/kubevirt-ca.pem' \
  > /tmp/kubevirt-rendered.yaml
kubectl apply --dry-run=server \
  --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  -f /tmp/kubevirt-rendered.yaml

helm upgrade --install kubevirt-otel-collector open-telemetry/opentelemetry-collector \
  --version 0.165.0 \
  --kubeconfig "$SRE_HRV_KCFG" --kube-context "$SRE_HRV_CTX" \
  --namespace open-telemetry --values config/local/kubevirt.values.yaml \
  --set-file 'extraManifests[0].data.ca-bundle=/tmp/kubevirt-ca.pem' \
  --wait --timeout 5m
```

If the SUSE OTLP endpoint uses a private CA, mount that public CA as well and set the exporter's `tls.ca_file`. The KubeVirt scrape CA and SUSE receiver CA need not be the same. The template does not synchronize a CA across namespaces: after rotation, retrieve the new bundle, verify it and repeat the Helm upgrade.

## 4. Validate real data

```bash
kubectl get deployment,pods --kubeconfig "$SRE_HRV_KCFG" \
  --context "$SRE_HRV_CTX" --namespace open-telemetry
kubectl logs --kubeconfig "$SRE_HRV_KCFG" --context "$SRE_HRV_CTX" \
  --namespace open-telemetry \
  --selector app.kubernetes.io/instance=kubevirt-otel-collector --since=10m
```

In Metrics Explorer, replace `harvester` with your integration name:

```promql
up{service_name="kubevirt-metrics",k8s_cluster_name="harvester"}
time() - timestamp(kubevirt_vmi_memory_usable_bytes{k8s_cluster_name="harvester"})
kubevirt_vmi_filesystem_used_bytes{k8s_cluster_name="harvester"}
```

Require healthy targets and recent samples from running VMs. Compare memory with `/proc/meminfo` inside the guest and filesystem usage with `df` on the same mount. Guest OS memory, configured memory, requests/limits and the host QEMU process are different measurements. Raw Block PVC allocation is not guest filesystem usage.

See [SUSE's KubeVirt collection overview](https://www.suse.com/c/monitoring-suse-virtualization-environment/) and [the upstream Collector chart](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-collector).
