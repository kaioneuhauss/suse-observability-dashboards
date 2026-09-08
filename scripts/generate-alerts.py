#!/usr/bin/env python3
"""Native SUSE threshold monitors; duration encoded in PromQL, not an invented `for` field."""
import json,yaml
from pathlib import Path
P=Path(__file__).resolve().parents[1];O=P/'alerts';O.mkdir(exist_ok=True)
N='cluster_name,node';NK='urn:kubernetes:/${cluster_name}:node/${node}';PK='urn:kubernetes:/${cluster_name}:${namespace}:pod/${pod_name}';VK='urn:kubernetes:/${cluster_name}:${namespace}:persistent-volume-claim/${persistentvolumeclaim}';CK='urn:kubernetes:/${cluster_name}:${namespace}:daemonset/${daemonset}'
E='job="sre-etcd"';S='job="sre-node",device!~"/dev/loop[0-9]+",mountpoint!~"/var/lib/kubelet/.*",fstype!~"tmpfs|overlay|squashfs"';F='cluster_name,node,device,mountpoint';K='cluster_name,namespace,pod_name,container';V='cluster_name,namespace,persistentvolumeclaim'
rules=[]
def add(slug,name,expr,compare,threshold,severity,urn,labels,desc,runbook,enabled=True):
 rules.append(dict(slug=slug,name='SRE · '+name,query=expr,comparator=compare,threshold=threshold,severity=severity,urnTemplate=urn,titleTemplate='SRE · '+name+' · '+labels,alias=labels,description=desc,remediation=runbook,enabled=enabled))
def high(e,d):return f'min_over_time(({e})[{d}:30s])'
def low(e,d):return f'max_over_time(({e})[{d}:30s])'
etcdguide='1. Confira quorum, membros e conectividade.\n2. Correlacione eleições, fsync, commits, RTT, logs anteriores e reinícios.\n3. Preserve snapshots antes de qualquer recuperação.'
add('etcd-no-leader','etcd without leader · 1m',low(f'max by ({N}) (etcd_server_has_leader{{{E}}})','1m'),'LT',1,'CRITICAL',NK,'${node}','Crítico quando um membro não enxerga líder durante 1 minuto. Coleta ausente tem monitor separado.',etcdguide)
for slug,name,expr,th,d in [
 ('etcd-elections','etcd leader changes above 3 in 15m',f'max by ({N}) (increase(etcd_server_leader_changes_seen_total{{{E}}}[15m]))',3,'5m'),
 ('etcd-failed','etcd failed proposals in 15m',f'max by ({N}) (increase(etcd_server_proposals_failed_total{{{E}}}[15m]))',0,'5m'),
 ('etcd-pending','etcd pending proposals above 100',f'max by ({N}) (etcd_server_proposals_pending{{{E}}})',100,'5m'),
 ('etcd-lag','etcd apply backlog above 1000',f'clamp_min(max by ({N}) (etcd_server_proposals_committed_total{{{E}}}) - max by ({N}) (etcd_server_proposals_applied_total{{{E}}}),0)',1000,'5m'),
 ('etcd-fsync','etcd WAL p99 above 10ms',f'histogram_quantile(0.99,sum by (cluster_name,node,le) (rate(etcd_disk_wal_fsync_duration_seconds_bucket{{{E}}}[5m])))',.01,'5m'),
 ('etcd-commit','etcd commit p99 above 25ms',f'histogram_quantile(0.99,sum by (cluster_name,node,le) (rate(etcd_disk_backend_commit_duration_seconds_bucket{{{E}}}[5m])))',.025,'5m'),
 ('etcd-quota','etcd database above 80 percent quota',f'max by ({N}) (etcd_mvcc_db_total_size_in_bytes{{{E}}}) / max by ({N}) (etcd_server_quota_backend_bytes{{{E}}})',.8,'10m')]:add(slug,name,high(expr,d),'GT',th,'DEVIATING',NK,'${node}',f'Condição persistente por {d}; limiar inicial de diagnóstico, ajustável ao baseline.',etcdguide)
