"""Check the artifacts users actually download, including retained older versions."""
import hashlib
from pathlib import Path
import tarfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class HelmRepositoryTests(unittest.TestCase):
    def test_index_packages_and_digests(self):
        index = yaml.safe_load((ROOT / 'helm/index.yaml').read_text())
        self.assertEqual(index['apiVersion'], 'v1')
        referenced = set()
        for name, releases in index['entries'].items():
            versions = set()
            for release in releases:
                with self.subTest(chart=name, version=release['version']):
                    self.assertNotIn(release['version'], versions)
                    versions.add(release['version'])
                    self.assertEqual(release['urls'], [f"{name}-{release['version']}.tgz"])
                    package = ROOT / 'helm' / release['urls'][0]
                    referenced.add(package.name)
                    self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(), release['digest'])
                    with tarfile.open(package) as archive:
                        metadata = yaml.safe_load(archive.extractfile(f'{name}/Chart.yaml').read())
                    self.assertEqual(metadata['name'], name)
                    self.assertEqual(metadata['version'], release['version'])
        self.assertEqual(referenced, {p.name for p in (ROOT / 'helm').glob('*.tgz')})

    def test_current_packages_match_chart_sources(self):
        index = yaml.safe_load((ROOT / 'helm/index.yaml').read_text())
        for chart in (ROOT / 'charts').iterdir():
            metadata = yaml.safe_load((chart / 'Chart.yaml').read_text())
            with self.subTest(chart=chart.name):
                release = next(r for r in index['entries'][chart.name] if r['version'] == metadata['version'])
                with tarfile.open(ROOT / 'helm' / release['urls'][0]) as archive:
                    packaged = {m.name.split('/', 1)[1]: archive.extractfile(m).read()
                                for m in archive.getmembers() if m.isfile()}
                sources = {str(p.relative_to(chart)): p.read_bytes()
                           for p in chart.rglob('*') if p.is_file()}
                self.assertEqual(set(packaged), set(sources))
                for path, content in sources.items():
                    if path == 'Chart.yaml':
                        self.assertEqual(yaml.safe_load(packaged[path]), yaml.safe_load(content))
                    else:
                        self.assertEqual(packaged[path], content, f'{chart.name}/{path} is stale in the package')


if __name__ == '__main__':
    unittest.main()
