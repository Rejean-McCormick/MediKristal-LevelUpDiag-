import tempfile
import unittest
import zipfile
from pathlib import Path

from run_medikristal_zip import find_target, safe_extract


class ZipRunnerTests(unittest.TestCase):
    def test_rejects_zip_slip(self):
        with tempfile.TemporaryDirectory() as td:
            archive=Path(td)/'bad.zip'
            with zipfile.ZipFile(archive,'w') as zf:
                zf.writestr('../escape.txt','x')
            with self.assertRaises(SystemExit):
                safe_extract(archive,Path(td)/'out')

    def test_finds_single_medikristal_root(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'wrapper'/'MediKristal'
            (root/'backend').mkdir(parents=True)
            (root/'contracts').mkdir()
            (root/'backend/pyproject.toml').write_text('[project]\nname="medikristal"\n',encoding='utf-8')
            (root/'contracts/openapi.json').write_text('{}',encoding='utf-8')
            self.assertEqual(find_target(Path(td)),root)

if __name__=='__main__': unittest.main()
