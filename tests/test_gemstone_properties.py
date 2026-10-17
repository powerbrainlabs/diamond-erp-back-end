import re
import unittest
from types import SimpleNamespace

from app.utils.gemstone_properties import sync_gemstone_properties


class Attributes:
    def __init__(self, rows):
        self.rows = rows

    async def update_many(self, query, update):
        for row in self.rows:
            if (row['type'] in query['type']['$in']
                    and row['is_deleted'] == query['is_deleted']
                    and re.search(query['name']['$regex'], row['name'], re.I)):
                row.update(update['$set'])


class GemstonePropertiesTests(unittest.IsolatedAsyncioTestCase):
    async def test_syncs_all_gemstone_roles_and_preserves_other_fields(self):
        rows = [dict(type=role, name='Natural Diamond', is_deleted=False,
                     sg='old', ri='old', hardness='10', group=group)
                for group, role in [('loose_stone', 'gemstone'),
                                    ('single_mounded', 'gemstone'),
                                    ('double_mounded', 'primary_gemstone'),
                                    ('double_mounded', 'secondary_gemstone')]]
        db = SimpleNamespace(attributes=Attributes(rows))
        await sync_gemstone_properties(db, rows[0], {'sg': '3.55', 'ri': ''})
        for row in rows:
            self.assertEqual((row['sg'], row['ri'], row['hardness']), ('3.55', '', '10'))

    async def test_matches_literal_name_case_insensitively_and_ignores_other_entries(self):
        rows = [dict(type=role, name=name, is_deleted=deleted, sg='old')
                for role, name, deleted in [('gemstone', ' Quartz (A) ', False),
                                            ('gemstone', 'quartz (a)', False),
                                            ('gemstone', 'Quartz A', False),
                                            ('color', 'Quartz (A)', False),
                                            ('gemstone', 'Quartz (A)', True)]]
        await sync_gemstone_properties(SimpleNamespace(attributes=Attributes(rows)),
                                       rows[0], {'sg': 'new', 'name': 'ignored'})
        self.assertEqual([r['sg'] for r in rows], ['new', 'new', 'old', 'old', 'old'])

    async def test_non_gemstone_and_name_only_changes_do_not_sync(self):
        rows = [dict(type='gemstone', name='Ruby', is_deleted=False, sg='old')]
        db = SimpleNamespace(attributes=Attributes(rows))
        await sync_gemstone_properties(db, dict(type='color', name='Ruby'), {'sg': 'new'})
        await sync_gemstone_properties(db, rows[0], {'name': 'Ruby'})
        self.assertEqual(rows[0]['sg'], 'old')
