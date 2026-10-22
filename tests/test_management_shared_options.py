"""Exercise Management save routes with database calls isolated."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

with patch.dict(os.environ, {
    'SECRET_KEY': 'test-only-not-a-production-key',
    'REMBG_API_URL': 'http://localhost',
    'REMBG_API_KEY': 'test-only',
}):
    from app.api import categories, dynamic_categories


class ManagementSharedOptionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_shares_non_gemstone_options(self):
        attributes = SimpleNamespace(find_one=AsyncMock(return_value=None),
                                     insert_one=AsyncMock(), update_one=AsyncMock())
        db = SimpleNamespace(attributes=attributes,
                             certificate_types=SimpleNamespace(find_one=AsyncMock(return_value={'slug': 'loose_stone'})))
        with patch.object(dynamic_categories, 'get_db', AsyncMock(return_value=db)):
            await dynamic_categories.create_attribute('loose_stone', 'comment',
                                                       {'name': '  Natural inclusions  '},
                                                       dict(id='test', name='Admin', email='test@example.com'))
        query, update = attributes.update_one.call_args.args
        self.assertEqual((query['group'], query['type']), ('single_mounded', 'comment'))
        self.assertEqual(update['$setOnInsert']['name'], 'Natural inclusions')

    async def test_single_mounted_exposes_shared_color_for_older_schemas(self):
        for fields in ([], [{'field_name': 'color', 'field_type': 'dropdown', 'display_order': 1}]):
            db = SimpleNamespace(
                certificate_types=SimpleNamespace(find_one=AsyncMock(return_value={'slug': 'single_mounded'})),
                category_schemas=SimpleNamespace(find_one=AsyncMock(return_value={'fields': fields})))
            with patch.object(dynamic_categories, 'get_db', AsyncMock(return_value=db)):
                result = await dynamic_categories.get_type_fields('single_mounded', {})
            self.assertEqual([f['field_name'] for f in result['data']].count('color'), 1)
