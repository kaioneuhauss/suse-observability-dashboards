# Aceite e diagnóstico

## 1. Recursos e publicadores

```bash
helm status obs-traefik --kubeconfig "$KCFG" --kube-context "$CTX" -n "$NS"
kubectl get pods,jobs --kubeconfig "$KCFG" --context "$CTX" -n "$NS"
kubectl logs job/obs-traefik-dashboards --kubeconfig "$KCFG" --context "$CTX" -n "$NS"
kubectl logs job/obs-traefik-monitors --kubeconfig "$KCFG" --context "$CTX" -n "$NS"
```

Troque `obs-traefik` pela release instalada. Os publicadores são Jobs finitos; `Complete` é esperado. Os logs devem confirmar as definições persistidas. `Running`, `Ready`, Helm `deployed` e `Events: <none>` não provam que uma métrica chega corretamente.

## 2. Telemetria

Aguarde pelo menos dois scrapes de 30s e o tempo de ingestão. Use Metrics Explorer para verificar `up`, idade da última amostra, número esperado de alvos e identidade do cluster. Confira logs recentes dos coletores procurando TLS, 401/403, timeouts, fila crescente ou dados descartados.

O modo OTLP pode prefixar `job` com `default/`; as consultas KubeVirt/Longhorn deste pacote aceitam essa forma. Remote write usa `cluster_name`; OTLP KubeVirt usa `k8s_cluster_name`. O mesmo nome de integração precisa ser preservado em ambos.

## 3. Painéis e filtros

Abra cada dashboard publicado. Teste Everything, cada cluster, namespace/aplicação/VM e uma seleção sem correspondência. Ao mudar o cluster, restaure os filtros dependentes para Everything. Compare ao menos uma série com a origem, mantendo a mesma janela e unidade.

`No data` pode significar ausência de tráfego, VM desligada, guest sem estatísticas, coletor bloqueado, label diferente ou série não aplicável. Não complete com zero para “deixar verde”. Janelas longas terão histórico parcial após uma coleta nova. Porcentagens de disponibilidade não equivalem a prova de um SLO de 30 dias.

Para auditar as consultas via API, um operador pode usar o script de desenvolvimento, com um endpoint de consulta autorizado:

```bash
python3 scripts/audit-queries.py --url http://127.0.0.1:18428 \
  --module virtualization --hours 1 --output local/query-audit.json
```

O script testa os filtros disponíveis e uma seleção inexistente. Esse endpoint local precisa ser preparado pelo operador; o script não abre túneis nem usa credenciais implicitamente. A consulta direta ao backend valida expressões/dados, mas não substitui permissões, escopo e apresentação na API/interface SUSE.

## 4. Monitores e notificações

Confirme Enabled, resultados recentes e associação ao componente correto. Configure canais e regras de notificação no SUSE. Em ambiente de teste autorizado, provoque um evento controlado e confirme abertura, notificação e recuperação. A publicação da regra não comprova entrega de e-mail ou paging.

## Falhas comuns

| Sintoma | Verificação decisiva |
|---|---|
| 403 no publicador | Permissões, dono do dashboard, token expirado; não trocar identidade como contorno |
| KubeVirt `unknown authority` | CA atual, logs de `prepare-ca`/`sync-ca`, permissão `get` no ConfigMap e nomes TLS |
| Longhorn timeout | EndpointSlice pronto, políticas existentes e acesso do coletor à porta 9500 |
| Traefik sem métricas | Flags Prometheus, selector/porta e política de entrada; não expor métricas publicamente |
| Aplicação sem dados | Contrato de métricas/labels/unidade, presença de buckets e tráfego |
| Host exporter não agenda | Coletor duplicado na mesma porta, tolerations e admissão de hostNetwork/mounts |
| Fleet recria recurso removido | Corrigir o GitRepo/Bundle proprietário antes de limpar a cópia reconciliada |
