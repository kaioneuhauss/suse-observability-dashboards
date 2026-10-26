# Set up OTLP access for Virtualization

Skip this page if your SUSE server already has a working OTLP gRPC endpoint. This setup belongs to the **SUSE server cluster**, not Harvester. It changes the server's Helm release, so do it with the administrator who manages that release.

The example uses Traefik and the server chart's existing OpenTelemetry Collector. For other ingress controllers or chart versions, follow the [official SUSE ingress guide](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/ingress.html).

## 1. Check the existing server

```sh
helm list --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability
kubectl get service,ingress --kubeconfig /path/to/observability.yaml --context observability --namespace suse-observability
```

Note the installed **server chart version**, release name and gRPC Service name. The lab used server chart 2.10.2, release `suse-observability`, Service `suse-observability-otel-collector-grpc`, port 4317. This is a different version from the dashboard charts.

You also need a DNS record pointing your chosen OTLP hostname to the ingress address and a certificate covering that hostname. DNS and certificate issuance are managed by your existing infrastructure. If you have a certificate and private key ready, create its Secret:

```sh
kubectl create secret tls otlp-tls --cert=/private/tls.crt --key=/private/tls.key \
  --kubeconfig /path/to/observability.yaml --context observability --namespace suse-observability
```

Reuse an existing valid TLS Secret instead when available.

## 2. Save the ingress values

Save as `otlp-ingress.yaml`. Replace the host, Service name, IngressClass and TLS Secret if needed:

```yaml
opentelemetry-collector:
  ingress:
    enabled: true
    ingressClassName: traefik
    annotations:
      traefik.ingress.kubernetes.io/router.entrypoints: websecure
    hosts:
      - host: otlp-observability.example.com
        paths:
          - path: /
            pathType: Prefix
            serviceName: suse-observability-otel-collector-grpc
            port: 4317
    tls:
      - hosts:
          - otlp-observability.example.com
        secretName: otlp-tls
```

If the collector already has ingress hosts, merge them into this file. Helm replaces lists; do not drop existing endpoints.

## 3. Apply to the existing server release

Add the official repository if needed. Use the **installed server chart version** to avoid an unintended server upgrade. Replace `SERVER_CHART_VERSION` below with the value from step 1:

```sh
helm repo add suse-observability https://charts.rancher.com/server-charts/prime/suse-observability
helm repo update suse-observability
helm upgrade suse-observability suse-observability/suse-observability \
  --version SERVER_CHART_VERSION --reuse-values --values otlp-ingress.yaml \
  --kubeconfig /path/to/observability.yaml --kube-context observability \
  --namespace suse-observability --wait --timeout 15m
```

This assumes a directly managed Helm release. For Fleet-managed installations, change the owning configuration instead. Preserve all existing server settings.

## 4. Check and use the address

```sh
kubectl get ingress suse-observability-otel-collector \
  --kubeconfig /path/to/observability.yaml --context observability --namespace suse-observability
kubectl get service suse-observability-otel-collector-grpc -o yaml \
  --kubeconfig /path/to/observability.yaml --context observability --namespace suse-observability
```

Check the host, TLS certificate and gRPC backend. The lab Service has the Traefik `service.serversscheme: h2c` annotation for the internal hop. The external collector connection still uses TLS. An Ingress object alone does not prove that ingestion works: after installing Virtualization, verify collector logs and fresh metrics.

In `virtualization.yaml`, use `observability.otlpEndpoint: otlp-observability.example.com:443`, without `https://`. Return to [Virtualization](virtualization.md).
