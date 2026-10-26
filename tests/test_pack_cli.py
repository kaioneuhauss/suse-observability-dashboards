"""Lifecycle safety: an external delete failure must never remove its publisher."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackLifecycleTests(unittest.TestCase):
    def execute(self, mode, version='1.2.0', delete_fails=False):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            binary = temp / 'bin'; binary.mkdir()
            (temp / 'kubeconfig').write_text('test-only')
            helper = '''#!/usr/bin/env python3
import json,os,sys,pathlib
args=sys.argv[1:]
with open(os.environ['CALL_LOG'],'a') as log:log.write(json.dumps([pathlib.Path(sys.argv[0]).name,*args])+'\\n')
if pathlib.Path(sys.argv[0]).name=='kubectl':raise SystemExit(0)
if args[0]=='list':
 if '--short' in args: print('obs-traefik')
 else: print(json.dumps([{'chart':'suse-observability-traefik-'+os.environ['TEST_VERSION']}]))
elif args[:2]==['get','values']: print('mode: '+os.environ['TEST_MODE'])
elif args[:2]==['get','manifest']:print('apiVersion: v1\\nkind: ConfigMap')
elif args[:2]==['show','chart']:print('version: 1.2.0')
elif args[0]=='upgrade' and os.environ['DELETE_FAILS']=='1':raise SystemExit(9)
'''
            for tool in ('helm','kubectl'):
                p=binary/tool;p.write_text(helper);p.chmod(0o755)
            env=dict(os.environ,PATH=str(binary)+os.pathsep+os.environ['PATH'],KCFG=str(temp/'kubeconfig'),CTX='explicit-test-cluster',NS='explicit-test-namespace',PACK_BACKUP_DIR=str(temp/'backups'),CALL_LOG=str(temp/'calls'),TEST_MODE=mode,TEST_VERSION=version,DELETE_FAILS=str(int(delete_fails)))
            process=subprocess.run(['bash',str(ROOT/'scripts/pack.sh'),'remove','traefik'],env=env,capture_output=True,text=True)
            import json
            calls=[json.loads(line) for line in (temp/'calls').read_text().splitlines()]
            return process,calls

    def test_delete_failure_preserves_release_and_hooks(self):
        process,calls=self.execute('content',delete_fails=True)
        self.assertNotEqual(process.returncode,0)
        self.assertTrue(any(c[1]=='upgrade' for c in calls))
        self.assertFalse(any(c[1] in ('uninstall','delete') for c in calls))

    def test_wrong_content_version_stops_before_mutation(self):
        process,calls=self.execute('content',version='1.0.0')
        self.assertNotEqual(process.returncode,0)
        self.assertFalse(any(c[1] in ('upgrade','uninstall','delete') for c in calls))

    def test_telemetry_removal_does_not_delete_external_content(self):
        process,calls=self.execute('telemetry',version='1.0.0')
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertFalse(any(c[1]=='upgrade' for c in calls))
        self.assertTrue(any(c[1]=='uninstall' for c in calls))
        for call in calls:
            if call[1] in ('get','list','uninstall','delete'):
                self.assertIn('--kubeconfig',call)
                self.assertIn('explicit-test-cluster',call)
                self.assertIn('explicit-test-namespace',call)


if __name__=='__main__':unittest.main()
