"""Keep operator guidance, published monitor rules and chart data consistent."""
import json,pathlib,unittest,yaml
ROOT=pathlib.Path(__file__).resolve().parents[1]/'charts/suse-observability-content'
class AlertCoverageTests(unittest.TestCase):
 def test_monitor_catalog_matches_sty(self):
  for m in json.loads((ROOT/'files/catalog.json').read_text()):
   d=yaml.safe_load((ROOT/'monitors'/(m['slug']+'.sty')).read_text().replace('{{ get "urn:stackpack:common:monitor-function:threshold" }}','function'))['nodes'][0]
   self.assertEqual(d['arguments']['metric']['query'],m['query'],m['slug'])
   self.assertEqual(d['arguments']['threshold'],m['threshold'],m['slug'])
   self.assertEqual(d['arguments']['comparator'],m['comparator'],m['slug'])
   self.assertEqual(d['description'],m['description'],m['slug'])
   self.assertEqual(d['tags'],m['tags'],m['slug'])
   self.assertIn('sre-dashboards',d['tags'])
 def test_every_metric_panel_has_guidance_and_layout(self):
  coverage=json.loads((ROOT/'files/panel-monitor-coverage.json').read_text());seen={(c['dashboard'],c['panel']) for c in coverage}
  for p in (ROOT/'dashboards').glob('*.json'):
   s=json.loads(p.read_text())['dashboard']['spec'];refs={i['content']['$ref'].split('/')[-1] for i in s['layouts'][0]['spec']['items']}
   self.assertEqual(set(s['panels']),refs)
   for key,panel in s['panels'].items():
    if panel['spec']['plugin']['kind']=='Markdown':continue
    self.assertIn((p.stem,key),seen)
    self.assertEqual(next(c['title'] for c in coverage if (c['dashboard'],c['panel'])==(p.stem,key)),panel['spec']['display']['name'])
    self.assertIn('When to investigate / alert coverage:',panel['spec']['display']['description'])
if __name__=='__main__':unittest.main()
