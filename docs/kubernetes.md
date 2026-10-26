# Kubernetes / RKE2

Módulo opcional com dois dashboards: saúde da plataforma e eficiência de recursos. Inclui node-exporter, inventário de requests/limits e 21 monitores. A coleta etcd é opcional e desligada por padrão.

## Instalar

Complete os [pré-requisitos comuns](prerequisites.md), especialmente o Agent e o nome exato da integração.

```bash
cp examples/kubernetes.yaml local/kubernetes.yaml
```

Preencha `clusterName` e `observability.url`. Em RKE2, confirme por acesso aprovado aos nós que `http://127.0.0.1:2381/metrics` responde em **cada nó etcd** antes de adicionar:

```yaml
telemetry:
  etcd:
    enabled: true
```

O coletor usa host networking, somente nos nós com `node-role.kubernetes.io/etcd=true`. Não publica a porta nem altera o etcd. Se o endpoint não existe, mantenha a opção desligada e confira a documentação/configuração da versão.

```bash
helm upgrade --install obs-kubernetes ./charts/suse-observability-kubernetes \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$NS" \
  -f local/kubernetes.yaml --wait --timeout 15m
```

## Aceite

Confirme `up{job="sre-node"}` por nó e `up{job="sre-etcd"}` por membro habilitado. Confira o sucesso do inventário, requests/limits, PVCs e filtros. O dashboard separa utilização, reserva e limite. CPU alta isoladamente é contexto; combine com latência, throttling e impacto no serviço.

Os monitores etcd não recebem séries onde a coleta não foi habilitada. Para não publicar monitores neste módulo, use `content.monitors.enabled: false`; a seleção individual de regras pertence à fonte de desenvolvimento. Não interprete falta de dados como etcd saudável.

Se o módulo Virtualization já coleta hosts e pods neste cluster, use este módulo em `mode: content`. Habilite etcd no módulo Virtualization, se necessário. Assim não haverá duplicação de node-exporter nem disputa pelas portas locais.
