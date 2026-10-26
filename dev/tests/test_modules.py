"""Module isolation, selection, SLO parameters and source-vs-central installation."""
import json,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
class ModuleTests(unittest.TestCase):
 def render(self,module,*args,ok=True):
  p=subprocess.run(['helm','template','test',str(ROOT/'charts'/('suse-observability-'+module)),'-f',str(ROOT/'examples'/(module+'.yaml')),*args],text=True,capture_output=True)
  if not ok:self.assertNotEqual(p.returncode,0);return
  self.assertEqual(p.returncode,0,p.stderr);return [o for o in yaml.safe_load_all(p.stdout) if o]
 def test_selection_and_monitor_ownership(self):
  names=set();slugs=set()
  for m,expected in [('virtualization',4),('traefik',1),('applications',1),('kubernetes',2),('imports',1)]:
   objs=self.render(m)
   cm=next(o for o in objs if o['kind']=='ConfigMap' and 'dashboards.json' in o.get('data',{}))
   dashboards=json.loads(cm['data']['dashboards.json'])['dashboards'];self.assertEqual(len(dashboards),expected)
   for d in dashboards:self.assertNotIn(d['name'],names);names.add(d['name'])
   cm=next((o for o in objs if o['kind']=='ConfigMap' and 'catalog.json' in o.get('data',{})),None)
   for r in json.loads(cm['data']['catalog.json']) if cm else []:self.assertNotIn(r['slug'],slugs);slugs.add(r['slug'])
  self.assertEqual(len(slugs),34)
 def test_traefik_never_installs_host_or_etcd(self):
  objs=self.render('traefik');self.assertFalse(any(o['kind']=='DaemonSet' for o in objs))
  self.render('traefik','--set','telemetry.etcd.enabled=true',ok=False)
  self.render('traefik','--set','telemetry.nodeExporter.enabled=true',ok=False)
 def test_content_only_needs_no_cluster_or_collector_secret(self):
  for m in ['virtualization','traefik','kubernetes','imports']:
   objs=self.render(m,'--set','mode=content','--set','clusterName=','--set','observability.otlpEndpoint=')
   self.assertFalse(any(o['kind'] in ('Deployment','DaemonSet','Role','ClusterRole') for o in objs))
 def test_telemetry_never_publishes(self):
  for m in ['virtualization','traefik','kubernetes','imports']:
   objs=self.render(m,'--set','mode=telemetry')
   self.assertFalse(any(o['kind']=='Job' for o in objs))
   self.assertFalse(any('dashboards.json' in o.get('data',{}) for o in objs))
 def test_slo_target_is_applied_and_invalid_target_rejected(self):
  objs=self.render('applications','--set','slo.availabilityTarget=99')
  cm=next(o for o in objs if 'dashboards.json' in o.get('data',{}));self.assertIn(' / 0.01000000',cm['data']['dashboards.json']);self.assertNotIn('__ERROR_BUDGET__',cm['data']['dashboards.json'])
  self.render('applications','--set','slo.availabilityTarget=100',ok=False)
 def test_no_cross_module_content_or_unguarded_delete(self):
  self.render('traefik','--set','content.dashboards.include[0]=harvester',ok=False)
  self.render('applications','--set','lifecycle.action=delete',ok=False)
 def test_virtualization_discovers_longhorn_without_writes(self):
  objs=self.render('virtualization','--set','mode=telemetry')
  role=next(o for o in objs if o['kind']=='Role' and o['metadata']['name'].endswith('-longhorn'))
  self.assertEqual(role['metadata']['namespace'],'longhorn-system')
  for rule in role['rules']:self.assertLessEqual(set(rule['verbs']),{'get','list','watch'})
 def test_application_aliases_reach_dashboards_and_monitors(self):
  objs=self.render('applications','--set','applicationMetrics.requestCounter=http_server_request_duration_seconds_count','--set','applicationMetrics.clusterLabel=k8s_cluster_name')
  for obj in objs:
   if obj['kind']=='ConfigMap':
    for key,value in obj.get('data',{}).items():
     if key=='dashboards.json' or key=='catalog.json' or key.endswith('.sty'):
      self.assertNotIn('http_server_requests_total',value)
      self.assertIn('k8s_cluster_name',value)
 def test_ca_sync_reads_only_named_public_configmap(self):
  objs=self.render('virtualization','--set','mode=telemetry')
  role=next(o for o in objs if o['kind']=='Role' and o['metadata']['namespace']=='harvester-system')
  ca=next(r for r in role['rules'] if 'configmaps' in r['resources'])
  self.assertEqual(ca['resourceNames'],['kubevirt-ca']);self.assertEqual(ca['verbs'],['get'])
  deployment=next(o for o in objs if o['kind']=='Deployment' and o['metadata']['name']=='test')
  pod=deployment['spec']['template']['spec'];self.assertIn('prepare-ca',[c['name'] for c in pod['initContainers']]);self.assertIn('sync-ca',[c['name'] for c in pod['containers']])
  self.assertIn('emptyDir',next(v for v in pod['volumes'] if v['name']=='ca'))
 def test_longhorn_network_policy_is_explicit_and_scoped(self):
  self.render('virtualization','--set','virtualization.longhorn.allowMetricsNetworkPolicy=true',ok=False)
  objs=self.render('virtualization','--set','virtualization.longhorn.allowMetricsNetworkPolicy=true','--set','virtualization.longhorn.existingIsolationConfirmed=true')
  np=next(o for o in objs if o['kind']=='NetworkPolicy')
  self.assertEqual(np['spec']['podSelector'],{'matchLabels':{'app':'longhorn-manager'}})
  self.assertEqual(np['spec']['ingress'][0]['ports'],[{'protocol':'TCP','port':9500}])
  self.assertEqual(np['spec']['ingress'][0]['from'][0]['podSelector']['matchLabels']['app.kubernetes.io/instance'],'test')
  self.assertEqual(np['spec']['ingress'][0]['from'][0]['namespaceSelector']['matchLabels']['kubernetes.io/metadata.name'],'default')
 def test_imports_rbac_and_container_credentials_are_minimal(self):
  objs=self.render('imports','--set','mode=telemetry')
  role=next(o for o in objs if o['kind']=='ClusterRole')
  self.assertEqual(role['rules'],[{'apiGroups':['migration.harvesterhci.io'],'resources':['virtualmachineimports'],'verbs':['list']}])
  pod=next(o for o in objs if o['kind']=='Deployment')['spec']['template']['spec']
  self.assertFalse(pod['automountServiceAccountToken'])
  exporter,writer=pod['containers']
  self.assertNotIn('auth',{v['name'] for v in exporter['volumeMounts']})
  self.assertNotIn('api-access',{v['name'] for v in writer['volumeMounts']})
  self.assertFalse(any(o['kind'] in ('Service','NetworkPolicy','DaemonSet') for o in objs))
if __name__=='__main__':unittest.main()
