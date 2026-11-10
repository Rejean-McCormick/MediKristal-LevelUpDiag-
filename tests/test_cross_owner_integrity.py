"""Independent software-only proof gates for MediKristal snapshots (no clinical claim)."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from levels.mk30_runtime_smoke import assess_engineering_only_capabilities
from levels.mk50_packaging import verify_delivery_manifest, verify_sbom_lock


class MediKristalCrossOwnerIntegrityTests(unittest.TestCase):
    def test_only_engineering_use_and_bounded_external_adapters_pass(self):
        caps = {
            'provider_network': {
                'state': 'not_configured',
                'supported_uses': ['engineering'],
                'limitations': ['No external provider is activated.'],
            },
            'fhir_partner': {
                'state': 'unavailable',
                'supported_uses': ['engineering'],
                'limitations': ['Partner contract absent.'],
            },
        }
        required = {'provider_network': ['unavailable', 'not_configured'], 'fhir_partner': ['unavailable', 'not_configured']}
        self.assertEqual(assess_engineering_only_capabilities(caps, required), [])
        caps['provider_network']['supported_uses'] = ['engineering', 'clinical']
        self.assertIn('unqualified_supported_use', str(assess_engineering_only_capabilities(caps, required)))

    def test_missing_limitations_and_available_partner_are_rejected(self):
        caps = {'kristal_export': {'state': 'available', 'supported_uses': ['engineering'], 'limitations': []}}
        issues = assess_engineering_only_capabilities(caps, {'kristal_export': ['not_configured', 'unavailable']})
        self.assertEqual({e['reason'] for e in issues}, {'missing_limitations', 'unauthorized_external_state'})

    def test_empty_runtime_capabilities_cannot_pass(self):
        issues = assess_engineering_only_capabilities({}, {'fhir_partner': ['not_configured']})
        self.assertIn('missing_capability_evidence', str(issues))

    def _manifest_fixture(self, root: Path) -> dict:
        file = root / 'app.py'
        file.write_text('print("synthetic")\n', encoding='utf-8')
        raw = file.read_bytes()
        return {'format': 'medikristal.delivery-manifest/2', 'api_version': '0.2.0',
                'files': [{'path': 'app.py', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}]}

    def test_manifest_complete_and_omitted_source_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._manifest_fixture(root)
            self.assertEqual(verify_delivery_manifest(root, manifest, '0.2.0'), [])
            (root / 'hidden.py').write_text('secret = 1\n', encoding='utf-8')
            issues = verify_delivery_manifest(root, manifest, '0.2.0')
            self.assertIn({'path': 'hidden.py', 'reason': 'unlisted_source_file'}, issues)

    def test_manifest_unsafe_and_duplicate_entry_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = self._manifest_fixture(root)
            manifest['files'].append(dict(manifest['files'][0]))
            manifest['files'].append({'path': '../outside', 'bytes': 1, 'sha256': '0' * 64})
            issues = verify_delivery_manifest(root, manifest, '0.2.0')
            self.assertIn('duplicate_entry', {e['reason'] for e in issues})
            self.assertIn('unsafe_path', {e['reason'] for e in issues})

    def _sbom_fixture(self, root: Path):
        (root / 'backend').mkdir()
        raw = b'fastapi==0.128.2\npsycopg[binary]==3.3.6\n'
        (root / 'backend/requirements.lock').write_bytes(raw)
        sbom = {
            'metadata': {'properties': [{'name': 'medikristal:requirements-lock-sha256',
                                         'value': hashlib.sha256(raw).hexdigest()}]},
            'components': [
                {'name': 'fastapi', 'version': '0.128.2', 'properties': []},
                {'name': 'psycopg', 'version': '3.3.6', 'properties': [
                    {'name': 'medikristal:extras', 'value': 'binary'}]},
            ],
        }
        return sbom

    def test_sbom_exact_lock_and_extras_verified(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sbom = self._sbom_fixture(root)
            self.assertEqual(verify_sbom_lock(root, sbom), [])
            sbom['components'][1]['properties'].clear()
            self.assertIn('extras_mismatch', str(verify_sbom_lock(root, sbom)))

    def test_sbom_stale_digest_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sbom = self._sbom_fixture(root)
            sbom['metadata']['properties'][0]['value'] = '0' * 64
            self.assertIn('stale_or_missing_lock_digest', str(verify_sbom_lock(root, sbom)))


if __name__ == '__main__':
    unittest.main()
