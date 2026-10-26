#!/usr/bin/env python3
"""Build self-contained user charts from tested internal components; no build on install."""
from pathlib import Path
import copy,json,shutil,yaml
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'components'
CONTENT=SRC/'suse-observability-content'
CAT=json.loads((CONTENT/'files/catalog.json').read_text())
PACKS={
 'virtualization':{'dashboards':['harvester'],'tag':'dashboard-harvester','platform':True,'virt':True},
 'traefik':{'dashboards':['traefik'],'tag':'dashboard-traefik','platform':True},
 'applications':{'dashboards':['applications'],'tag':'dashboard-applications'},
 'kubernetes':{'dashboards':['platform','resources'],'tag':'dashboard-platform','platform':True},
}
def inline_refs(value, root):
 if isinstance(value,list):return [inline_refs(v,root) for v in value]
 if isinstance(value,dict):
  if '$ref' in value and value['$ref'].startswith('#/'):
   target=root
   for part in value['$ref'][2:].split('/'):target=target[part]
   return inline_refs(target,root)
  return {k:inline_refs(v,root) for k,v in value.items()}
 return value
def dump(p,v):p.write_text(yaml.safe_dump(v,sort_keys=False,allow_unicode=True))
def wrap(text,component):
 condition='ne .Values.mode "telemetry"' if component=='content' else 'ne .Values.mode "content"'
 prefix='{{- if '+condition+' }}\n{{- $root := . }}\n{{- $v := deepCopy .Values.'+component+' }}\n'
 if component=='content':
  prefix+='{{- if hasKey .Values "applicationMetrics" }}{{- $_ := set $v "applicationMetrics" .Values.applicationMetrics }}{{- end }}\n{{- $_ := set $v "observability" .Values.observability }}\n{{- $_ := set $v "auth" .Values.auth }}\n{{- $_ := set $v "lifecycle" .Values.lifecycle }}\n{{- $_ := set $v "slo" .Values.slo }}\n'
 else:
  prefix+='{{- $_ := set $v "clusterName" (required "clusterName: use the exact SUSE integration name" .Values.clusterName) }}\n'
  if component=='telemetry':
   prefix+='{{- $_ := set $v.remoteWrite "url" (default (printf "%s/receiver/prometheus/api/v1/write" (trimSuffix "/" .Values.observability.url)) .Values.observability.remoteWriteUrl) }}\n{{- $_ := set $v.remoteWrite "existingSecret" .Values.ingestion.existingSecret }}\n{{- $_ := set $v.remoteWrite "secretKey" .Values.ingestion.secretKey }}\n'
  else:
   prefix+='{{- $_ := set $v.otlp "endpoint" (required "observability.otlpEndpoint is required for VM telemetry" .Values.observability.otlpEndpoint) }}\n{{- $_ := set $v.otlp "existingSecret" .Values.ingestion.existingSecret }}\n{{- $_ := set $v.otlp "secretKey" .Values.ingestion.secretKey }}\n'
 prefix+='{{- with (dict "Values" $v "Release" .Release "Chart" .Chart "Files" .Files "Capabilities" .Capabilities "Template" .Template) }}\n'
 return prefix+'{{- $ := . }}\n'+text+'\n{{- end }}\n{{- end }}\n'
