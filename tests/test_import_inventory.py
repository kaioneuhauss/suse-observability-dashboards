"""Semantic and privacy guarantees for the optional read-only VMIC exporter."""
import copy
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'components/sre-import-telemetry/files/import_inventory.py'
spec=importlib.util.spec_from_file_location('imports',path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def condition(kind, seconds):
 return {'type':kind,'status':'True','lastTransitionTime':f'2026-01-01T00:{seconds//60:02}:{seconds%60:02}Z'}


class ImportInventoryTests(unittest.TestCase):
 def record(self):
  return {'metadata':{'name':'sample','namespace':'test','creationTimestamp':'2026-01-01T00:00:00Z'},'spec':{'sourceCluster':{'kind':'VmwareSource'},'secret':'must-not-export'},'status':{'importStatus':'virtualMachineRunning','importedVirtualMachineName':'target','importConditions':[condition('VMPoweredOff',10),condition('VMExported',50)],'diskImportStatus':[{'diskName':'private-path','diskSize':1024,'diskRoute':'https://private/?token=secret','diskConditions':[condition('VirtualMachineImageSubmitted',60),condition('VirtualMachineImageReady',120)]},{'diskSize':2048,'diskConditions':[condition('VirtualMachineImageSubmitted',80),condition('VirtualMachineImageReady',180)]}]}}
 def values(self,text,name):
  return [float(line.rsplit(' ',1)[1]) for line in text.splitlines() if line.startswith(name+'{')]
 def test_completed_stage_times_are_not_total_migration_duration(self):
  text=mod.build_metrics([self.record()],mod.timestamp('2026-01-01T01:00:00Z'))
  self.assertEqual(self.values(text,'harvester_import_stage_duration_seconds'),[40,120])
  self.assertIn('outcome="succeeded"',text)
  self.assertNotIn('harvester_import_active_age_seconds',text)
  self.assertNotIn('migration_duration',text)
  self.assertEqual(self.values(text,'harvester_import_disk_capacity_bytes'),[3072,3072,0])
  self.assertEqual(self.values(text,'harvester_import_created_timestamp_seconds'),[1767225600])
 def test_active_age_and_partial_disk_readiness(self):
  obj=self.record();obj['status']['importStatus']='diskImageSubmitted';obj['status']['diskImportStatus'][1]['diskConditions']=[]
  text=mod.build_metrics([obj],mod.timestamp('2026-01-01T01:00:00Z'))
  self.assertEqual(self.values(text,'harvester_import_disks'),[2,1,0])
  self.assertEqual(self.values(text,'harvester_import_active_age_seconds'),[3600])
  self.assertEqual(self.values(text,'harvester_import_stage_duration_seconds'),[40])
 def test_failure_condition_detected_before_phase_changes(self):
  obj=self.record();obj['status']['importStatus']='sourceReady';obj['status']['importConditions'].append(condition('VMExportFailed',90))
  self.assertIn('outcome="failed"',mod.build_metrics([obj],1))
 def test_success_wins_over_old_error_condition(self):
  obj=self.record();obj['status']['importConditions'].append(condition('VMExportFailed',1))
  self.assertIn('outcome="succeeded"',mod.build_metrics([obj],1))
 def test_missing_and_invalid_sizes_are_not_zero(self):
  for value in (None,-1,'bad','NaN'):
   obj=self.record();obj['status']['diskImportStatus'][0]['diskSize']=value
   text=mod.build_metrics([obj],1)
   self.assertEqual(self.values(text,'harvester_import_disk_capacity_bytes'),[0])
 def test_unknown_phases_remain_unknown(self):
  obj=self.record();obj['status']['importStatus']='brandNewPhase'
  self.assertIn('outcome="unknown"',mod.build_metrics([obj],1))
 def test_no_disks_has_no_stage_duration_or_fake_progress(self):
  obj=self.record();obj['status']={'importStatus':'sourceReady'}
  text=mod.build_metrics([obj],1)
  self.assertEqual(self.values(text,'harvester_import_disks'),[0,0,0])
  self.assertNotIn('harvester_import_stage_duration_seconds',text)
  self.assertNotIn('progress',text)
 def test_source_credentials_paths_and_messages_never_exported(self):
  obj=self.record();obj['status']['importConditions'][0]['message']='sensitive-error-message'
  text=mod.build_metrics([obj],1)
  for value in ('must-not-export','private-path','private/?token','sensitive-error-message'):
   self.assertNotIn(value,text)
 def test_poll_failure_and_staleness_remove_old_healthy_inventory(self):
  s=mod.Snapshot(30);s.update([self.record()],100)
  self.assertTrue(s.metrics(120)[1]);s.fail();text,ok=s.metrics(121)
  self.assertFalse(ok);self.assertNotIn('harvester_import_info',text)
  s.update([self.record()],130);self.assertTrue(s.metrics(140)[1])
  self.assertFalse(s.metrics(221)[1]);self.assertNotIn('harvester_import_info',s.metrics(221)[0])
 def test_paginated_list_retains_all_objects(self):
  calls=[]
  def fetch(params):
   calls.append(params)
   return {'items':[{'id':len(calls)}],'metadata':{'continue':'next' if len(calls)==1 else ''}}
  self.assertEqual(mod.list_imports(fetch),[{'id':1},{'id':2}])
  self.assertEqual(calls,[{'limit':500},{'limit':500,'continue':'next'}])


if __name__=='__main__':unittest.main()
