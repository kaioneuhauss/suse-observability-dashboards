# Set up the server's OTLP gRPC endpoint

Skip this page if your SUSE server already has a working OTLP gRPC endpoint. This setup belongs to the **SUSE server cluster**, not Harvester. It changes the server's Helm release, so do it with the administrator who manages that release.

The endpoint can receive Virtualization metrics or telemetry from a separate application collector. It does not install application instrumentation. For applications, continue afterward with [application telemetry setup](application-telemetry.md).

The example uses Traefik and the server chart's existing OpenTelemetry Collector. For other ingress controllers or chart versions, follow the [official SUSE ingress guide](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/ingress.html).

## 1. Check the existing server

```sh
helm list --kubeconfig /path/to/observability.yaml --kube-context observability --namespace suse-observability
kubectl get service,ingress --kubeconfig /path/to/observability.yaml --context observability --namespace suse-observability
```

Note the installed **server chart version**, release name and gRPC Service name. The lab used server chart 2.10.2, release `suse-observability`, Service `suse-observability-otel-collector-grpc`, port 4317. This is a different version from the dashboard charts.

**Check:** the gRPC Service already exists. Save the existing server values privately before modifying the release:

```sh
helm get values suse-observability --kubeconfig /path/to/observability.yaml \
  --kube-context observability --namespace suse-observability -o yaml > server-values-backup.yaml
kubectl get ingressclass --kubeconfig /path/to/observability.yaml --context observability
```

The backup can contain credentials; keep it out of Git. The Traefik example requires the corresponding IngressClass and a compatible server chart; the official ingress guide documents this gRPC route for server charts from 2.8.0. Do not silently upgrade an older server to make the example fit.

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

| Parameter | What to fill in / why |
|---|---|
| `enabled` | Creates the ingress for the server's existing collector |
| `ingressClassName` | Your actual ingress controller class |
| `router.entrypoints` | Traefik's configured HTTPS entrypoint, `websecure` in this example |
| `hosts[].host` | DNS hostname covered by your certificate |
| `path`, `pathType` | Routes the gRPC request paths through `/` |
| `serviceName`, `port` | The existing gRPC Service and its 4317 port; not the UI Service |
| `tls[].hosts`, `secretName` | Same hostname and the TLS Secret containing its certificate/private key |

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

In `virtualization.yaml`, use `observability.otlpEndpoint: otlp-observability.example.com:443`, without `https://`. Return to [Virtualization](virtualization.md) or [application telemetry setup](application-telemetry.md).

## 5. Removing only an endpoint you added

Dashboard uninstall leaves this shared server configuration in place. If you later want to remove it, first confirm that **no** VM or application collector still uses it. Remove only your added host/TLS entries from the server owner's saved values and repeat the same-version Helm upgrade from step 3. If this was the only collector ingress, use `opentelemetry-collector.ingress.enabled: false` in a small override file. Verify the resulting ingress list. Delete its dedicated TLS Secret only after checking that nothing else references it; never uninstall the SUSE server for this cleanup.
