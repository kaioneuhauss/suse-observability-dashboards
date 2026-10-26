# Pré-requisitos comuns

Faça esta preparação antes de instalar um módulo. Se uma etapa já está pronta, apenas confira o resultado. Não reinstale o servidor ou o Agent para instalar dashboards.

## 0. Preparar o computador e os acessos

Use Bash no Linux, macOS ou WSL. Tenha Git, `curl`, `tar`, `sha256sum`, kubectl e Helm. No Linux x86_64, este exemplo instala ferramentas no diretório do projeto, sem sudo:

```bash
mkdir -p local/tools
cd local/tools
# Exemplo compativel com os clusters 1.34/1.35 deste laboratorio.
curl -fSLO https://dl.k8s.io/release/v1.35.2/bin/linux/amd64/kubectl
curl -fSLO https://dl.k8s.io/release/v1.35.2/bin/linux/amd64/kubectl.sha256
printf '%s  kubectl\n' "$(cat kubectl.sha256)" | sha256sum --check
curl -fSLO https://get.helm.sh/helm-v4.1.1-linux-amd64.tar.gz
curl -fSLO https://get.helm.sh/helm-v4.1.1-linux-amd64.tar.gz.sha256sum
sha256sum --check helm-v4.1.1-linux-amd64.tar.gz.sha256sum
tar -xzf helm-v4.1.1-linux-amd64.tar.gz linux-amd64/helm
chmod 755 kubectl linux-amd64/helm
export PATH="$PWD:$PWD/linux-amd64:$PATH"
cd ../..
kubectl version --client
helm version --short
```

Pare se algum download ou checksum falhar. Em outro terminal, ajuste novamente o PATH ou use uma instalação permanente. Para outro sistema/arquitetura, use [kubectl](https://kubernetes.io/docs/tasks/tools/) e [Helm](https://helm.sh/docs/intro/install/). Escolha kubectl compatível com seu API server; não trate a versão do laboratório como a mais recente.

**Obter o kubeconfig:** no Rancher, abra o cluster desejado e use a opção de download do kubeconfig. No Harvester, use a opção de kubeconfig do cluster. Salve em um diretório privado, dê permissão `chmod 600 /caminho/cluster.yaml` e nunca envie esse arquivo ao Git. Ele permite acesso ao ambiente.

Confira os contextos sem alterar o contexto global:

```bash
kubectl config get-contexts --kubeconfig /caminho/cluster.yaml
```

O nome da coluna `NAME` será `CTX` nos exemplos. A conta precisa poder criar os recursos do chart, incluindo RBAC e DaemonSets. Não use credenciais de outra organização ou contexto por engano.

**SUSE ainda não existe?** Um administrador deve primeiro instalar o servidor conforme os [requisitos e instalação oficiais](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/requirements.html), configurar DNS/certificado e confirmar login na URL HTTPS. Sizing, licença e persistência do servidor não são definidos por este projeto.

**Agent ainda não existe?** Na instância SUSE, abra a integração/StackPack Kubernetes, adicione uma instância para o cluster, escolha um nome estável e siga os comandos Helm gerados pela própria instância. Eles contêm o endereço e a credencial adequados à sua versão. Guarde-os fora do Git. No Harvester 1.8, confira também o [add-on SUSE Observability Agent](https://docs.harvesterhci.io/v1.8/advanced/addons/suse-observability-agent/), identificado como experimental na documentação dessa versão. Espere o cluster aparecer no SUSE com nós e pods antes de continuar.

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

O nome legado da chave não obriga o uso de uma API key antiga: pode conter a credencial de ingestão fornecida pela integração oficial. A documentação atual recomenda Service Tokens e anuncia a descontinuação de API keys. Siga o fluxo da versão instalada; não troque o Secret do Agent apenas para instalar este projeto. [Autenticação de ingestão](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/security/k8s-ingestion-api-keys.html).

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

Para criar o arquivo temporário sem deixar o token literal no histórico do terminal, use Bash:

```bash
umask 077
TOKEN_FILE=$(mktemp)
read -r -s -p 'Cole o Service Token de publicacao: ' PUBLISH_TOKEN
printf '\n'
printf '%s' "$PUBLISH_TOKEN" > "$TOKEN_FILE"
unset PUBLISH_TOKEN
kubectl create secret generic suse-observability-publisher-token \
  --kubeconfig "$KCFG" --context "$CTX" -n "$NS" \
  --from-file=serviceToken="$TOKEN_FILE"
rm -f "$TOKEN_FILE"
unset TOKEN_FILE
```

Execute uma das duas formas de criação, não ambas. Se o Secret já existe, confirme sua finalidade e reutilize-o; não o substitua automaticamente. Não copie a credencial para o chat, values ou README.

Quando já existem dois Secrets proprietários, configure no arquivo do módulo:

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

Confira a URL sem enviar credenciais:

```bash
curl --head --fail --show-error "$OBS_URL"
```

Esse teste confirma somente DNS/HTTPS a partir do computador; os Pods também precisam alcançar o destino. Se a empresa usa CA privada, instale a CA confiável no computador e monte o Secret nos componentes pertinentes. Não use `-k` como solução.

## Pronto para instalar?

| Conferência | Resultado esperado |
|---|---|
| `kubectl get nodes` com KCFG/CTX explícitos | Cluster correto e nós esperados |
| Pods do Agent | Prontos e integração visível no SUSE |
| ConfigMap de nome da integração | Nome que será usado em `clusterName` |
| Secret de ingestão | Existe na origem com a chave esperada |
| Secret de publicação | Existe somente onde o conteúdo será publicado |
| Pré-requisito do módulo | OTLP/imagens, Traefik metrics, VMIC ou instrumentação, conforme o caso |

Volte ao [README](../README.md#instalar--exemplo-completo-para-harvester). O comando `configure` preenche automaticamente o nome da integração quando usa o ConfigMap padrão. Se sua instalação tem nomes personalizados, copie o exemplo e preencha os campos manualmente.

Referências: [instalação SUSE](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/install-stackstate/requirements.html), [Service Tokens](https://documentation.suse.com/cloudnative/suse-observability/latest/en/use/security/k8s-service-tokens.html), [roles](https://documentation.suse.com/cloudnative/suse-observability/latest/en/setup/security/rbac/rbac_roles.html), [Agent Harvester 1.8](https://docs.harvesterhci.io/v1.8/advanced/addons/suse-observability-agent/). A documentação `latest` pode descrever funcionalidades posteriores à versão instalada; o laboratório deste projeto usa SUSE 2.10.2.
