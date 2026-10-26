#!/usr/bin/env python3
"""Curated SRE panels using the native, exported SUSE 2.10.2 schema."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'components/suse-observability-content'
def load(n):return json.loads((ROOT/'dashboards'/f'{n}.json').read_text())
def save(n,d): (ROOT/'dashboards'/f'{n}.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def add(d,key,title,description,queries,unit='decimal',stat=False):
 s=d['dashboard']['spec'];kind='StatChart' if stat else 'TimeSeriesChart'
 model=next((p for p in s['panels'].values() if p['spec']['plugin']['kind']==kind), load('applications')['dashboard']['spec']['panels']['rps'])
 p=copy.deepcopy(model);p['spec']['display']={'name':title,'description':description+'\n\nWhen to investigate / alert coverage: Investigate deviations with the associated request, resource or collection signals; this context panel does not independently page.'}
 p['spec'].pop('links',None)
 plug=p['spec']['plugin']['spec']
 if 'yAxis' in plug:plug['yAxis'].pop('label',None)
 if stat:plug['format']={'decimalPlaces':2,'unit':unit};plug['thresholds']={'defaultColor':'#1976B9','steps':[]}
 else:plug['yAxis']['show']=True;plug['yAxis']['format']={'decimalPlaces':2,'unit':unit};plug['thresholds']={'mode':'absolute','steps':[]}
 p['spec']['queries']=[{'kind':'TimeSeriesQuery','spec':{'plugin':{'kind':'PrometheusTimeSeriesQuery','spec':{'query':q,'alias':a}}}} for a,q in queries]
 s['panels'][key]=p
 items=s['layouts'][0]['spec']['items']
 if not any(i['content']['$ref']=='#/spec/panels/'+key for i in items):
  y=max(i['y']+i['height'] for i in items)
  items.append({'x':0,'y':y,'width':24,'height':3,'content':{'$ref':'#/spec/panels/'+key}})
# Explicitly request-based availability: zero traffic remains undefined, never 100%.
a=load('applications');sel='cluster_name=~"${app_cluster}",service_name=~"${instrumented_service}",http_route!~"(?i).*(health|ready|live|metrics).*"'
def app_ratio(window):
 total=f'sum by (cluster_name,service_name) (rate(http_server_requests_total{{{sel}}}[{window}]))'
 bad=f'sum by (cluster_name,service_name) (rate(http_server_requests_total{{{sel},http_response_status_code=~"5.."}}[{window}]))'
 return f'(({bad} or on (cluster_name,service_name) (0 * {total})) / ({total} > 0))'
add(a,'availability5m','Request availability · rolling 5m · %','1 minus the fraction of completed HTTP requests with 5xx responses. Excludes health/metrics routes. This is not uptime; timeouts before instrumentation and no traffic are not measured. Missing input stays empty.', [('${cluster_name} · ${service_name}',f'100 * (1 - {app_ratio("5m")})')],'percent')
add(a,'burnRate','Availability error-budget burn · 5m and 1h','Error fraction divided by the configured error budget. 1x consumes budget at the allowed rate; 14.4x sustained in both windows is a common fast-burn investigation signal. The default target is 99.9%; set slo.availabilityTarget to your agreed objective. This chart alone does not prove a 30-day SLO or trigger paging.', [('${cluster_name} · ${service_name} · 5m',app_ratio('5m')+' / __ERROR_BUDGET__'),('${cluster_name} · ${service_name} · 1h',app_ratio('1h')+' / __ERROR_BUDGET__')])
add(a,'sampleAge','Request metric age · seconds','Age of the newest counter sample per service. Compare with the collection interval; an empty result means missing telemetry, not a healthy service. A counter can stay unchanged while timestamps remain fresh.', [('${cluster_name} · ${service_name}',f'time() - max by (cluster_name,service_name) (timestamp(http_server_requests_total{{{sel}}}))')],'seconds')
save('applications',a)
t=load('traefik');p=t['dashboard']['spec']['panels']['p95'];q=p['spec']['queries'][0]['spec']['plugin']['spec']['query'].replace('histogram_quantile(0.95','histogram_quantile(0.99')
add(t,'p99','Tail latency · p99 · 5 min · ms','99% of observed completed requests finish within this latency estimate. Uses histogram buckets; compare p95, request volume and backend errors. Low traffic makes quantiles unstable.', [('p99',q)],'milliseconds',True)
add(t,'connections','Open connections by entrypoint','Concurrent connections are a saturation signal, not completed requests. This is cluster scope; namespace and application filters do not apply. Compare with latency, CPU and connection capacity.', [('${cluster_name} · ${entrypoint} · ${protocol}','sum by (cluster_name,entrypoint,protocol) (traefik_open_connections{cluster_name=~"${ingress_cluster}"})')])
add(t,'scrapeHealth','Traefik targets · 1 healthy / 0 failed','Every discovered Traefik endpoint should report 1. No series can mean no discovered targets, blocked telemetry, or incorrect cluster selection. A successful HTTP scrape alone does not validate request labels.', [('${cluster_name} · ${instance}','min by (cluster_name,instance) (up{job="traefik",cluster_name=~"${ingress_cluster}"})')])
save('traefik',t)
v=load('harvester');sel='k8s_cluster_name=~"${vm_cluster}",namespace=~"${vm_namespace}",name=~"${vm_name}"'
add(v,'runningCount','Observed VM instances','Count of VM instances currently exposing kubevirt_vmi_info; not a count of all defined or powered-off VMs. Compare with the Harvester inventory and collection-health panel.', [('VM instances',f'count(max by (k8s_cluster_name,namespace,name) (kubevirt_vmi_info{{{sel}}}))')],stat=True)
add(v,'scrapeHealth','Virtualization collection · 1 healthy / 0 failed','Per-target KubeVirt and Longhorn scrape status. TLS errors, API discovery permissions, NetworkPolicies or stale CA bundles can break collection even when the collector Pod is Running. Cluster scope; VM filters do not apply.', [('${k8s_cluster_name} · ${job} · ${instance}','min by (k8s_cluster_name,job,instance) (up{k8s_cluster_name=~"${vm_cluster}",job=~"(.*/)?(kubevirt-metrics|longhorn)"})')])
add(v,'vmSampleAge','VM metric age · seconds','Age of the latest VM identity sample. Compare with scrape interval and expected VMs. No data must not be interpreted as healthy or powered off without checking Harvester.', [('${k8s_cluster_name} · ${namespace} · ${name}',f'time() - max by (k8s_cluster_name,namespace,name) (timestamp(kubevirt_vmi_info{{{sel}}}))')],'seconds')
add(v,'storageHealth','Longhorn volume robustness','Cluster storage scope. Each state is a labeled series: 1 means the volume is in that state; 0 means it is not. Investigate replica placement, disk free space and rebuild activity. A single host cannot provide host-failure redundancy, even with healthy volumes.', [('${k8s_cluster_name} · ${volume} · ${state}','max by (k8s_cluster_name,volume,state) (longhorn_volume_robustness{k8s_cluster_name=~"${vm_cluster}"})')])
add(v,'storageUsage','Longhorn physical storage usage','Node storage usage and capacity in bytes. Cluster scope; VM/namespace filters do not apply. This differs from guest filesystem usage and logical volume capacity.', [('${node} · used','max by (k8s_cluster_name,node) (longhorn_node_storage_usage_bytes{k8s_cluster_name=~"${vm_cluster}"})'),('${node} · capacity','max by (k8s_cluster_name,node) (longhorn_node_storage_capacity_bytes{k8s_cluster_name=~"${vm_cluster}"})')],'bytes(IEC)')
save('harvester',v)
k=load('platform')
add(k,'etcdLeader','etcd leader visibility · 1 yes / 0 no','Each etcd member should observe a leader. A healthy single-node cluster has no redundancy. Empty results require checking whether etcd collection was enabled and the local endpoint exists.', [('${cluster_name} · ${node}','max by (cluster_name,node) (etcd_server_has_leader{cluster_name=~"${platform_cluster}",job="sre-etcd"})')])
save('platform',k)

coverage=json.loads((ROOT/"files/panel-monitor-coverage.json").read_text())
seen={(r["dashboard"],r["panel"]) for r in coverage}
for path in (ROOT/"dashboards").glob("*.json"):
 for key,panel in json.loads(path.read_text())["dashboard"]["spec"]["panels"].items():
  if (path.stem,key) not in seen and panel["spec"].get("queries"):
   coverage.append({"dashboard":path.stem,"panel":key,"title":panel["spec"]["display"]["name"],"monitors":[],"guidance":"Context panel; use related monitors and verify telemetry."})
(ROOT/"files/panel-monitor-coverage.json").write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+"\n")

for entry in coverage:
 entry["title"]=load(entry["dashboard"])["dashboard"]["spec"]["panels"][entry["panel"]]["spec"]["display"]["name"]
(ROOT/"files/panel-monitor-coverage.json").write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+"\n")

# Put incident triage first and avoid one full-width gauge per row.
def arrange(name, featured):
 d=load(name);s=d['dashboard']['spec'];old=s['layouts'][0]['spec']['items']
 used={'guide'};items=[{'x':0,'y':0,'width':24,'height':1,'content':{'$ref':'#/spec/panels/guide'}}];y=1
 for row in featured:
  x=0
  for key,width,height in row:
   if key not in s['panels']:raise ValueError((name,key))
   items.append({'x':x,'y':y,'width':width,'height':height,'content':{'$ref':'#/spec/panels/'+key}});x+=width;used.add(key)
  y+=max(t[2] for t in row)
 rest=[i['content']['$ref'].split('/')[-1] for i in old if i['content']['$ref'].split('/')[-1] not in used]
 for index,key in enumerate(rest):
  items.append({'x':12*(index%2),'y':y+3*(index//2),'width':12,'height':3,'content':{'$ref':'#/spec/panels/'+key}})
 s['layouts'][0]['spec']['items']=items;save(name,d)
arrange('harvester',[
 [('guestCpuGauge',8,2),('guestMemoryGauge',8,2),('guestDiskGauge',8,2)],
 [('runningCount',6,2),('hostCpuGauge',9,2),('hostMemoryGauge',9,2)],
 [('scrapeHealth',12,3),('vmSampleAge',12,3)],
 [('storageHealth',12,3),('storageUsage',12,3)]])
arrange('applications',[[('rps',8,2),('success',8,2),('p95_1h',8,2)],[('availability5m',12,3),('sampleAge',12,3)],[('burnRate',24,3)]])
arrange('traefik',[[('rps',8,2),('meanLatency',8,2),('p95',8,2)],[('p99',8,2),('client4xx',8,2),('error5xx',8,2)],[('scrapeHealth',12,3),('connections',12,3)]])
