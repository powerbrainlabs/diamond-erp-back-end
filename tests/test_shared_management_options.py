import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.utils.shared_management_options import share_new_management_option


class SharedManagementOptionsTests(unittest.IsolatedAsyncioTestCase):
    async def targets(self, group, field):
        attributes = SimpleNamespace(update_one=AsyncMock())
        doc = dict(uuid='source', _id='mongo-id', group=group, type=field,
                   name='Ruby (A)', is_deleted=False, sg='4')
        await share_new_management_option(SimpleNamespace(attributes=attributes), doc)
        calls = attributes.update_one.call_args_list
        for call in calls:
            query, update = call.args
            self.assertTrue(call.kwargs['upsert'])
            self.assertEqual(query['name']['$regex'], r'^\s*Ruby\ \(A\)\s*$')
            self.assertNotIn('_id', update['$setOnInsert'])
            self.assertNotEqual(update['$setOnInsert']['uuid'], 'source')
            self.assertEqual(update['$setOnInsert']['sg'], '4')
            self.assertEqual(set(update), {'$setOnInsert'})
        return {(c.args[0]['group'], c.args[0]['type']) for c in calls}

    async def test_gemstones_share_in_every_direction(self):
        targets = {('loose_stone', 'gemstone'), ('single_mounded', 'gemstone'),
                   ('double_mounded', 'primary_gemstone'), ('double_mounded', 'secondary_gemstone')}
        for source in targets:
            self.assertEqual(await self.targets(*source), targets - {source})

    async def test_color_spelling_is_mapped(self):
        self.assertEqual(await self.targets('double_mounded', 'colour'),
                         {('loose_stone', 'color'), ('single_mounded', 'color')})

    async def test_shared_fields_in_every_direction(self):
        groups = {'loose_stone', 'single_mounded', 'double_mounded'}
        for field in ('shape', 'microscopic_obs', 'conclusion'):
            for source in groups:
                self.assertEqual(await self.targets(source, field),
                                 {(g, field) for g in groups - {source}})

    async def test_comments_only_between_loose_and_single(self):
        self.assertEqual(await self.targets('loose_stone', 'comment'), {('single_mounded', 'comment')})
        self.assertEqual(await self.targets('single_mounded', 'comment'), {('loose_stone', 'comment')})
        self.assertEqual(await self.targets('double_mounded', 'comment'), set())

    async def test_unrelated_groups_and_fields_are_untouched(self):
        for source in [('loose_diamond', 'color'), ('navaratna', 'conclusion'),
                       ('single_mounded', 'metal'), ('double_mounded', 'clarity')]:
            self.assertEqual(await self.targets(*source), set())