add('etcd-scrape','etcd scrape failing · 3m',low(f'min by ({N}) (up{{{E}}})','3m'),'LT',1,'CRITICAL',NK,'${node}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.',etcdguide)
nodeguide='Projeção linear de 6h, persistente por 30m; confira crescimento real, retenção e capacidade. Exclui raw block. Preserve dados e confirme suporte da expansão.'
free=f'max by ({F}) (node_filesystem_avail_bytes{{{S}}}) / max by ({F}) (node_filesystem_size_bytes{{{S}}})'
add('node-space','filesystem below 10 percent available · 15m',low(free,'15m'),'LT',.1,'CRITICAL',NK,'${mountpoint} · ${device}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.',nodeguide)
add('node-inodes','filesystem below 10 percent free inodes · 15m',low(f'max by ({F}) (node_filesystem_files_free{{{S}}}) / (max by ({F}) (node_filesystem_files{{{S}}}) > 0)','15m'),'LT',.1,'CRITICAL',NK,'${mountpoint} · ${device}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.',nodeguide)
add('node-memory','host OS below 10 percent available RAM · 15m',low(f'max by ({N}) (node_memory_MemAvailable_bytes{{job="sre-node"}}) / max by ({N}) (node_memory_MemTotal_bytes{{job="sre-node"}})','15m'),'LT',.1,'DEVIATING',NK,'${node}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.','Confira /proc/meminfo, pressão de memória, OOM, processos e guests. Não use soma de requests como uso real. Colete evidências antes de ajustar recursos.')
missing=f'(max by ({N}) (kubernetes_state_node_age) * 0 + 1) unless on ({N}) (max by ({N}) (up{{job="sre-node"}} == 1))'
add('node-telemetry','missing node OS telemetry · 5m',high(f'({missing}) or on ({N}) (max by ({N}) (kubernetes_state_node_age) * 0)','5m'),'GT',0,'DEVIATING',NK,'${node}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.','Confira DaemonSet, taints, tolerations, logs do vmagent, Secret de ingestão e conectividade do receiver. Compare os targets com o inventário de nós.')
pvc_guard=f'max by ({V}) (kubernetes_kubelet_volume_stats_inodes) > 0';pvc_free=f'(max by ({V}) (kubernetes_kubelet_volume_stats_available_bytes) / max by ({V}) (kubernetes_kubelet_volume_stats_capacity_bytes)) and on ({V}) ({pvc_guard})'
add('pvc-space','PVC filesystem below 10 percent available · 15m',low(pvc_free,'15m'),'LT',.1,'CRITICAL',VK,'${persistentvolumeclaim}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.',nodeguide)
ratio=f'max by ({K}) (container_memory_working_set{{pod_name!~"virt-launcher-.*"}}) / (max by ({K}) (kubernetes_state_container_memory_limit) > 0)'
add('container-memory','container working set above 95 percent limit · 5m',high(ratio,'5m'),'GT',.95,'DEVIATING',PK,'${container}','Risco de OOM em containers comuns; exclui virt-launcher, que tem monitor de RAM disponível no guest. Working set não é heap.','Colete Last State, probes, logs --previous, RSS/cache/heap e eventos. Compare o mesmo container e instante. Working set não é heap. Diagnostique antes de ajustar recursos.')
guest='max by (k8s_cluster_name,namespace,name,node) (kubevirt_vmi_memory_usable_bytes) / max by (k8s_cluster_name,namespace,name,node) (kubevirt_vmi_memory_available_bytes)'
add('vm-guest-memory','VM guest OS below 10 percent available RAM · 15m',f'label_replace({low(guest,"15m")}, "cluster_name", "$1", "k8s_cluster_name", "(.*)")','LT',.1,'DEVIATING',NK,'${namespace} · ${name}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.','Confira RAM disponível, balloon, QEMU Guest Agent e pressão no SO guest. Compare requests/limits do domínio separadamente do consumo do guest. O residente QEMU não equivale a RAM usada dentro da VM.')
# One certificate can cover multiple SANs and is repeated by every Traefik instance.
cert='min by (cluster_name,sans,serial) ({__name__=~"traefik_tls_certs_not_after|_traefik_tls_certs_not_after"})'
for days,sev in [(30,'DEVIATING'),(7,'CRITICAL')]:add('tls-'+str(days),f'Traefik certificate expires within {days} days',f'(({cert} - time()) / 86400) * on (cluster_name) group_left(namespace,daemonset) (max by (cluster_name,namespace,daemonset) (kubernetes_state_daemonset_desired{{daemonset=~".*traefik.*"}}) * 0 + 1)','LT',days,sev,CK,'${sans} · ${serial}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.','Identifique SAN/serial no dashboard. Localize Secret e emissor; confira renovação. Valide o certificado servido pelo endpoint.')
# Safe corrected replacements for the two built-in PVC forecasts that include raw block.
for hours,sev in [(12,'CRITICAL'),(96,'DEVIATING')]:
 expr=f'predict_linear((max by ({V}) (kubernetes_kubelet_volume_stats_available_bytes))[6h:5m], {hours*3600}) and on ({V}) ({pvc_guard})'
 add('pvc-trend-'+str(hours),f'PVC filesystem projected full within {hours}h',low(expr,'30m'),'LT',0,sev,VK,'${persistentvolumeclaim}','Condição persistente calculada na consulta. Limiar de diagnóstico ajustável ao ambiente. Investigue coleta ausente separadamente.',nodeguide)
