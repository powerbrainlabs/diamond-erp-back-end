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


class ManagementSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_update_routes_propagate_saved_properties(self):
        for module in (categories, dynamic_categories):
            with self.subTest(route=module.__name__):
                doc = dict(_id='test', uuid='test', name='Natural Diamond',
                           group='single_mounded', type='gemstone')
                attributes = SimpleNamespace(
                    find_one=AsyncMock(side_effect=(
                        [doc, None, doc] if module is dynamic_categories else [doc, doc])),
                    update_one=AsyncMock(), update_many=AsyncMock())
                db = SimpleNamespace(attributes=attributes)
                with patch.object(module, 'get_db', AsyncMock(return_value=db)):
                    await module.update_attribute('test', {'name': 'Natural Diamond', 'sg': '3.6'}, {})
                query, update = attributes.update_many.call_args.args
                self.assertIn('secondary_gemstone', query['type']['$in'])
                self.assertEqual(update['$set']['sg'], '3.6')
                self.assertNotIn('name', update['$set'])

    async def test_both_create_routes_propagate_supplied_properties(self):
        for module, group in ((categories, 'gemstone'), (dynamic_categories, 'loose_stone')):
            with self.subTest(route=module.__name__):
                attributes = SimpleNamespace(find_one=AsyncMock(return_value=None),
                                             insert_one=AsyncMock(), update_many=AsyncMock())
                db = SimpleNamespace(attributes=attributes,
                                     certificate_types=SimpleNamespace(find_one=AsyncMock(return_value={'slug': group})))
                user = dict(id='test', name='Admin', email='test@example.com')
                with patch.object(module, 'get_db', AsyncMock(return_value=db)):
                    await module.create_attribute(group, 'gemstone',
                                                  {'name': 'Ruby', 'hardness': '9'}, user)
                self.assertEqual(attributes.update_many.call_args.args[1]['$set']['hardness'], '9')
