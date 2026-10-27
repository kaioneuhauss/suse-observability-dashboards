"""Regression: Helm YAML 1.1 must never turn a dashboard y coordinate into true."""
import importlib.util,json,pathlib,subprocess,unittest,yaml,copy,shutil,tempfile,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pub',ROOT/'components/suse-observability-content/files/publisher.py');pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
class LayoutTests(unittest.TestCase):
 def test_native_grid_does_not_need_compaction_or_threshold_sort(self):
  for path in (ROOT/'components/suse-observability-content/dashboards').glob('*.json'):
   s=json.loads(path.read_text())['dashboard']['spec'];rows={}
   for item in s['layouts'][0]['spec']['items']:rows.setdefault(item['y'],[]).append(item)
   y=0
   for start,row in sorted(rows.items()):
    self.assertEqual(start,y,path.name);x=0
    for item in sorted(row,key=lambda i:i['x']):
     self.assertEqual(item['x'],x,path.name);x+=item['width']
     self.assertEqual(item['height'],row[0]['height'])
    self.assertEqual(x,24,path.name);y+=row[0]['height']
   for p in s['panels'].values():
    steps=p['spec']['plugin']['spec'].get('thresholds',{}).get('steps',[])
    self.assertEqual(steps,sorted(steps,key=lambda step:step['value'],reverse=True))
 def test_enhancement_preserves_layout_on_repeat(self):
  with tempfile.TemporaryDirectory() as directory:
   temporary=pathlib.Path(directory)/'dev'
   component=temporary/'components/suse-observability-content'
   shutil.copytree(ROOT/'components/suse-observability-content/dashboards',component/'dashboards')
   (component/'files').mkdir()
   shutil.copy2(ROOT/'components/suse-observability-content/files/panel-monitor-coverage.json',component/'files')
   (temporary/'scripts').mkdir()
   shutil.copy2(ROOT/'scripts/enhance-dashboards.py',temporary/'scripts')
   shutil.copy2(ROOT/'scripts/build-virtualization-dashboards.py',temporary/'scripts')
   shutil.copy2(ROOT/'scripts/curate-dashboards.py',temporary/'scripts')
   (temporary.parent/'docs').mkdir()
   def snapshot():return {str(p.relative_to(temporary)):p.read_bytes() for p in component.rglob('*.json')}
   expected=snapshot()
   for _ in range(2):
    subprocess.run([sys.executable,str(temporary/'scripts/enhance-dashboards.py')],check=True)
    subprocess.run([sys.executable,str(temporary/'scripts/build-virtualization-dashboards.py')],check=True)
    subprocess.run([sys.executable,str(temporary/'scripts/curate-dashboards.py')],check=True)
    self.assertEqual(expected,snapshot())
 def test_rendered_payload_preserves_layout(self):
  raw=subprocess.check_output(['helm','template','test',str(ROOT/'components/suse-observability-content'),'-f',str(ROOT/'components/suse-observability-content/config/values.yaml')],text=True)
  cm=next(d for d in yaml.safe_load_all(raw) if d and d['kind']=='ConfigMap' and 'dashboards.json' in d['data'])
  actual=json.loads(cm['data']['dashboards.json'])['dashboards']
  desired={json.loads(p.read_text())['name']:json.loads(p.read_text().replace('__ERROR_BUDGET__','0.00100000')) for p in (ROOT/'components/suse-observability-content/dashboards').glob('*.json')}
  self.assertEqual(len(actual),5)
  for d in actual:
   pub.validate_dashboard(d);self.assertEqual(d,desired[d['name']])
 def test_union_and_coordinate_regression(self):
  d=json.loads((ROOT/'components/suse-observability-content/dashboards/traefik.json').read_text());canonical=pub.normalized_dashboard(d)
  self.assertEqual(canonical,pub.normalized_dashboard(canonical))
  changed=copy.deepcopy(d);changed['dashboard']['spec']['layouts'][0]['spec']['items'][1]['y']=0
  self.assertNotEqual(pub.normalized_dashboard(d),pub.normalized_dashboard(changed))
  with self.assertRaises(pub.PublishError):pub.validate_dashboard(changed)
 def test_selected_period_keeps_nonoverlapping_steps(self):
  for p in (ROOT/'components/suse-observability-content/dashboards').glob('*.json'):
   for panel in json.loads(p.read_text())['dashboard']['spec']['panels'].values():
    for q in panel['spec'].get('queries',[]):
     spec=q['spec']['plugin']['spec'];expr=spec['query']
     if 'range_sum(' in expr:
      self.assertEqual(spec.get('minStep'),'1m')
      self.assertIn('[${__interval}]',expr)
      self.assertNotIn('[1i]',expr)
      self.assertNotIn('[1m]',expr)
      self.assertNotIn('[${__interval}] @ end()',expr)
      self.assertNotIn('${__range}',expr)
      self.assertIn('@ start()',expr)
 def test_legend_avoids_misaligned_summary_values(self):
  # SUSE 2.10.2 sorts Recharts legend labels before assigning point-array indexes.
  # The Last column can therefore be attributed to the wrong series.
  for path in (ROOT/'components/suse-observability-content/dashboards').glob('*.json'):
   for panel in json.loads(path.read_text())['dashboard']['spec']['panels'].values():
    plugin=panel['spec']['plugin']
    if plugin['kind']=='TimeSeriesChart':
     self.assertFalse(plugin['spec'].get('legend',{}).get('values',[]))
 def test_discrete_counts_are_displayed_as_integers(self):
  examples={'harvester':['runningCount'],'virtualization-capacity':['allocatedCpu','coverage'],
   'virtualization-storage':['unhealthy','neverBackup','staleBackup','volumeHealth','attachment','backupState'],
   'imports':['registered','succeeded','failed','active','disks'],
   'platform':['nonRunning','missingCopies','restartCount'],
   'resources':['cpuOver80Count','memOver80Count','cpuRequestMissingList','memRequestMissingList']}
  for slug,keys in examples.items():
   panels=json.loads((ROOT/'components/suse-observability-content/dashboards'/(slug+'.json')).read_text())['dashboard']['spec']['panels']
   for key in keys:
    p=panels[key]['spec']['plugin']['spec']
    self.assertEqual(p.get('format',p.get('yAxis',{}).get('format',{}))['decimalPlaces'],0,(slug,key))
 def test_running_vm_count_excludes_other_phases(self):
  d=json.loads((ROOT/'components/suse-observability-content/dashboards/harvester.json').read_text())
  q=d['dashboard']['spec']['panels']['runningCount']['spec']['queries'][0]['spec']['plugin']['spec']['query']
  self.assertIn('phase="running"',q)
 def test_every_panel_is_laid_out_once_without_overlap(self):
  for path in (ROOT/'components/suse-observability-content/dashboards').glob('*.json'):
   spec=json.loads(path.read_text())['dashboard']['spec'];items=spec['layouts'][0]['spec']['items']
   self.assertEqual(len(items),len(spec['panels']))
   for i,a in enumerate(items):
    self.assertLessEqual(a['x']+a['width'],24)
    for b in items[i+1:]:
     overlaps=a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and a['y']<b['y']+b['height'] and b['y']<a['y']+a['height']
     self.assertFalse(overlaps,(path.name,a['content'],b['content']))
if __name__=='__main__':unittest.main()

