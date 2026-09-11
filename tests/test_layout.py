"""Regression: Helm YAML 1.1 must never turn a dashboard y coordinate into true."""
import importlib.util,json,pathlib,subprocess,unittest,yaml,copy
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pub',ROOT/'charts/suse-observability-content/files/publisher.py');pub=importlib.util.module_from_spec(spec);spec.loader.exec_module(pub)
class LayoutTests(unittest.TestCase):
 def test_rendered_payload_preserves_layout(self):
  raw=subprocess.check_output(['helm','template','test',str(ROOT/'charts/suse-observability-content'),'-f',str(ROOT/'charts/suse-observability-content/config/values.yaml')],text=True)
  cm=next(d for d in yaml.safe_load_all(raw) if d and d['kind']=='ConfigMap' and 'dashboards.json' in d['data'])
  actual=json.loads(cm['data']['dashboards.json'])['dashboards']
  desired={json.loads(p.read_text())['name']:json.loads(p.read_text()) for p in (ROOT/'charts/suse-observability-content/dashboards').glob('*.json')}
  self.assertEqual(len(actual),5)
  for d in actual:
   pub.validate_dashboard(d);self.assertEqual(d,desired[d['name']])
 def test_union_and_coordinate_regression(self):
  d=json.loads((ROOT/'charts/suse-observability-content/dashboards/traefik.json').read_text());canonical=pub.normalized_dashboard(d)
  self.assertEqual(canonical,pub.normalized_dashboard(canonical))
  changed=copy.deepcopy(d);changed['dashboard']['spec']['layouts'][0]['spec']['items'][1]['y']=0
  self.assertNotEqual(pub.normalized_dashboard(d),pub.normalized_dashboard(changed))
  with self.assertRaises(pub.PublishError):pub.validate_dashboard(changed)
 def test_selected_period_keeps_nonoverlapping_steps(self):
  for p in (ROOT/'charts/suse-observability-content/dashboards').glob('*.json'):
   for panel in json.loads(p.read_text())['dashboard']['spec']['panels'].values():
    for q in panel['spec'].get('queries',[]):
     spec=q['spec']['plugin']['spec'];expr=spec['query']
     if 'range_sum(' in expr:
      self.assertEqual(spec.get('minStep'),'1m')
      self.assertIn('[1m]',expr)
      self.assertNotIn('[1i]',expr)
      self.assertNotIn('${__range}',expr)
      self.assertIn('@ start()',expr)
 def test_legend_avoids_misaligned_summary_values(self):
  # SUSE 2.10.2 sorts Recharts legend labels before assigning point-array indexes.
  # The Last column can therefore be attributed to the wrong series.
  for path in (ROOT/'charts/suse-observability-content/dashboards').glob('*.json'):
   for panel in json.loads(path.read_text())['dashboard']['spec']['panels'].values():
    plugin=panel['spec']['plugin']
    if plugin['kind']=='TimeSeriesChart':
     self.assertFalse(plugin['spec'].get('legend',{}).get('values',[]))
if __name__=='__main__':unittest.main()

