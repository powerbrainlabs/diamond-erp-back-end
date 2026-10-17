"""Keep reference properties consistent across existing gemstone options."""
import re
from datetime import datetime


GEMSTONE_FIELDS = ('gemstone', 'primary_gemstone', 'secondary_gemstone', 'gemstone_type')
PROPERTY_FIELDS = ('sg', 'ri', 'hardness')


async def sync_gemstone_properties(db, attribute: dict, changes: dict) -> None:
    """Copy only supplied properties; never rename or create category options."""
    if attribute.get('type') not in GEMSTONE_FIELDS:
        return
    properties = {key: changes[key] for key in PROPERTY_FIELDS if key in changes}
    name = attribute.get('name', '').strip()
    if not properties or not name:
        return

    await db.attributes.update_many(
        {
            'type': {'$in': list(GEMSTONE_FIELDS)},
            'name': {'$regex': r'^\s*' + re.escape(name) + r'\s*$', '$options': 'i'},
            'is_deleted': False,
        },
        {'$set': {**properties, 'updated_at': datetime.utcnow()}},
    )
