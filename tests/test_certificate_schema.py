import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.utils.certificate_schema import legacy_mounted_schema


class LegacyMountedSchemaTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_schema_resolves_without_mutating_certificate(self):
        schema = {"uuid": "mounted-schema", "group": "single_mounded"}
        lookup = AsyncMock(return_value=schema)
        db = SimpleNamespace(category_schemas=SimpleNamespace(find_one=lookup))
        doc = {"type": "single_mounted", "category_id": None,
               "fields": {"sg": "2.8", "ri": "1.61-1.65", "hardness": "6"}}
        original = dict(doc)
        cache = {}
        self.assertEqual(await legacy_mounted_schema(db, doc, cache), schema)
        self.assertEqual(await legacy_mounted_schema(db, doc, cache), schema)
        lookup.assert_awaited_once_with({
            "group": "single_mounded", "is_deleted": False, "is_active": True,
        })
        self.assertEqual(doc, original)

    async def test_explicit_references_and_other_types_are_not_overridden(self):
        lookup = AsyncMock()
        db = SimpleNamespace(category_schemas=SimpleNamespace(find_one=lookup))
        for key in ("category_id", "schema_uuid", "category_uuid"):
            self.assertIsNone(await legacy_mounted_schema(
                db, {"type": "single_mounted", key: "custom-schema"}, {}))
        for kind in ("single_diamond", "custom", "legacy_scan", "single_mounded"):
            self.assertIsNone(await legacy_mounted_schema(db, {"type": kind}, {}))
        lookup.assert_not_awaited()

    async def test_missing_target_is_cached(self):
        lookup = AsyncMock(return_value=None)
        db = SimpleNamespace(category_schemas=SimpleNamespace(find_one=lookup))
        cache = {}
        for _ in range(2):
            self.assertIsNone(await legacy_mounted_schema(db, {"type": "single_mounted"}, cache))
        lookup.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
