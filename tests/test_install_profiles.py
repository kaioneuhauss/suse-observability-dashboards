"""Check the documented short profiles at their rendered deployment boundary."""
import pathlib
import subprocess
import unittest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def render(profile, chart, *extra):
    output = subprocess.check_output([
        'helm', 'template', 'test', str(ROOT/'charts'/chart),
        '-f', str(ROOT/'deploy'/profile/'values.yaml'), *extra,
    ], text=True)
    return [obj for obj in yaml.safe_load_all(output) if obj]


class InstallationProfiles(unittest.TestCase):
    def test_short_profiles_inherit_resource_budgets_without_creating_credentials(self):
        for profile, chart in [
            ('cluster', 'sre-platform-telemetry'),
            ('harvester', 'sre-platform-telemetry'),
            ('virtual-machines', 'sre-kubevirt-telemetry'),
            ('central', 'suse-observability-content'),
        ]:
            objects = render(profile, chart)
            self.assertFalse(any(obj['kind'] == 'Secret' for obj in objects))
            workloads = [obj for obj in objects if obj['kind'] in ('Job', 'Deployment', 'DaemonSet')]
            self.assertTrue(workloads)
            for obj in workloads:
                for container in obj['spec']['template']['spec']['containers']:
                    with self.subTest(profile=profile, container=container['name']):
                        for bound in ('requests', 'limits'):
                            self.assertTrue(container['resources'][bound]['cpu'])
                            self.assertTrue(container['resources'][bound]['memory'])

    def test_same_secret_reaches_both_publishers_in_apply_and_explicit_delete(self):
        for action in ('apply', 'delete'):
            extra = ['--set', 'lifecycle.action='+action]
            if action == 'delete':
                extra += ['--set', 'lifecycle.confirmDelete=DELETE_MANAGED_OBJECTS']
            jobs = [obj for obj in render('central', 'suse-observability-content', *extra) if obj['kind'] == 'Job']
            self.assertEqual(len(jobs), 2)
            for job in jobs:
                env = {v['name']: v for v in job['spec']['template']['spec']['containers'][0]['env']}
                self.assertEqual(env['STS_CLI_SERVICE_TOKEN']['valueFrom']['secretKeyRef'], {
                    'name': 'suse-observability-publisher-token', 'key': 'serviceToken',
                })
                self.assertEqual(env['PUBLISH_ACTION']['value'], action)


if __name__ == '__main__':
    unittest.main()
