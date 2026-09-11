# Validation: results and customer acceptance

## Observed in the lab on 11 September 2026

| Check | Result |
|---|---|
| Persisted dashboards | Five definitions matched the published content |
| Interface | 131 panels reviewed; 125 metric panels and six explanatory panels |
| Queries and filter combinations | 3452 cases, zero query errors, zero non-finite values; 715 empty results required scope/applicability interpretation |
| Collectors | 23 Pods Ready; recent log review found no collection errors |
| Controlled HTTP tests | Request Lab and Traefik counter deltas matched controlled request/status counts |
| Monitors | 33 project monitors; existing native monitors preserved |
| Email | Recipient confirmed real HTTP opening and recovery notifications |
| Code and charts | Unit tests and Helm 3/4 checks passed for the released implementation |

These are recorded lab results, not a fresh health claim for today or certification of another customer. The detailed [test record](../tests/RESULTADOS.md), [UI review](../tests/UI-VALIDATION.md) and [request matrix](../tests/MATRIZ-SOLICITACOES.md) retain methods and limitations.

The documentation revision passed 31 unit tests, Helm 3.19/4.1 lint/template checks for the five existing and four short profiles, local Markdown link checks and Bash syntax checks. Both PDFs were rendered and visually reviewed. The short profiles also passed shared-Secret apply/delete rendering checks. Reusing the default SUSE publisher role is based on official documentation; the live lab retained its restricted tokens. No new-server installation was performed to validate that alternative end to end.

## Repeat this checklist in each customer

1. **Origin:** compare actual nodes, etcd members, Traefik replicas and VMs with collector targets. Every expected source needs a healthy sample, not just one per cluster.
2. **Transport:** collector Pods are Ready, logs have no recurring errors, remote-write/OTLP delivery is healthy, and samples are recent.
3. **Content:** both publisher Jobs completed and their verified counts match the selected catalog.
4. **Filters:** open each deployed dashboard. Check each cluster and relevant namespace/application; reset dependent filters after switching clusters. Exclude unavailable sources such as Traefik on an NGINX-only Harvester.
5. **Meaning:** compare Pod CPU/memory with Kubernetes and host filesystems with the OS. Check units, time ranges and missing-data descriptions.
6. **Traffic:** run a bounded request test, record start/end and status counts, allow ingestion, then compare the same application/time window. Browser achieved rate and a five-minute rate are different measurements.
7. **Alerts:** verify resource identity, value, threshold and investigation link; test real opening/recovery and delivery with approved destinations.
8. **Impact:** measure canary overhead and storage trend before rollout to all clusters.

For a cluster with Traefik enabled:

```bash
helm test sre-platform-telemetry \
  --kubeconfig "$KCFG" --kube-context "$CTX" -n "$AGENT_NS" \
  --logs --timeout 3m
```

This tests metrics reachability from the collector namespace. It does not prove ingestion. In Metrics Explorer, inspect these queries and compare their labels/counts with the inventory:

```promql
up{job=~"sre-node|sre-etcd|traefik"}
sre_pod_inventory_success
up{service_name="kubevirt-metrics"}
```

An empty applicable query needs investigation. An inapplicable metric, such as etcd peer latency on a single-member cluster, needs explanation. Neither should silently become a healthy zero.
