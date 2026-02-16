"""Seed default category schemas and certificate types on first startup."""
import uuid
from datetime import datetime


async def seed_default_attributes(db):
    """Seed predefined attribute values for certificate dropdowns."""
    existing = await db.attributes.count_documents({"is_deleted": False})
    if existing > 0:
        return  # Already seeded

    now = datetime.utcnow()
    system_author = {"user_id": "system", "name": "System", "email": "system"}

    # Diamond attributes
    diamond_colors = ["D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O-Z"]
    diamond_clarity = ["FL", "IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2", "I1", "I2", "I3"]
    diamond_cut = ["Excellent", "Very Good", "Good", "Fair", "Poor"]
    diamond_categories = ["Jewelry", "Loose Diamond", "Pendant", "Ring", "Earrings", "Bracelet", "Necklace"]
    metal_types = ["Gold 14K", "Gold 18K", "Gold 22K", "Gold 24K", "White Gold 14K", "White Gold 18K", "Platinum", "Silver"]
    diamond_conclusions = ["Natural Diamond", "Lab Grown Diamond", "Treated Diamond", "Natural Colored Diamond"]

    # Gemstone attributes
    gemstone_types = ["Ruby", "Sapphire", "Emerald", "Pearl", "Coral", "Cat's Eye", "Hessonite", "Blue Sapphire", "Yellow Sapphire"]
    gemstone_shapes = ["Round", "Oval", "Cushion", "Princess", "Emerald", "Pear", "Marquise", "Heart", "Asscher", "Radiant"]
    gemstone_categories = ["Natural", "Synthetic", "Treated", "Enhanced"]
    microscopic_observations = ["Inclusions", "Clean", "Minor Inclusions", "Eye Clean", "Visible Inclusions"]

    # Navaratna stones (9 gems)
    navaratna_stones = ["Ruby", "Pearl", "Coral", "Emerald", "Yellow Sapphire", "Diamond", "Blue Sapphire", "Hessonite", "Cat's Eye"]

    attributes = []

    # Diamond attributes
    for color in diamond_colors:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "color",
            "name": color,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    for clarity in diamond_clarity:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "clarity",
            "name": clarity,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    for cut in diamond_cut:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "cut",
            "name": cut,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    for category in diamond_categories:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "category",
            "name": category,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    for metal in metal_types:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "metal_type",
            "name": metal,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    for conclusion in diamond_conclusions:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "conclusion",
            "name": conclusion,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    # Gemstone attributes
    for gemstone in gemstone_types:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "gemstone",
            "type": "gemstone",
            "name": gemstone,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    for shape in gemstone_shapes:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "gemstone",
            "type": "gemstone_shape",
            "name": shape,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    for category in gemstone_categories:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "gemstone",
            "type": "gemstone_category",
            "name": category,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    for observation in microscopic_observations:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "gemstone",
            "type": "microscopic_observation",
            "name": observation,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    # Navaratna attributes
    for stone in navaratna_stones:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "navaratna",
            "type": "stone_type",
            "name": stone,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    # Also add metal types for gemstone and navaratna groups
    for metal in metal_types:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "gemstone",
            "type": "metal_type",
            "name": metal,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "navaratna",
            "type": "metal_type",
            "name": metal,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        })

    await db.attributes.insert_many(attributes)


