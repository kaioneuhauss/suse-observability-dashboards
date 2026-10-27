"""The uninstall boundary must keep credentials and definitions until cleanup succeeds."""
import pathlib
import subprocess
import unittest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]


def render(module, *args):
    result = subprocess.check_output([
        'helm', 'template', 'test', str(ROOT / 'charts' / ('suse-observability-' + module)),
        '-f', str(ROOT / 'examples' / (module + '.yaml')), *args,
    ], text=True)
    return [obj for obj in yaml.safe_load_all(result) if obj]


class UninstallHooks(unittest.TestCase):
    def test_cleanup_uses_same_identity_and_definitions_as_publication(self):
        for module in ('virtualization', 'imports', 'applications', 'traefik', 'kubernetes'):
            objects = render(module, '--set', 'mode=content',
                             '--set', 'auth.dashboards.existingSecret=dashboard-owner',
                             '--set', 'auth.monitors.existingSecret=monitor-owner')
            jobs = {obj['metadata']['name']: obj for obj in objects if obj['kind'] == 'Job'}
            cleanups = [job for job in jobs.values() if job['metadata']['annotations']['helm.sh/hook'] == 'pre-delete']
            self.assertEqual(len(cleanups), 2)
            for job in cleanups:
                name = job['metadata']['name'].removesuffix('-delete')
                publish = jobs[name]
                pod = job['spec']['template']['spec']
                self.assertEqual(pod['volumes'], publish['spec']['template']['spec']['volumes'])
                env = {v['name']: v for v in pod['containers'][0]['env']}
                pubenv = {v['name']: v for v in publish['spec']['template']['spec']['containers'][0]['env']}
                self.assertEqual(env['STS_CLI_SERVICE_TOKEN'], pubenv['STS_CLI_SERVICE_TOKEN'])
                self.assertEqual(env['PUBLISH_ACTION']['value'], 'delete')
                self.assertEqual(env['CONFIRM_DELETE']['value'], 'DELETE_MANAGED_OBJECTS')
                self.assertEqual(pubenv['PUBLISH_ACTION']['value'], 'apply')
                policy = job['metadata']['annotations']['helm.sh/hook-delete-policy']
                self.assertIn('hook-succeeded', policy)
                self.assertNotIn('hook-failed', policy)
                self.assertFalse(pod['automountServiceAccountToken'])

    def test_plan_opt_out_and_telemetry_cannot_delete_content_on_uninstall(self):
        for settings in (('mode=telemetry',), ('lifecycle.action=plan',), ('lifecycle.deleteOnUninstall=false',)):
            args = [part for setting in settings for part in ('--set', setting)]
            objects = render('traefik', *args)
            self.assertFalse(any(obj['metadata'].get('annotations', {}).get('helm.sh/hook') == 'pre-delete' for obj in objects))

    def test_disabled_content_is_not_deleted(self):
        objects = render('applications', '--set', 'content.monitors.enabled=false')
        self.assertFalse(any(obj['kind'] == 'Job' and 'monitors' in obj['metadata']['name'] for obj in objects))


if __name__ == '__main__':
    unittest.main()
