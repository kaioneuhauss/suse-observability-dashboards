# Atualização, migração e remoção

## Atualizar

Preserve os arquivos de values, releases, namespaces e tokens proprietários. Confira o diff, renderize e execute novamente `helm upgrade --install` do módulo. O publicador compara a definição persistida com a desejada. Se não mudou, não recria o dashboard. Quando muda, a estratégia padrão `replace` pode alterar seu ID e substitui edições manuais. Não edite diretamente um dashboard gerenciado esperando que o chart preserve essas alterações.

Os Jobs baixam uma CLI fixada e verificam seu hash. A identidade precisa ter acesso ao objeto antigo; um 403 interrompe a operação antes de criar duplicatas. Faça exportação externa antes de atualização relevante: o backup temporário do Job não substitui um backup persistente.

## Migrar do pacote antigo

A revisão anterior permanece no histórico Git (`c059f58`). Antes de remover qualquer recurso:

1. Liste Helm, Pods, RBAC, Services, ConfigMaps e políticas do projeto nos três clusters. Confirme a propriedade Helm/Fleet.
2. Salve `helm get values`, `helm get manifest` e exports dos dashboards/monitores. Guarde fora do repositório, com acesso restrito. Registre o dashboard nativo que deve continuar existindo.
3. Prepare os novos values e valide com `helm lint`, `helm template` e dry-run no API server. Para ConfigMaps grandes, use `kubectl apply --server-side --dry-run=server`; não use a anotação client-side de `kubectl apply`.
4. No chart antigo `suse-observability-content`, use `lifecycle.action: delete` e `lifecycle.confirmDelete: DELETE_MANAGED_OBJECTS`. Confira a ausência apenas dos cinco dashboards/33 monitores antigos. Não apague conteúdo por wildcard.
5. Desinstale somente as releases antigas identificadas: `sre-platform-telemetry` em cada origem, `kubevirt-otel-collector` no Harvester e `suse-observability-content` no central. Remova os dois Jobs hook antigos por nome exato. Não apague namespaces, PVCs ou plataformas.
6. Confirme a ausência dos coletores antigos. Instale os módulos desejados e faça o [aceite](validation.md). Se ocorrer falha, pare aquele módulo e restaure seu chart/values e definições exportadas; IDs de dashboards podem mudar.

O servidor SUSE, Agents oficiais, Rancher, Harvester, monitoramento nativo, VMs e volumes não pertencem à limpeza deste projeto. Aplicações de demonstração exigem uma decisão separada. O histórico de métricas existente é preservado; “do zero” refere-se aos componentes e conteúdo deste projeto, não ao apagamento do backend.

## Remover um módulo

Se a release publica conteúdo (`all` ou `content`), remova primeiro os objetos externos enquanto o token ainda funciona:

```bash
helm upgrade obs-traefik ./charts/suse-observability-traefik \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$NS" \
  -f local/traefik.yaml \
  --set lifecycle.action=delete \
  --set lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS \
  --wait --timeout 15m
```

Confira nos logs a ausência de todos os objetos do módulo, depois:

```bash
helm uninstall obs-traefik --kubeconfig "$KCFG" --kube-context "$CTX" -n "$NS" --wait
kubectl delete job obs-traefik-dashboards obs-traefik-monitors --ignore-not-found \
  --kubeconfig "$KCFG" --context "$CTX" -n "$NS"
```

Substitua nomes e arquivo pelo módulo correspondente. `helm uninstall` sozinho não remove conteúdo externo do SUSE. Jobs hooks podem sobreviver à release até o TTL de 24h; a exclusão por nomes exatos limpa imediatamente.

Para uma release `telemetry`, basta `helm uninstall` no cluster de origem. Não execute a etapa de exclusão de conteúdo em uma release coletora. Remova ou revogue Secrets exclusivos do projeto somente após confirmar que nenhum outro módulo os utiliza.
