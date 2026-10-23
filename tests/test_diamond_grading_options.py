import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

with patch.dict(os.environ, {'SECRET_KEY': 'test-only-not-a-production-key', 'REMBG_API_URL': 'http://localhost', 'REMBG_API_KEY': 'test-only'}):
    from app.api import certification

class Cursor:
    def __init__(self, rows):
        self.rows = rows
    def sort(self, _):
        return self
    def __aiter__(self):
        async def items():
            for row in self.rows:
                yield row
        return items()

class DiamondGradingOptionsTests(unittest.IsolatedAsyncioTestCase):
    async def schema(self, group, values):
        fields = [dict(field_name=name, field_type='creatable_select', options=['Old default'])
                  for name in ('cut', 'clarity', 'colour', 'shape')]
        queries = []
        def find(query):
            queries.append(query)
            return Cursor([{'name': n} for n in values.get((query['group'], query['type']), [])])
        db = SimpleNamespace(
            category_schemas=SimpleNamespace(find_one=AsyncMock(return_value=dict(group=group, fields=fields))),
            attributes=SimpleNamespace(find=find))
        with patch.object(certification, 'get_db', AsyncMock(return_value=db)):
            result = await certification.get_form_schema('schema')
        return {f['field_name']: f['options'] for f in result['fields']}, queries

    async def test_double_uses_diamond_management_and_maps_colour(self):
        values = {('single_diamond', 'cut'): ['Excellent'], ('single_diamond', 'clarity'): ['VVS1'],
                  ('single_diamond', 'color'): ['D'], ('double_mounded', 'cut'): ['Wrong'],
                  ('double_mounded', 'shape'): ['Oval']}
        options, queries = await self.schema('double_mounded', values)
        self.assertEqual(options, dict(cut=['Excellent'], clarity=['VVS1'], colour=['D'], shape=['Oval']))
        self.assertTrue(all(q['is_deleted'] is False for q in queries))

    async def test_empty_management_does_not_restore_stale_defaults(self):
        options, _ = await self.schema('double_mounded', {})
        self.assertEqual([options[k] for k in ('cut', 'clarity', 'colour')], [[], [], []])

    async def test_other_certificate_groups_keep_their_sources(self):
        _, queries = await self.schema('loose_stone', {})
        self.assertTrue(all(q['group'] == 'loose_stone' for q in queries))
