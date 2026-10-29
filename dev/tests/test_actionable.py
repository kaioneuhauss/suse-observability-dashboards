"""Safeguards for actionable panels and opt-in kubelet access."""
import json,pathlib,subprocess,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[2]
CONTENT=ROOT/'dev/components/suse-observability-content/dashboards'
class ActionableTests(unittest.TestCase):
 def test_storage_details_preserve_consumer_identity_and_full_list(self):
  panels=json.loads((CONTENT/'virtualization-storage.json').read_text())['dashboard']['spec']['panels']
  for key in ['unhealthyDetails','neverBackupDetails','staleBackupDetails']:
   p=panels[key]['spec'];detail=json.loads(p['links'][0]['url'].split('metrics=',1)[1])[0][0][0]
   self.assertNotIn('topk(',detail)
   self.assertIn('@ end()',detail)
   for label in ['k8s_cluster_name','pvc_namespace','pvc','volume']:
    self.assertIn(label,detail)
   self.assertIn('pod_name',detail)
   self.assertIn('kubernetes_state_pod_volumes_persistentvolumeclaims_readonly',detail)
   self.assertIn('0 * (',detail) # A read/write mount reports 0, but is still a reference.
   self.assertIn('group_left(volume,state)',detail)
   self.assertIn('count by (k8s_cluster_name,pvc_namespace,pvc)',detail)
   self.assertIn('unless on (k8s_cluster_name,volume)',detail)
   self.assertIn('${sre_display}',p['queries'][0]['spec']['plugin']['spec']['alias'])
   self.assertNotIn('sre_display',detail)
  self.assertIn('degraded|faulted',panels['unhealthyDetails']['spec']['queries'][0]['spec']['plugin']['spec']['query'])
 def test_detail_links_roundtrip_and_keep_all_offenders(self):
  panels=json.loads((CONTENT/'resources.json').read_text())['dashboard']['spec']['panels']
  for key in ['memLimitReview','cpuLimitReview','cpuRequestMissingValues','cpuLimitMissingValues','memRequestMissingValues','memLimitMissingValues']:
   p=panels[key]['spec'];q=p['queries'][0]['spec']['plugin']['spec']['query']
   self.assertEqual(p['plugin']['kind'],'StatChart')
   self.assertIn('@ end()',q)
   self.assertNotIn('sort_by_label',q)
   raw=p['links'][0]['url'].split('metrics=',1)[1]
   self.assertNotIn('%',raw);self.assertNotIn('>',raw)
   state=json.loads(raw); detail=state[0][0][0]
   self.assertIn('${workload_cluster}',detail)
   self.assertNotIn('topk(',detail)
   self.assertIn('topk(5, ',q)
   self.assertIn('sre_pod',q)
   self.assertNotIn('sre_display',detail)
   if key.endswith('LimitReview'):
    self.assertIn('> 0.8',q);self.assertTrue(detail.startswith('round(100 * ('))
 def test_rankings_keep_full_identity_and_freeze_the_selected_end(self):
  panels=json.loads((CONTENT/'virtualization-contention.json').read_text())['dashboard']['spec']['panels']
  for key in ['cpuReady','cpuUsage','memoryUse']:
   p=panels[key]['spec'];q=p['queries'][0]['spec']['plugin']['spec']
   self.assertIn('topk(5, last_over_time(',q['query'])
   self.assertIn('@ end()',q['query'])
   self.assertIn('phase="running"',q['query'])
   for label in ['name','namespace','k8s_cluster_name']:self.assertIn(label,q['query'])
   self.assertEqual(q['alias'],'${sre_display}')
   detail=json.loads(p['links'][0]['url'].split('metrics=',1)[1])[0][0][0]
   self.assertNotIn('topk(',detail)
 def test_stat_cards_reserve_readable_space_and_bound_action_lists(self):
  for path in CONTENT.glob('*.json'):
   s=json.loads(path.read_text())['dashboard']['spec']
   for item in s['layouts'][0]['spec']['items']:
    p=s['panels'][item['content']['$ref'].split('/')[-1]]['spec']
    if p['plugin']['kind']=='StatChart':
     self.assertGreaterEqual(item['height'],2,(path.name,p['display']['name']))
     if item['width']==24 and p['queries'][0]['spec']['plugin']['spec']['alias']!='Pods':
      self.assertGreaterEqual(item['height'],3)
      self.assertIn('topk(5, ',p['queries'][0]['spec']['plugin']['spec']['query'])
 def test_import_selectors_use_normalized_pod_label(self):
  panels=json.loads((CONTENT/'imports.json').read_text())['dashboard']['spec']['panels']
  for key in ['controllerRx','controllerTx','controllerCPU','controllerMemory','imageRx','imageTx']:
   q=panels[key]['spec']['queries'][0]['spec']['plugin']['spec']
   self.assertIn('pod_name=~',q['query'])
   self.assertNotIn('pod=~',q['query'])
   self.assertIn('${pod_name}',q['alias'])
 def test_no_spacer_sections(self):
  for path in CONTENT.glob('*.json'):
   panels=json.loads(path.read_text())['dashboard']['spec']['panels']
   self.assertFalse(any(key.startswith('section_') for key in panels))
 def test_kubelet_access_is_opt_in_and_does_not_grant_proxy(self):
  chart=ROOT/'charts/suse-observability-imports'
  for enabled in (False,True):
   raw=subprocess.check_output(['helm','template','obs-imports',str(chart),'-f',str(ROOT/'examples/imports.yaml'),'--set','imports.performance.enabled='+str(enabled).lower()],text=True)
   docs=[d for d in yaml.safe_load_all(raw) if d]
   role=next(d for d in docs if d['kind']=='ClusterRole')
   resources={r for rule in role['rules'] for r in rule['resources']}
   self.assertEqual('nodes/metrics' in resources,enabled)
   self.assertFalse(resources & {'nodes/proxy','pods/exec','secrets'})
   deploy=next(d for d in docs if d['kind']=='Deployment')
   vmagent=next(c for c in deploy['spec']['template']['spec']['containers'] if c['name']=='vmagent')
   self.assertEqual(vmagent['resources']['limits']['memory'],'512Mi' if enabled else '128Mi')
   self.assertEqual(vmagent['resources']['requests']['memory'],'128Mi' if enabled else '32Mi')
   config=next(d for d in docs if d['kind']=='ConfigMap' and 'scrape.yaml' in d.get('data',{}))
   jobs=yaml.safe_load(config['data']['scrape.yaml'])['scrape_configs']
   performance=[j for j in jobs if j['job_name']=='sre-import-performance']
   self.assertEqual(len(performance),int(enabled))
   if enabled:
    self.assertFalse(performance[0]['tls_config']['insecure_skip_verify'])
    self.assertEqual(performance[0]['metrics_path'],'/metrics/cadvisor')
    self.assertTrue(performance[0]['stream_parse'])
if __name__=='__main__':unittest.main()
