# SUSE Virtualization / Harvester

Este módulo instala coleta KubeVirt/Longhorn, métricas de host, inventário de recursos, um dashboard e cinco monitores. Instale **no cluster Harvester**, no namespace do Agent. Não exige o módulo Traefik nem o de aplicações.

## Pré-requisitos específicos

1. Complete os [pré-requisitos comuns](prerequisites.md).
2. Disponibilize um endpoint **OTLP gRPC com TLS** no SUSE. Use `host:443`, sem `https://`. Se ainda não existe, configure-o na instalação do servidor conforme a [documentação SUSE](https://documentation.suse.com/en-us/cloudnative/suse-observability/latest/en/setup/install-stackstate/kubernetes_openshift/ingress.html). O arquivo `prerequisites/otlp-ingress-values.yaml` é um fragmento a adaptar ao Service e IngressClass reais; não substitui os values completos do servidor.
3. Confirme no Harvester:

```bash
kubectl get svc kubevirt-prometheus-metrics --kubeconfig "$KCFG" --context "$CTX" -n harvester-system
kubectl get configmap kubevirt-ca --kubeconfig "$KCFG" --context "$CTX" -n harvester-system
kubectl get svc longhorn-backend --kubeconfig "$KCFG" --context "$CTX" -n longhorn-system
kubectl get networkpolicy --kubeconfig "$KCFG" --context "$CTX" -n longhorn-system
```

O chart lê a CA pública diretamente do ConfigMap `kubevirt-ca`, prepara o arquivo antes do Collector iniciar e sincroniza mudanças a cada 60 segundos. A permissão limita-se a `get` desse ConfigMap. Não lê chaves privadas e não modifica KubeVirt. A coleta mantém TLS e valida quatro nomes de servidor distintos. Um CA inválido nunca substitui a última cópia válida. Para uma instalação com CA preparada externamente, use `virtualization.kubevirt.ca.autoSync: false` e configure `existingConfigMap`.

4. Crie/reutilize o Secret de registry `application-collection` no namespace do Agent para baixar a imagem OTel de `dp.apps.rancher.io`. Use as credenciais da organização no Rancher/Harvester; não as grave em values. O chart também usa imagens públicas de node-exporter, vmagent e Python; verifique acesso ou espelhamento.
5. Confirme que o coletor pode acessar os endpoints KubeVirt e Longhorn. Em ambientes com NetworkPolicies isolando os managers Longhorn, é necessária permissão de entrada TCP/9500 a partir do coletor.

## Instalar

```bash
cp examples/virtualization.yaml local/virtualization.yaml
```

Edite somente os valores do ambiente:

```yaml
clusterName: meu-harvester
observability:
  url: https://observability.exemplo.com.br
  otlpEndpoint: otlp-observability.exemplo.com.br:443
```

Se os managers Longhorn **já estão isolados por NetworkPolicy** e essa permissão foi aprovada, acrescente:

```yaml
virtualization:
  longhorn:
    allowMetricsNetworkPolicy: true
    existingIsolationConfirmed: true
```

Essa regra permite apenas o coletor desta release/namespace e a porta 9500. A porta também atende à API Longhorn; avalie essa exposição interna. Não habilite a regra como primeira política de um Longhorn que não era isolado: uma política nova pode mudar o comportamento do tráfego existente. Se a organização não permite esse acesso, use `virtualization.longhorn.enabled: false`; os dois painéis Longhorn ficam sem dados e devem ser tratados como não aplicáveis.

```bash
helm upgrade --install obs-virtualization ./charts/suse-observability-virtualization \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$NS" \
  -f local/virtualization.yaml --wait --timeout 15m
kubectl logs deployment/obs-virtualization --kubeconfig "$KCFG" --context "$CTX" \
  -n "$NS" -c collector --since=5m
```

## Aceite

No Metrics Explorer, selecione o nome exato do cluster:

```promql
up{k8s_cluster_name="meu-harvester",job=~"(.*/)?(kubevirt-metrics|longhorn)"}
kubevirt_vmi_info{k8s_cluster_name="meu-harvester"}
longhorn_volume_robustness{k8s_cluster_name="meu-harvester"}
```

Os alvos habilitados devem ter `up=1`, com amostras posteriores à instalação. Compare a lista de VMs com as instâncias em execução no Harvester. Verifique CPU, memória, disco e filtros do dashboard. A memória do guest depende de estatísticas do balloon; filesystems dependem de QEMU Guest Agent. VMs desligadas não têm consumo atual. O painel de contagem mostra instâncias observadas, não todas as definições de VMs.

Longhorn expõe uma série por `state`: `1` significa que o volume está naquele estado. Capacidade física do host, tamanho lógico de volume e filesystem do guest são medições diferentes. Um volume saudável em um único host não oferece tolerância à perda desse host.

Se também quiser os dashboards Kubernetes no Harvester, publique o módulo Kubernetes com `mode: content`; reutilize os coletores deste módulo. Para etcd, confirme o endpoint local e habilite `telemetry.etcd.enabled: true` aqui. Não instale outro node-exporter nas mesmas portas.
