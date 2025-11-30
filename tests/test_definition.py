import unittest

from .context import definition

class TestIndexingDef(unittest.TestCase):
    def test_from_dict_empty(self):
        data = {}
        idx_def = definition.IndexingDef.from_dict(data)
        self.assertIsInstance(idx_def, definition.IndexingDef)
        self.assertEqual(idx_def.pipelines, [])

if __name__ == "__main__":
    unittest.main()