collector_labels='cluster_name,node,collector_kind'
node_collectors='job="sre-collector",node!=""'
add('collector-backlog','metric collection backlog persists · 10m',high(f'max by ({collector_labels}) (vmagent_remotewrite_pending_data_bytes{{{node_collectors}}})','10m'),'GT',0,'DEVIATING',NK,'${node} · ${collector_kind}','Fila dos coletores de nó/etcd positiva em todas as amostras por dez minutos. Pequenos picos não disparam.','Verifique DNS, TLS, status HTTP do receiver e espaço da fila. A série também deixa de chegar durante indisponibilidade total; use cobertura e sinais do próprio SUSE em conjunto.')
add('collector-dropped','metric collector discarded data · 15m',f'max by ({collector_labels}) (increase(vmagent_remotewrite_samples_dropped_total{{{node_collectors}}}[15m])) + max by ({collector_labels}) (increase(vm_persistentqueue_bytes_dropped_total{{{node_collectors}}}[15m]))','GT',0,'CRITICAL',NK,'${node} · ${collector_kind}','Qualquer descarte observado de amostras ou bytes da fila merece investigação. O valor é apenas detector combinado, não uma unidade de volume.','Verifique receiver, fila, retenção do buffer e reinícios. Os dados descartados não são recuperados automaticamente.')
previous=f'max by ({N}) (last_over_time(up{{job="sre-etcd"}}[24h])) * 0 + 1'
healthy=f'max by ({N}) (up{{job="sre-etcd"}} == 1)'
add('etcd-telemetry-missing','etcd telemetry disappeared · 5m',high(f'(({previous}) unless on ({N}) ({healthy})) or on ({N}) (({previous}) * 0)','5m'),'GT',0,'CRITICAL',NK,'${node}','Membro coletado nas últimas 24h sem target saudável por cinco minutos. Não descobre membros que nunca foram coletados.','Confira o DaemonSet etcd, labels dos nós, DNS e envio. Compare com a topologia esperada; membros removidos exigem interpretação do histórico.')
traefik_ds='max by (cluster_name,namespace,daemonset) (kubernetes_state_daemonset_desired{daemonset=~".*traefik.*"}) * 0 + 1'
add('ingress-inventory','Ingress inventory collection failing · 3m',f'({low("min by (cluster_name) (sre_ingress_inventory_success)","3m")}) * on (cluster_name) group_left(namespace,daemonset) ({traefik_ds})','LT',1,'DEVIATING',CK,'${daemonset}','O mapeamento de namespace/Service/porta nomeada não está sendo atualizado. O endpoint usa somente list de Ingress.','Confira logs do container ingress-inventory, RBAC list ingresses, CA e acesso à API Kubernetes. Em ambientes com mais de um Traefik por cluster adapte o vínculo de topologia.')
for r in rules:
 if r['slug'] in ['node-space','node-inodes']:
  r['description']='Menos de 10% disponível em todas as amostras dos últimos 15 minutos. Exclui imagens loop, filesystems temporários e montagens de pods. Não equivale ao espaço livre dentro de uma VM.'
  r['remediation']='Confira o dispositivo e a montagem com df -h e df -i no nó afetado. Identifique crescimento de logs, imagens e arquivos pequenos. Verifique retenção e capacidade antes de remover dados. Para Harvester, diferencie a partição persistente da partição de dados Longhorn.'
 args={'metric':{'query':r['query'],'unit':'none','aliasTemplate':r['alias']},'comparator':r['comparator'],'threshold':r['threshold'],'failureState':r['severity'],'urnTemplate':r['urnTemplate'],'titleTemplate':r['titleTemplate']}
 obj={'_type':'Monitor','name':r['name'],'identifier':'urn:custom:monitor:sre-dashboards:'+r['slug'],'description':r['description'],'arguments':args,'intervalSeconds':60,'status':'ENABLED' if r['enabled'] else 'DISABLED','remediationHint':r['remediation'],'tags':['sre-dashboards','platform'],'function':'FUNCTION_REF'}
 text=yaml.safe_dump({'nodes':[obj]},allow_unicode=True,sort_keys=False).replace('function: FUNCTION_REF','function: {{ get "urn:stackpack:common:monitor-function:threshold" }}')
 (P/'charts/suse-observability-monitors/monitors'/(r['slug']+'.sty')).write_text(text)
(O/'catalog.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2))
(P/'charts/suse-observability-monitors/files/catalog.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2))
print('monitors',len(rules))