async def seed_default_certificate_types(db):
    """Create comprehensive certificate types matching old hr-admin-gac system."""
    existing = await db.certificate_types.count_documents({"is_deleted": False})
    if existing > 0:
        return

    now = datetime.utcnow()
    system_author = {"user_id": "system", "name": "System", "email": "system"}

    types = [
        {
            "uuid": str(uuid.uuid4()),
            "slug": "single_diamond",
            "name": "Single Diamond",
            "description": "Jewelry with diamonds (mounted)",
            "icon": "diamond",
            "display_order": 0,
            "has_photo": True,
            "has_logo": True,
            "has_rear_logo": True,
            "is_active": True,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        },
        {
            "uuid": str(uuid.uuid4()),
            "slug": "loose_diamond",
            "name": "Loose Diamond",
            "description": "Unmounted diamond certification",
            "icon": "gem",
            "display_order": 1,
            "has_photo": True,
            "has_logo": True,
            "has_rear_logo": True,
            "is_active": True,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        },
        {
            "uuid": str(uuid.uuid4()),
            "slug": "loose_stone",
            "name": "Loose Stone",
            "description": "Unmounted gemstone certification",
            "icon": "gem",
            "display_order": 2,
            "has_photo": True,
            "has_logo": True,
            "has_rear_logo": True,
            "is_active": True,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        },
        {
            "uuid": str(uuid.uuid4()),
            "slug": "single_mounded",
            "name": "Single Mounded",
            "description": "Single gemstone in setting",
            "icon": "gem",
            "display_order": 3,
            "has_photo": True,
            "has_logo": True,
            "has_rear_logo": True,
            "is_active": True,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        },
        {
            "uuid": str(uuid.uuid4()),
            "slug": "double_mounded",
            "name": "Double Mounded",
            "description": "Two gemstones in setting",
            "icon": "gem",
            "display_order": 4,
            "has_photo": True,
            "has_logo": True,
            "has_rear_logo": True,
            "is_active": True,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        },
        {
            "uuid": str(uuid.uuid4()),
            "slug": "navaratna",
            "name": "Navaratna",
            "description": "Nine-gem jewelry (traditional)",
            "icon": "sparkles",
            "display_order": 5,
            "has_photo": True,
            "has_logo": True,
            "has_rear_logo": True,
            "is_active": True,
            "is_deleted": False,
            "created_by": system_author,
            "created_at": now,
            "updated_at": now,
        },
    ]
    await db.certificate_types.insert_many(types)


