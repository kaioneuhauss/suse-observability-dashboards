"""Resource budgets must survive rendering and reject missing/zero budgets."""
import pathlib
import subprocess
import unittest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ResourceTests(unittest.TestCase):
    def test_all_rendered_containers_have_cpu_and_memory_budgets(self):
        count = 0
        for profile in (ROOT / 'charts').glob('*/config/*.yaml'):
            chart = profile.parent.parent
            raw = subprocess.check_output(['helm', 'template', 'test', str(chart), '-f', str(profile)], text=True)
            for obj in yaml.safe_load_all(raw):
                if not obj:
                    continue
                if obj['kind'] == 'Pod':
                    spec = obj['spec']
                elif obj['kind'] in ('Deployment', 'DaemonSet', 'StatefulSet', 'Job'):
                    spec = obj['spec']['template']['spec']
                else:
                    continue
                for container in spec.get('containers', []) + spec.get('initContainers', []):
                    with self.subTest(profile=profile.name, workload=obj['metadata']['name'], container=container['name']):
                        for kind in ('requests', 'limits'):
                            budget = container.get('resources', {}).get(kind, {})
                            self.assertTrue(budget.get('cpu'))
                            self.assertTrue(budget.get('memory'))
                    count += 1
        self.assertGreater(count, 10)

    def test_missing_and_zero_budgets_are_rejected(self):
        cases = [
            ('sre-platform-telemetry', 'harvester.yaml', 'vmagent.resources.requests=null'),
            ('sre-platform-telemetry', 'harvester.yaml', 'nodeExporter.resources.limits.cpu=0'),
            ('sre-platform-telemetry', 'rancher-kaio.yaml', 'traefik.inventoryResources.limits.memory=null'),
            ('sre-platform-telemetry', 'harvester.yaml', 'podInventory.resources.requests.memory=0Mi'),
            ('sre-kubevirt-telemetry', 'values.yaml', 'resources.requests.cpu=null'),
            ('suse-observability-content', 'values.yaml', 'publisher.resources.limits=null'),
        ]
        for chart, profile, setting in cases:
            with self.subTest(chart=chart, setting=setting):
                result = subprocess.run(['helm', 'template', 'test', str(ROOT/'charts'/chart), '-f', str(ROOT/'charts'/chart/'config'/profile), '--set', setting], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('schema', result.stderr.lower())


if __name__ == '__main__':
    unittest.main()
