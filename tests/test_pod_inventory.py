import importlib.util,pathlib,unittest,json,io
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inventory',ROOT/'charts/sre-platform-telemetry/files/pod_inventory.py')
inventory=importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
class InventoryTests(unittest.TestCase):
 def test_kubernetes_quantities(self):
  for raw,want in [('4Gi',4294967296),('100m',.1),('2M',2000000),('78125Ki',80000000),('1e3',1000),('1E',1e18),('.5',.5)]:
   self.assertEqual(inventory.quantity(raw),want)
  for raw in ['-1','NaN','bad','1unknown']:
   with self.assertRaises((ValueError,KeyError)):inventory.quantity(raw)
 def test_pagination_running_containers_and_no_private_fields(self):
  pod={'metadata':{'namespace':'demo','name':'app','annotations':{'secret':'DO_NOT_EXPORT'}},'spec':{'containers':[{'name':'main','resources':{'requests':{'cpu':'25m','memory':'64Mi'}},'env':[{'name':'secret','value':'DO_NOT_EXPORT'}]},{'name':'waiting'}]},'status':{'phase':'Running','containerStatuses':[{'name':'main','state':{'running':{}}}]}}
  pages=[{'items':[pod],'metadata':{'continue':'NEXT'}},{'items':[],'metadata':{}}];urls=[]
  def response(req,**kw):urls.append(req.full_url);return io.BytesIO(json.dumps(pages.pop(0)).encode())
  with patch.object(inventory.ssl,'create_default_context'),patch.object(pathlib.Path,'read_text',return_value='fake-test-token'),patch.object(inventory.urllib.request,'urlopen',side_effect=response):s=inventory.refresh()
  self.assertEqual(len(urls),2);self.assertIn('continue=NEXT',urls[1]);self.assertNotIn('DO_NOT_EXPORT',s);self.assertNotIn('fake-test-token',s)
  self.assertIn('container="main"} 1',s);self.assertIn('container="waiting"} 0',s);self.assertIn('} 0.025',s);self.assertNotIn('sre_pod_container_cpu_limit',s)
if __name__=='__main__':unittest.main()
