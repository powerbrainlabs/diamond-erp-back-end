"""Propagate newly added management options to related gemstone certificates."""
import re
import uuid


GROUPS = ('loose_stone', 'single_mounded', 'double_mounded')
SHARED_FIELDS = {
    'gemstone': {
        'loose_stone': ('gemstone',),
        'single_mounded': ('gemstone',),
        'double_mounded': ('primary_gemstone', 'secondary_gemstone'),
    },
    'color': {
        'loose_stone': ('color',),
        'single_mounded': ('color',),
        'double_mounded': ('colour',),
    },
    **{field: {group: (field,) for group in GROUPS}
       for field in ('shape', 'microscopic_obs', 'conclusion')},
    'comment': {
        'loose_stone': ('comment',),
        'single_mounded': ('comment',),
    },
}


async def share_new_management_option(db, attribute: dict) -> None:
    """Add missing peer options without overwriting existing names or metadata."""
    group, field = attribute['group'], attribute['type']
    targets = next((mapping for mapping in SHARED_FIELDS.values()
                    if field in mapping.get(group, ())), {})
    for target_group, target_fields in targets.items():
        for target_field in target_fields:
            if (target_group, target_field) == (group, field):
                continue
            copy = {key: value for key, value in attribute.items() if key != '_id'}
            copy.update(uuid=str(uuid.uuid4()), group=target_group, type=target_field)
            await db.attributes.update_one(
                {
                    'group': target_group,
                    'type': target_field,
                    'name': {'$regex': r'^\s*' + re.escape(attribute['name'].strip()) + r'\s*$',
                             '$options': 'i'},
                    'is_deleted': False,
                },
                {'$setOnInsert': copy},
                upsert=True,
            )
