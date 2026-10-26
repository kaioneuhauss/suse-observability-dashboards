# Pré-requisitos comuns

## 1. Confirmar o destino

Instale Helm 3/4 e kubectl. Use kubeconfig e contexto explícitos. O namespace abaixo é aquele onde o Agent já existe; ele pode ser `suse-observability-agent` ou `suse-observability`.

```bash
export KCFG=/caminho/cluster.yaml
export CTX=meu-contexto
export NS=suse-observability-agent
kubectl get nodes --kubeconfig "$KCFG" --context "$CTX"
helm list --all-namespaces --kubeconfig "$KCFG" --kube-context "$CTX"
kubectl get pods --kubeconfig "$KCFG" --context "$CTX" -n "$NS"
kubectl get configmap suse-observability-agent-cluster-name \
  --kubeconfig "$KCFG" --context "$CTX" -n "$NS" \
  -o jsonpath='{.data.STS_CLUSTER_NAME}{"\n"}'
```

Use o nome retornado em `clusterName`, exatamente como cadastrado na integração Kubernetes do SUSE. O nome do contexto pode ser diferente. Os charts adicionais não substituem a instalação oficial do Agent. No Harvester, confira o método e o status de suporte do add-on na documentação da sua versão.

## 2. Ingestão: reutilizar o Secret do Agent

Confirme a existência do Secret e o nome de sua chave, sem imprimir o valor:

```bash
kubectl get secret suse-observability-agent-secrets \
  --kubeconfig "$KCFG" --context "$CTX" -n "$NS" \
  -o go-template='{{range $key, $value := .data}}{{$key}}{{"\n"}}{{end}}'
```

O padrão espera `STS_API_KEY`. Se sua instalação usa outro nome:

```yaml
ingestion:
  existingSecret: meu-secret-de-ingestao
  secretKey: STS_API_KEY
```

Garanta DNS, TLS e acesso de saída à instância SUSE e aos registries. Os coletores de host exigem Linux, host networking e mounts de host somente para leitura. Valide isso nas políticas de admissão. Não execute dois coletores adicionais para os mesmos alvos.

## 3. Publicação: preparar um Service Token

O token de ingestão não publica dashboards. Peça ao administrador um **Service Token com leitura, criação, alteração e exclusão de dashboards e monitores**. Na própria instância, abra a opção CLI para instalar e autenticar `sts`. Consulte as permissões efetivas antes de usar uma role:

```bash
sts rbac describe-permissions --context CONTEXTO-ADMIN --subject stackstate-k8s-troubleshooter
sts service-token create --context CONTEXTO-ADMIN \
  --name dashboard-publisher --roles stackstate-k8s-troubleshooter \
  --expiration AAAA-MM-DD
```

A role padrão tem permissões adicionais. Use uma role dedicada se a política da organização exigir menor privilégio. Não coloque tokens em Git ou em values. Guarde o token no cofre; para criar o Secret a partir de arquivo protegido sem newline:

```bash
kubectl create secret generic suse-observability-publisher-token \
  --kubeconfig "$KCFG" --context "$CTX" -n "$NS" \
  --from-file=serviceToken=/caminho-seguro/token
```

Esse Secret fica no cluster/namespace em que os Jobs rodam. Um mesmo Secret atende ambos os Jobs. Em instalações existentes, preserve a identidade proprietária dos dashboards e os Secrets já usados:

```yaml
auth:
  dashboards:
    existingSecret: suse-observability-dashboard-token
  monitors:
    existingSecret: suse-observability-monitor-token
```

Uma identidade diferente com permissões semelhantes pode não ser proprietária dos dashboards antigos. Um erro 403 exige revisar acesso/propriedade; o publicador não cria uma cópia como contorno.

## 4. TLS, imagens e rede

- Publicação: HTTPS para a API SUSE e download da CLI 3.3.6, conferido por SHA-256; requer nó Linux amd64. Em air gap, forneça imagem própria com a CLI e `content.publisher.cli.path`.
- Virtualization: OTLP gRPC com TLS, CA KubeVirt e acesso interno ao Longhorn. O chart acompanha automaticamente a CA pública; veja o guia do módulo.
- Traefik: endpoint de métricas interno, porta 9100. A habilitação pertence à configuração do Traefik existente.
- CA privada da instância: use Secrets de CA nos respectivos blocos `content.publisher.caSecret`, `telemetry.remoteWrite.caSecret` e `virtualization.otlp.caSecret`. Cada bloco usa `ca.crt` por padrão. Nunca desabilite a validação TLS.

Referências: [instalação SUSE](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/requirements.html), [Service Tokens](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/security/k8s-service-tokens.html), [roles](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/security/rbac/rbac_roles.html), [Agent Harvester 1.8](https://docs.harvesterhci.io/v1.8/advanced/addons/suse-observability-agent/). A documentação `latest` pode descrever funcionalidades posteriores à versão instalada; o laboratório deste projeto usa SUSE 2.10.2.