for name,cfg in PACKS.items():
 dest=ROOT/'charts'/('suse-observability-'+name)
 dest.mkdir(parents=True,exist_ok=True)
 for sub in ('templates','files','dashboards','monitors'):
  if (dest/sub).exists():shutil.rmtree(dest/sub)
  (dest/sub).mkdir()
 c=yaml.safe_load((CONTENT/'values.yaml').read_text())
 selected=[x for x in CAT if (cfg['tag'] in x['tags'] or (name=='kubernetes' and 'dashboard-resources' in x['tags'])) and not (name=='virtualization' and x['slug']=='node-memory')]
 c['dashboards']['include']=cfg['dashboards'];c['monitors']['include']=[x['slug'] for x in selected]
 values={'mode':'all','clusterName':'','observability':{'url':'','remoteWriteUrl':'','otlpEndpoint':''},'ingestion':{'existingSecret':'suse-observability-agent-secrets','secretKey':'STS_API_KEY'},'auth':{'dashboards':{'existingSecret':'suse-observability-publisher-token','serviceTokenKey':'serviceToken'},'monitors':{'existingSecret':'suse-observability-publisher-token','serviceTokenKey':'serviceToken'}},'lifecycle':c.pop('lifecycle'),'slo':{'availabilityTarget':99.9},'content':c}
 c.pop('observability');c.pop('auth')
 sources=[('content',CONTENT)]
 if cfg.get('platform'):
  source=SRC/'sre-platform-telemetry';v=yaml.safe_load((source/'values.yaml').read_text());v.pop('clusterName')
  v['remoteWrite'].pop('url');v['remoteWrite'].pop('existingSecret');v['remoteWrite'].pop('secretKey')
  v['traefik']['enabled']=name=='traefik';v['nodeExporter']['enabled']=name!='traefik';v['podInventory']['enabled']=name!='traefik'
  v['tests']['enabled']=False
  values['telemetry']=v;sources.append(('telemetry',source))
 if cfg.get('virt'):
  source=SRC/'sre-kubevirt-telemetry';v=yaml.safe_load((source/'values.yaml').read_text());v.pop('clusterName');v['otlp'].pop('endpoint');v['otlp'].pop('existingSecret');v['otlp'].pop('secretKey');v['longhorn']['enabled']=True;v['kubevirt']['ca']['autoSync']=True;values['virtualization']=v;sources.append(('virtualization',source))
 if name=='applications':
  values['mode']='content'
  values['applicationMetrics']={'requestCounter':'http_server_requests_total','durationHistogram':'http_server_request_duration_seconds','clusterLabel':'cluster_name','serviceLabel':'service_name','statusLabel':'http_response_status_code','routeLabel':'http_route'}
 dump(dest/'Chart.yaml',{'apiVersion':'v2','name':dest.name,'description':f'Independent {name} dashboards, monitors and applicable collectors for SUSE Observability','type':'application','version':'1.0.0','appVersion':'2.10.2','home':'https://github.com/kaioneuhauss/suse-observability-dashboards'})
 dump(dest/'values.yaml',values)
 for component,source in sources:
  for file in (source/'files').glob('*'):
   if file.is_file() and file.name not in ('catalog.json','panel-monitor-coverage.json','legacy-identifiers.json'):shutil.copy2(file,dest/'files'/file.name)
  for file in (source/'templates').glob('*'):
   if file.name=='NOTES.txt':continue
   out=dest/'templates'/(component+'-'+file.name if not file.name.startswith('_') else '_'+component+file.name)
   out.write_text(file.read_text() if file.suffix=='.tpl' else wrap(file.read_text(),component))
 for dashboard in cfg['dashboards']:shutil.copy2(CONTENT/'dashboards'/f'{dashboard}.json',dest/'dashboards')
 for rule in selected:shutil.copy2(CONTENT/'monitors'/(rule['slug']+'.sty'),dest/'monitors')
 (dest/'files/catalog.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
 legacy=json.loads((CONTENT/'files/legacy-identifiers.json').read_text());(dest/'files/legacy-identifiers.json').write_text(json.dumps({k:v for k,v in legacy.items() if k in c['monitors']['include']},indent=2)+'\n')
 schema={'$schema':'http://json-schema.org/draft-07/schema#','type':'object','additionalProperties':False,'required':list(values),'properties':{k:{'type':'object'} for k in values if isinstance(values[k],dict)}}
 schema['properties'].update({'mode':{'enum':['content'] if name=='applications' else ['all','content','telemetry']},'clusterName':{'type':'string'},'observability':{'type':'object','required':['url'],'properties':{'url':{'type':'string','pattern':'^https://[^ /]+(/.*)?$'},'remoteWriteUrl':{'type':'string','pattern':'^(https://[^ ]+)?$'},'otlpEndpoint':{'type':'string'}}},'slo':{'type':'object','properties':{'availabilityTarget':{'type':'number','minimum':1,'exclusiveMaximum':100}},'required':['availabilityTarget']}})
 # Reuse component constraints after removing the fields supplied at the pack boundary.
 for component,source in sources:
  raw=json.loads((source/'values.schema.json').read_text());sub=inline_refs(raw,raw);sub.pop('$schema',None);sub.pop('definitions',None)
  removed=['observability','auth','lifecycle'] if component=='content' else ['clusterName']
  for key in removed:
   sub['properties'].pop(key,None)
   if key in sub.get('required',[]):sub['required'].remove(key)
  if component!='content':
   block='remoteWrite' if component=='telemetry' else 'otlp'
   for key in (['url','existingSecret','secretKey'] if component=='telemetry' else ['endpoint','existingSecret','secretKey']):
    sub['properties'][block]['properties'].pop(key,None)
    if key in sub['properties'][block].get('required',[]):sub['properties'][block]['required'].remove(key)
  else:
   sub['properties']['dashboards']['properties']['include']={'const':cfg['dashboards']}
   sub['properties']['monitors']['properties']['include']={'const':c['monitors']['include']}
  schema['properties'][component]=sub
 if name=='applications':schema['properties']['applicationMetrics']={'type':'object','additionalProperties':False,'required':list(values['applicationMetrics']),'properties':{k:{'type':'string','pattern':'^[a-zA-Z_][a-zA-Z0-9_:]*$'} for k in values['applicationMetrics']}}
 for k in ('auth','lifecycle'):
  schema['properties'][k]=json.loads((CONTENT/'values.schema.json').read_text())['properties'][k]
 if name=='traefik':
  for feature in ('nodeExporter','podInventory','etcd'):schema['properties']['telemetry']['properties'][feature]['properties']['enabled']={'const':False}
 elif cfg.get('platform'):schema['properties']['telemetry']['properties']['traefik']['properties']['enabled']={'const':False}
 (dest/'values.schema.json').write_text(json.dumps(schema,indent=2)+'\n')
 (dest/'templates/NOTES.txt').write_text('Module: '+name+' ({{ .Values.mode }})\nCheck collector readiness, publisher Job logs and fresh metrics in SUSE Observability.\nSee docs/'+name+'.md for prerequisites, acceptance and removal.\n')
 ex={'clusterName':'my-cluster','observability':{'url':'https://observability.example.com'}}
 if cfg.get('virt'):ex['observability']['otlpEndpoint']='otlp-observability.example.com:443'
 if name=='applications':ex.pop('clusterName')
 ep=ROOT/'examples'/(name+'.yaml');ep.parent.mkdir(exist_ok=True);dump(ep,ex)
 print(dest.name,len(cfg['dashboards']),'dashboards',len(selected),'monitors')