async def seed_default_category_schemas(db):
    """Create comprehensive certificate schemas matching old hr-admin-gac system."""
    existing = await db.category_schemas.count_documents({"is_deleted": False})
    if existing > 0:
        return

    now = datetime.utcnow()
    system_author = {"user_id": "system", "name": "System", "email": "system"}

    # Helper to fetch attribute names (returns empty list if no attributes exist yet)
    async def _get_attr_names(group: str, attr_type: str) -> list:
        docs = await db.attributes.find({
            "group": group, "type": attr_type, "is_deleted": False,
        }).to_list(None)
        return [d["name"] for d in docs]

    schemas = []

    # ═══════════════════════════════════════════════════════════════
    # 1. SINGLE DIAMOND (Jewelry with diamonds - mounted)
    # ═══════════════════════════════════════════════════════════════
    single_diamond_fields = [
        {
            "field_id": str(uuid.uuid4()),
            "label": "Category",
            "field_name": "category",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 0,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Metal Type",
            "field_name": "metal",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 1,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Cut",
            "field_name": "cut",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 2,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Clarity",
            "field_name": "clarity",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 3,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Color",
            "field_name": "color",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 4,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Conclusion",
            "field_name": "conclusion",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 5,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gross Weight (gms)",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Enter gross weight in gms",
            "display_order": 6,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Diamond Weight (cts)",
            "field_name": "diamond_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Enter diamond weight in cts",
            "display_order": 7,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Diamond Piece",
            "field_name": "diamond_piece",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Number of diamond pieces",
            "display_order": 8,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comment",
            "field_type": "textarea",
            "is_required": False,
            "placeholder": "Additional comments or observations",
            "display_order": 9,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Single Diamond Certificate",
        "group": "single_diamond",
        "description": "Jewelry with diamonds (mounted diamond jewelry)",
        "description_template": "One {metal} {category} Studded with {diamond_piece} {conclusion}.",
        "fields": single_diamond_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })

    # ═══════════════════════════════════════════════════════════════
    # 2. LOOSE DIAMOND (Unmounted diamond)
    # ═══════════════════════════════════════════════════════════════
    loose_diamond_fields = [
        {
            "field_id": str(uuid.uuid4()),
            "label": "Dimension (mm)",
            "field_name": "dimension",
            "field_type": "composite",
            "is_required": False,
            "help_text": "Enter length x width x height in millimeters",
            "sub_fields": [
                {
                    "field_name": "length",
                    "name": "Length",
                    "field_type": "text",
                    "is_required": False,
                    "placeholder": "e.g., 5.2",
                    "display_order": 0,
                },
                {
                    "field_name": "width",
                    "name": "Width",
                    "field_type": "text",
                    "is_required": False,
                    "placeholder": "e.g., 5.1",
                    "display_order": 1,
                },
                {
                    "field_name": "height",
                    "name": "Height/Depth",
                    "field_type": "text",
                    "is_required": False,
                    "placeholder": "e.g., 3.2",
                    "display_order": 2,
                },
            ],
            "display_order": 0,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Shape",
            "field_name": "shape",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 1,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Hardness",
            "field_name": "hardness",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Mohs hardness scale",
            "display_order": 2,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Clarity",
            "field_name": "clarity",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 3,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Color",
            "field_name": "color",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 4,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Weight (cts)",
            "field_name": "weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Weight in carats",
            "display_order": 5,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "SG",
            "field_name": "sg",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Specific gravity",
            "display_order": 6,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Microscopic Obs",
            "field_name": "microscopic_obs",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 7,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Conclusion",
            "field_name": "conclusion",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Final conclusion",
            "display_order": 8,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comment",
            "field_type": "textarea",
            "is_required": False,
            "placeholder": "Additional comments",
            "display_order": 9,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Loose Diamond Certificate",
        "group": "loose_diamond",
        "description": "Unmounted diamond certification",
        "description_template": "One {shape} shaped {conclusion} weighing {weight}.",
        "fields": loose_diamond_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })

    # ═══════════════════════════════════════════════════════════════
    # 3. LOOSE STONE (Unmounted gemstone)
    # ═══════════════════════════════════════════════════════════════
    loose_stone_fields = [
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gemstone",
            "field_name": "gemstone",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 0,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Dimension (mm)",
            "field_name": "dimension",
            "field_type": "composite",
            "is_required": False,
            "help_text": "Enter length x width x height in millimeters",
            "sub_fields": [
                {
                    "field_name": "length",
                    "name": "Length",
                    "field_type": "text",
                    "is_required": False,
                    "placeholder": "e.g., 5.2",
                    "display_order": 0,
                },
                {
                    "field_name": "width",
                    "name": "Width",
                    "field_type": "text",
                    "is_required": False,
                    "placeholder": "e.g., 5.1",
                    "display_order": 1,
                },
                {
                    "field_name": "height",
                    "name": "Height/Depth",
                    "field_type": "text",
                    "is_required": False,
                    "placeholder": "e.g., 3.2",
                    "display_order": 2,
                },
            ],
            "display_order": 1,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Shape",
            "field_name": "shape",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 2,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Weight (cts)",
            "field_name": "weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Weight in carats",
            "display_order": 3,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Color",
            "field_name": "color",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Stone color",
            "display_order": 4,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Hardness",
            "field_name": "hardness",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Mohs hardness",
            "display_order": 5,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "SG",
            "field_name": "sg",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Specific gravity",
            "display_order": 6,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "RI",
            "field_name": "ri",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Refractive index",
            "display_order": 7,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Microscopic Obs",
            "field_name": "microscopic_obs",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 8,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Conclusion",
            "field_name": "conclusion",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Final conclusion",
            "display_order": 9,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comment",
            "field_type": "textarea",
            "is_required": False,
            "placeholder": "Additional comments",
            "display_order": 10,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Loose Stone Certificate",
        "group": "loose_stone",
        "description": "Unmounted gemstone certification",
        "description_template": "One {shape} shaped {gemstone} weighing {weight}.",
        "fields": loose_stone_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })

    # ═══════════════════════════════════════════════════════════════
    # 4. SINGLE MOUNDED (Single gemstone in setting)
    # ═══════════════════════════════════════════════════════════════
    single_mounded_fields = [
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gemstone",
            "field_name": "gemstone",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 0,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Category",
            "field_name": "category",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 1,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Metal Type",
            "field_name": "metal",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 2,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gemstone Piece",
            "field_name": "gemstone_piece",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Number of gemstone pieces",
            "display_order": 3,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Shape",
            "field_name": "shape",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 4,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Hardness",
            "field_name": "hardness",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Mohs hardness",
            "display_order": 5,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "SG",
            "field_name": "sg",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Specific gravity",
            "display_order": 6,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "RI",
            "field_name": "ri",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Refractive index",
            "display_order": 7,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Stone Weight (cts)",
            "field_name": "stone_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Gemstone weight in carats",
            "display_order": 8,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gross Weight (gms)",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Total weight in grams",
            "display_order": 9,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Microscopic Obs",
            "field_name": "microscopic_obs",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 10,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Conclusion",
            "field_name": "conclusion",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Final conclusion",
            "display_order": 11,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comment",
            "field_type": "textarea",
            "is_required": False,
            "placeholder": "Additional comments",
            "display_order": 12,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Single Mounded Certificate",
        "group": "single_mounded",
        "description": "Single gemstone in setting",
        "description_template": "One {metal} {category} studded with {gemstone_piece} {gemstone}.",
        "fields": single_mounded_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })

    # ═══════════════════════════════════════════════════════════════
    # 5. DOUBLE MOUNDED (Two gemstones in setting)
    # ═══════════════════════════════════════════════════════════════
    double_mounded_fields = [
        {
            "field_id": str(uuid.uuid4()),
            "label": "Primary Gemstone",
            "field_name": "primary_gemstone",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 0,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Secondary Gemstone",
            "field_name": "secondary_gemstone",
            "field_type": "creatable_select",
            "is_required": True,
            "options": [],
            "display_order": 1,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Category",
            "field_name": "category",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 2,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Metal Type",
            "field_name": "metal",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 3,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Primary Gemstone Piece",
            "field_name": "primary_gemstone_piece",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Number of primary gemstone pieces",
            "display_order": 4,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Secondary Gemstone Piece",
            "field_name": "secondary_gemstone_piece",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Number of secondary gemstone pieces",
            "display_order": 5,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Shape",
            "field_name": "shape",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 6,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Hardness",
            "field_name": "hardness",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Mohs hardness",
            "display_order": 7,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "SG",
            "field_name": "sg",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Specific gravity",
            "display_order": 8,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "RI",
            "field_name": "ri",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Refractive index",
            "display_order": 9,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Primary Stone Wt",
            "field_name": "primary_stone_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Primary gemstone weight",
            "display_order": 10,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Secondary Stone Wt",
            "field_name": "secondary_stone_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Secondary gemstone weight",
            "display_order": 11,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gross Weight (gms)",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Total weight in grams",
            "display_order": 12,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Microscopic Obs",
            "field_name": "microscopic_obs",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 13,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Conclusion",
            "field_name": "conclusion",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Final conclusion",
            "display_order": 14,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Double Mounded Certificate",
        "group": "double_mounded",
        "description": "Two gemstones in setting",
        "description_template": "One {metal} {category} studded with {primary_gemstone_piece} {primary_gemstone} and {secondary_gemstone_piece} {secondary_gemstone}.",
        "fields": double_mounded_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })

    # ═══════════════════════════════════════════════════════════════
    # 6. NAVARATNA (9-gem jewelry - traditional)
    # ═══════════════════════════════════════════════════════════════
    navaratna_fields = [
        {
            "field_id": str(uuid.uuid4()),
            "label": "Category",
            "field_name": "category",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 0,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Cut",
            "field_name": "cut",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 1,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Clarity",
            "field_name": "clarity",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 2,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Color",
            "field_name": "color",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 3,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Conclusion",
            "field_name": "conclusion",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 4,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gross Weight (gms)",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Total weight in grams",
            "display_order": 5,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Diamond Weight (cts)",
            "field_name": "diamond_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Diamond weight in carats",
            "display_order": 6,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Diamond Piece",
            "field_name": "diamond_piece",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Number of diamond pieces",
            "display_order": 7,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comment",
            "field_type": "textarea",
            "is_required": False,
            "placeholder": "Additional comments",
            "display_order": 8,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Navaratna Certificate",
        "group": "navaratna",
        "description": "Nine-gem jewelry (traditional Navaratna)",
        "description_template": "One Navaratna {category} set in {metal} with nine precious gemstones.",
        "fields": navaratna_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })

    # Insert all schemas
    await db.category_schemas.insert_many(schemas)
