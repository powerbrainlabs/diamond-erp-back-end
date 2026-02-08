"""Seed default category schemas on first startup."""
import uuid
from datetime import datetime


async def seed_default_category_schemas(db):
    """Create default Diamond and Gemstone certificate schemas if none exist."""
    existing = await db.category_schemas.count_documents({"is_deleted": False})
    if existing > 0:
        return

    now = datetime.utcnow()
    system_author = {"user_id": "system", "name": "System", "email": "system"}

    # ── Fetch existing attribute names to pre-populate dropdown options ──
    async def _get_attr_names(group: str, attr_type: str) -> list:
        docs = await db.attributes.find({
            "group": group, "type": attr_type, "is_deleted": False,
        }).to_list(None)
        return [d["name"] for d in docs]

    # ── Diamond Certificate Schema ───────────────────────────────────
    diamond_fields = [
        {
            "field_id": str(uuid.uuid4()),
            "label": "Category",
            "field_name": "category",
            "field_type": "dropdown",
            "is_required": True,
            "options": await _get_attr_names("diamond", "category"),
            "display_order": 0,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Color",
            "field_name": "color",
            "field_type": "dropdown",
            "is_required": True,
            "options": await _get_attr_names("diamond", "color"),
            "display_order": 1,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Clarity",
            "field_name": "clarity",
            "field_type": "dropdown",
            "is_required": True,
            "options": await _get_attr_names("diamond", "clarity"),
            "display_order": 2,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Cut",
            "field_name": "cut",
            "field_type": "dropdown",
            "is_required": False,
            "options": await _get_attr_names("diamond", "cut"),
            "display_order": 3,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Conclusion",
            "field_name": "conclusion",
            "field_type": "dropdown",
            "is_required": False,
            "options": await _get_attr_names("diamond", "conclusion"),
            "display_order": 4,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Metal Type",
            "field_name": "metal_type",
            "field_type": "dropdown",
            "is_required": False,
            "options": await _get_attr_names("diamond", "metal_type"),
            "display_order": 5,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gross Weight",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Enter weight in gms",
            "display_order": 6,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Diamond Weight",
            "field_name": "diamond_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Enter weight in cts",
            "display_order": 7,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comments",
            "field_type": "textarea",
            "is_required": False,
            "display_order": 8,
        },
    ]

    await db.category_schemas.insert_one({
        "uuid": str(uuid.uuid4()),
        "name": "Diamond Certificate",
        "group": "diamond",
        "description": "Standard diamond certification fields",
        "fields": diamond_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })

    # ── Gemstone Certificate Schema ──────────────────────────────────
    gemstone_fields = [
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gemstone",
            "field_name": "gemstone",
            "field_type": "dropdown",
            "is_required": True,
            "options": await _get_attr_names("gemstone", "gemstone"),
            "display_order": 0,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Category",
            "field_name": "gemstone_category",
            "field_type": "dropdown",
            "is_required": False,
            "options": await _get_attr_names("gemstone", "gemstone_category"),
            "display_order": 1,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Shape",
            "field_name": "gemstone_shape",
            "field_type": "dropdown",
            "is_required": False,
            "options": await _get_attr_names("gemstone", "gemstone_shape"),
            "display_order": 2,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Microscopic Observation",
            "field_name": "microscopic_observation",
            "field_type": "dropdown",
            "is_required": False,
            "options": await _get_attr_names("gemstone", "microscopic_observation"),
            "display_order": 3,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "gemstone_comments",
            "field_type": "textarea",
            "is_required": False,
            "options": await _get_attr_names("gemstone", "gemstone_comments"),
            "display_order": 4,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gross Weight",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Enter weight in gms",
            "display_order": 5,
        },
    ]

    await db.category_schemas.insert_one({
        "uuid": str(uuid.uuid4()),
        "name": "Gemstone Certificate",
        "group": "gemstone",
        "description": "Standard gemstone certification fields",
        "fields": gemstone_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })
