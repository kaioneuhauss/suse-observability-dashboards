"""Offline unit tests. No SUSE/Kubernetes calls and no credentials required."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('publisher', ROOT/'charts/suse-observability-content/files/publisher.py')
p = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(p)

DESIRED = {'name':'Test dashboard','description':'testing','scope':'publicDashboard','dashboard':{'metadata':{'project':'{"saveVariables":false}'},'spec':{'panels':{'note':{'spec':{'queries':[]}}}}}}
class FakeCLI:
    def __init__(self, old=False, forbidden=False, fail_create=False):
        self.calls=[];self.forbidden=forbidden;self.fail_create=fail_create
        self.items=([dict(id=123,identifier='urn:custom:dashboard:test',**copy.deepcopy(DESIRED))] if old else [])
    def run(self,*a,**kw):
        self.calls.append(a)
        if a[:2]==('dashboard','list'):return {'dashboards':copy.deepcopy(self.items)}
        if a[:2]==('dashboard','describe'):return {'data':copy.deepcopy(self.items[0]),'format':'json'}
        if a[:2]==('dashboard','delete'):
            if self.forbidden:raise p.PublishError('403 Forbidden')
            self.items=[obj for obj in self.items if str(obj['id']) != a[3]];return {}
        if a[:2]==('dashboard','apply'):
            if self.fail_create: self.fail_create=False; raise p.PublishError('creation error')
            obj=json.loads(Path(a[3]).read_text()); obj.update(id=456,identifier='urn:custom:dashboard:new');self.items=[obj];return {}
        raise AssertionError(a)
class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.work=patch.object(p,'WORK',Path(self.tmp.name));self.work.start()
    def tearDown(self):self.work.stop();self.tmp.cleanup()
    def test_create(self):
        cli=FakeCLI();p.sync_dashboard(cli,DESIRED,'apply','replace');self.assertEqual(len(cli.items),1)
    def test_unchanged_no_writes(self):
        cli=FakeCLI(old=True);p.sync_dashboard(cli,DESIRED,'apply','replace');self.assertFalse(any(c[1] in ('delete','apply') for c in cli.calls))
    def test_changed_replacement(self):
        cli=FakeCLI(old=True);v=copy.deepcopy(DESIRED);v['description']='new';p.sync_dashboard(cli,v,'apply','replace');self.assertEqual(cli.items[0]['description'],'new')
    def test_403_no_duplicate(self):
        cli=FakeCLI(old=True,forbidden=True);v=copy.deepcopy(DESIRED);v['description']='new'
        with self.assertRaises(p.PublishError):p.sync_dashboard(cli,v,'apply','replace')
        self.assertFalse(any(c[:2]==('dashboard','apply') for c in cli.calls));self.assertEqual(len(cli.items),1)
    def test_restore_after_failed_create(self):
        cli=FakeCLI(old=True,fail_create=True);v=copy.deepcopy(DESIRED);v['description']='new'
        with self.assertRaises(p.PublishError):p.sync_dashboard(cli,v,'apply','replace')
        self.assertEqual(cli.items[0]['description'],'testing')
    def test_plan_no_writes(self):
        cli=FakeCLI(old=True);p.sync_dashboard(cli,DESIRED,'plan','replace');self.assertEqual(cli.calls,[('dashboard','list')])
    def test_delete_scoped(self):
        cli=FakeCLI(old=True);cli.items.append({'id':777,'name':'Kubernetes Cluster','identifier':'urn:stackpack:kubernetes-v2:dashboard:cluster'})
        p.sync_dashboard(cli,DESIRED,'delete','replace')
        self.assertEqual([obj['id'] for obj in cli.items],[777])
        self.assertIn(('dashboard','delete','--id','123'),cli.calls)
        self.assertNotIn(('dashboard','delete','--id','777'),cli.calls)
    def test_native_same_name_blocked(self):
        cli=FakeCLI(old=True);cli.items[0]['identifier']='urn:stackpack:dashboard:test'
        with self.assertRaises(p.PublishError):p.sync_dashboard(cli,DESIRED,'delete','replace')
        self.assertFalse(any(c[1]=='delete' for c in cli.calls))
    def test_duplicate_names_blocked(self):
        cli=FakeCLI(old=True);cli.items.append(copy.deepcopy(cli.items[0]))
        with self.assertRaises(p.PublishError):p.sync_dashboard(cli,DESIRED,'delete','replace')
    def test_ids(self):
        for val in ('',None,'abc',-1,0):
            with self.assertRaises(p.PublishError):p.numeric_id({'id':val})
        self.assertEqual(p.numeric_id({'id':139822756311820}),'139822756311820')
    def test_normalizes_queries_only(self):
        actual=copy.deepcopy(DESIRED);del actual['dashboard']['spec']['panels']['note']['spec']['queries'];actual['dashboard']['metadata']['updatedAt']='yesterday'
        self.assertEqual(p.normalized_dashboard(actual),p.normalized_dashboard(DESIRED))
    def test_changed_spec_detected(self):
        actual=copy.deepcopy(DESIRED);actual['dashboard']['spec']['panels']['note']['spec']['changed']=True
        self.assertNotEqual(p.normalized_dashboard(actual),p.normalized_dashboard(DESIRED))
    def test_list_schema_rejected(self):
        class Wrong:
            def run(self,*a):return {'items':[]}
        with self.assertRaises(p.PublishError):p.listed(Wrong(),'dashboard')
    def test_redaction(self):
        with patch.dict('os.environ',{'STS_CLI_SERVICE_TOKEN':'secret-value'}):self.assertNotIn('secret-value',p.redact('failure secret-value'))
    def test_confirmation_required(self):
        with patch.dict('os.environ',{'PUBLISH_ACTION':'delete','CONFIRM_DELETE':''}):
            with self.assertRaisesRegex(p.PublishError,'confirmacao'):p.main()
    def test_monitor_plan_and_duplicates(self):
        catalog=json.loads((ROOT/'charts/suse-observability-content/files/catalog.json').read_text())
        class Empty:
            def run(self,*a):assert a==('monitor','list');return {'monitors':[]}
        with patch.object(p,'ROOT',ROOT/'charts/suse-observability-content/monitors'):
            p.sync_monitors(Empty(),catalog,'plan')
            with self.assertRaises(p.PublishError):p.sync_monitors(Empty(),[catalog[0],catalog[0]],'plan')
    def test_monitor_wrong_identity_no_writes(self):
        rules=json.loads((ROOT/'charts/suse-observability-content/files/catalog.json').read_text())[:1]
        class Wrong:
            def run(self,*a):assert a==('monitor','list');return {'monitors':[{'id':123,'name':rules[0]['name'],'identifier':'urn:stackpack:monitor:native','tags':['sre-dashboards','platform']}]}
        with patch.object(p,'ROOT',ROOT/'charts/suse-observability-content/monitors'):
            with self.assertRaises(p.PublishError):p.sync_monitors(Wrong(),rules,'delete')
    def test_monitor_tag_migration_and_idempotence(self):
        rule=json.loads((ROOT/'charts/suse-observability-content/files/catalog.json').read_text())[0]
        identifier='urn:custom:monitor:sre-dashboards:'+rule['slug']
        actual={'id':123,'name':rule['name'],'identifier':identifier,'tags':['sre-dashboards','platform'],
                'description':rule['description'],'remediationHint':rule['remediation'],'status':'ENABLED','intervalSeconds':60,
                'arguments':[{'_type':kind,'value':value} for kind,value in [
                    ('ArgumentPromQLMetricVal',{'query':rule['query'],'unit':'none','aliasTemplate':rule['alias']}),
                    ('ArgumentDoubleVal',rule['threshold']),('ArgumentComparatorWithoutEqualityVal',rule['comparator']),
                    ('ArgumentFailingHealthStateVal',rule['severity']),('ArgumentStringVal',rule['urnTemplate']),
                    ('ArgumentStringVal',rule['titleTemplate'])]]}
        class MonitorCLI:
            def __init__(self):self.writes=0
            def run(self,*args):
                if args==('monitor','list'):return {'monitors':[copy.deepcopy(actual)]}
                if args[:2]==('monitor','apply'):
                    self.writes+=1
                    self.source=Path(args[3]).read_text()
                    actual['tags']=rule['tags'][:]
                    return {}
                raise AssertionError(args)
        cli=MonitorCLI()
        self.assertFalse(p.verify_monitor(actual,rule,identifier))
        with patch.object(p,'ROOT',ROOT/'charts/suse-observability-content/monitors'):
            p.sync_monitors(cli,[rule],'apply')
            self.assertEqual(cli.writes,1)
            self.assertIn('identifier: '+identifier,cli.source)
            for tag in rule['tags']:self.assertIn(tag,cli.source)
            self.assertTrue(p.verify_monitor(actual,rule,identifier))
            p.sync_monitors(cli,[rule],'apply')
            self.assertEqual(cli.writes,1)
            actual['tags'].append('customer-owned')
            with self.assertRaises(p.PublishError):p.sync_monitors(cli,[rule],'delete')

    def test_publisher_copies_identical(self):
        src=(ROOT/'charts/suse-observability-content/files/publisher.py').read_bytes()
        for f in (ROOT/'charts').glob('*/files/publisher.py'):self.assertEqual(src,f.read_bytes(),f)

if __name__=='__main__':unittest.main()
