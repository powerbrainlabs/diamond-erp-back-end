"""Seed default category schemas and certificate types on first startup."""
import uuid
from datetime import datetime


async def seed_default_attributes(db):
    """Upsert predefined attribute values — runs on every startup, safe to re-run."""

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

    # Seed diamond conclusions for schema groups that load them dynamically from management
    for schema_group in ("single_diamond", "loose_diamond", "navaratna"):
        for conclusion in diamond_conclusions:
            extra = {}
            if conclusion == "Natural Diamond":
                extra = {"sg": "3.52", "hardness": "10"}
            attributes.append({
                "uuid": str(uuid.uuid4()),
                "group": schema_group,
                "type": "conclusion",
                "name": conclusion,
                "is_deleted": False,
                "created_by": system_author,
                "created_at": now,
                "updated_at": now,
                **extra,
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

    # Gemstone-mounted groups: seed primary/secondary gemstone dropdown options.
    # "Natural Diamond" must be present (and correctly cased) so the double_mounded
    # conditional_logic (show_if_value: "Natural Diamond") toggles cut/clarity/colour
    # vs sg/ri/hardness when picked from the dropdown.
    mounted_gemstone_options = ["Natural Diamond", *gemstone_types]
    for schema_group in ("double_mounded", "single_mounded", "loose_stone"):
        for gem_type in ("primary_gemstone", "secondary_gemstone", "gemstone"):
            for gem_name in mounted_gemstone_options:
                attributes.append({
                    "uuid": str(uuid.uuid4()),
                    "group": schema_group,
                    "type": gem_type,
                    "name": gem_name,
                    "is_deleted": False,
                    "created_by": system_author,
                    "created_at": now,
                    "updated_at": now,
                })
        # Also seed metal/shape/microscopic option sets shared across gemstone forms
        for metal in metal_types:
            attributes.append({
                "uuid": str(uuid.uuid4()),
                "group": schema_group,
                "type": "metal",
                "name": metal,
                "is_deleted": False,
                "created_by": system_author,
                "created_at": now,
                "updated_at": now,
            })
        for shape in gemstone_shapes:
            attributes.append({
                "uuid": str(uuid.uuid4()),
                "group": schema_group,
                "type": "shape",
                "name": shape,
                "is_deleted": False,
                "created_by": system_author,
                "created_at": now,
                "updated_at": now,
            })

    for attr in attributes:
        await db.attributes.update_one(
            {"group": attr["group"], "type": attr["type"], "name": attr["name"]},
            {
                "$set": {k: v for k, v in attr.items() if k not in ("created_at", "created_by", "uuid")},
                "$setOnInsert": {
                    "uuid": attr["uuid"],
                    "created_at": attr["created_at"],
                    "created_by": attr["created_by"],
                },
            },
            upsert=True,
        )


async def seed_default_certificate_types(db):
    """Upsert certificate types — runs on every startup, safe to re-run."""
    now = datetime.utcnow()
    system_author = {"user_id": "system", "name": "System", "email": "system"}

    types = [
        {
            "uuid": str(uuid.uuid4()),
            "slug": "single_diamond",
            "name": "Diamond Jewellery",
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
            "name": "Loose Gemstone",
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
            "name": "Single Mounted Gemstone",
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
    for t in types:
        await db.certificate_types.update_one(
            {"slug": t["slug"]},
            {
                "$set": {k: v for k, v in t.items() if k not in ("created_at", "created_by", "uuid")},
                "$setOnInsert": {
                    "uuid": t["uuid"],
                    "created_at": t["created_at"],
                    "created_by": t["created_by"],
                },
            },
            upsert=True,
        )


async def seed_default_category_schemas(db):
    """Upsert category schemas — runs on every startup, safe to re-run."""
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
            "label": "Gross Weight",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Enter gross weight in gms",
            "unit": "gms",
            "display_order": 6,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Diamond Weight",
            "field_name": "diamond_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Enter diamond weight in cts",
            "unit": "cts",
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
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type a comment (max 50 characters)",
            "options": [
                "Excellent quality with superior characteristics and exceptional brilliance",
                "No visible inclusions under 10x magnification, outstanding clarity grade",
                "Minor inclusions visible only under magnification, does not affect brilliance",
                "Exceptional clarity and brilliance with superior cut proportions",
                "Good overall quality with well-defined characteristics and natural origin confirmed",
            ],
            "validation": {"min_length": 1, "max_length": 50},
            "display_order": 9,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Diamond Jewellery Certificate",
        "group": "single_diamond",
        "description": "Jewelry with diamonds (mounted diamond jewelry)",
        "description_template": "One {metal} {category} studded with {diamond_piece} {conclusion} and Colour Stones.",
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
            "label": "Dimension",
            "field_name": "dimension",
            "field_type": "composite",
            "is_required": False,
            "help_text": "Enter length x width x height in millimeters",
            "unit": "mm",
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
            "placeholder": "Hardness",
            "unit": "",
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
            "label": "Weight",
            "field_name": "weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Weight in carats",
            "unit": "cts",
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
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type conclusion",
            "options": ["Natural", "Synthetic", "Treated", "Heat Treated", "Unheated", "No Treatment", "Beryllium Treated", "Glass Filled", "Fracture Filled", "Irradiated", "Coated", "Dyed"],
            "display_order": 8,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comment",
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type a comment (max 50 characters)",
            "options": [
                "Superior cut and polish with excellent light performance and symmetry",
                "Good symmetry and proportions with natural characteristics confirmed",
                "Exceptional quality with well-defined inclusions typical of natural origin",
                "Outstanding brilliance and fire with superior optical performance observed",
                "No fluorescence detected, natural formation confirmed under magnification",
            ],
            "validation": {"min_length": 1, "max_length": 50},
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
            "label": "Dimension",
            "field_name": "dimension",
            "field_type": "composite",
            "is_required": False,
            "help_text": "Enter length x width x height in millimeters",
            "unit": "mm",
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
            "label": "Weight",
            "field_name": "weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Weight in carats",
            "unit": "cts",
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
            "placeholder": "Hardness",
            "unit": "",
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
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type conclusion",
            "options": ["Natural", "Synthetic", "Treated", "Heat Treated", "Unheated", "No Treatment", "Beryllium Treated", "Glass Filled", "Fracture Filled", "Irradiated", "Coated", "Dyed"],
            "display_order": 9,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comment",
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type a comment (max 50 characters)",
            "options": [
                "Unheated, excellent origin with natural inclusions typical of the variety",
                "Heat treated for color enhancement, standard industry practice confirmed",
                "Natural with typical inclusions observed, no clarity enhancement detected",
                "Origin and natural formation confirmed, exceptional color saturation noted",
                "Vivid natural color with no indications of artificial treatment observed",
            ],
            "validation": {"min_length": 1, "max_length": 50},
            "display_order": 10,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Loose Gemstone Certificate",
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
            "placeholder": "Hardness",
            "unit": "",
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
            "label": "Stone Weight",
            "field_name": "stone_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Gemstone weight in carats",
            "unit": "cts",
            "display_order": 8,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gross Weight",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Total weight in grams",
            "unit": "gms",
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
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type conclusion",
            "options": ["Natural", "Synthetic", "Treated", "Heat Treated", "Unheated", "No Treatment", "Beryllium Treated", "Glass Filled", "Fracture Filled", "Irradiated", "Coated", "Dyed"],
            "display_order": 11,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Comments",
            "field_name": "comment",
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type a comment (max 50 characters)",
            "options": [
                "Beautiful color with excellent setting craftsmanship and premium quality stones",
                "Excellent setting with natural gemstone origin confirmed under magnification",
                "Premium quality gemstone with well-defined natural characteristics observed",
                "Superior brilliance with natural inclusions typical of the gemstone variety",
                "Outstanding color saturation with no indications of artificial enhancement",
            ],
            "validation": {"min_length": 1, "max_length": 50},
            "display_order": 12,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Single Mounted Gemstone Certificate",
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
            "label": "Cut",
            "field_name": "cut",
            "field_type": "creatable_select",
            "is_required": False,
            "options": ["Excellent", "Very Good", "Good", "Fair", "Poor"],
            "display_order": 7,
            "conditional_logic": {
                "show_if_field": "primary_gemstone",
                "show_if_value": "Natural Diamond",
            },
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Clarity",
            "field_name": "clarity",
            "field_type": "creatable_select",
            "is_required": False,
            "options": ["FL", "IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2", "I1", "I2", "I3"],
            "display_order": 8,
            "conditional_logic": {
                "show_if_field": "primary_gemstone",
                "show_if_value": "Natural Diamond",
            },
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Colour",
            "field_name": "colour",
            "field_type": "creatable_select",
            "is_required": False,
            "options": ["D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O-Z"],
            "display_order": 9,
            "conditional_logic": {
                "show_if_field": "primary_gemstone",
                "show_if_value": "Natural Diamond",
            },
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Hardness",
            "field_name": "hardness",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Hardness",
            "unit": "",
            "display_order": 7,
            "conditional_logic": {
                "show_if_field": "primary_gemstone",
                "show_if_not_value": "Natural Diamond",
            },
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "SG",
            "field_name": "sg",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Specific gravity",
            "display_order": 8,
            "conditional_logic": {
                "show_if_field": "primary_gemstone",
                "show_if_not_value": "Natural Diamond",
            },
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "RI",
            "field_name": "ri",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Refractive index",
            "display_order": 9,
            "conditional_logic": {
                "show_if_field": "primary_gemstone",
                "show_if_not_value": "Natural Diamond",
            },
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Primary Stone Weight",
            "field_name": "primary_stone_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Primary gemstone weight",
            "unit": "cts",
            "display_order": 10,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Secondary Stone Weight",
            "field_name": "secondary_stone_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Secondary gemstone weight",
            "unit": "cts",
            "display_order": 11,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Gross Weight",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Total weight in grams",
            "unit": "gms",
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
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type conclusion",
            "options": ["Natural", "Synthetic", "Treated", "Heat Treated", "Unheated", "No Treatment", "Beryllium Treated", "Glass Filled", "Fracture Filled", "Irradiated", "Coated", "Dyed"],
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
            "label": "Gross Weight",
            "field_name": "gross_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Total weight in grams",
            "unit": "gms",
            "display_order": 5,
        },
        {
            "field_id": str(uuid.uuid4()),
            "label": "Diamond Weight",
            "field_name": "diamond_weight",
            "field_type": "text",
            "is_required": False,
            "placeholder": "Diamond weight in carats",
            "unit": "cts",
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
            "field_type": "creatable_select",
            "is_required": False,
            "placeholder": "Select or type a comment (max 50 characters)",
            "options": [
                "Traditional Navaratna setting with nine auspicious gems of natural origin",
                "Premium quality Navaratna with all nine gemstones confirmed as natural",
                "Astrological quality gemstones with natural characteristics confirmed under magnification",
                "All nine stones are natural and untreated, excellent astrological properties",
                "Superior craftsmanship with natural gemstones, ideal for astrological purposes",
            ],
            "validation": {"min_length": 1, "max_length": 50},
            "display_order": 8,
        },
    ]

    schemas.append({
        "uuid": str(uuid.uuid4()),
        "name": "Navaratna Certificate",
        "group": "navaratna",
        "description": "Nine-gem jewelry (traditional Navaratna)",
        "description_template": "One NR {category} studded with {diamond_piece} Natural Diamond and Colour Stones.",
        "fields": navaratna_fields,
        "is_active": True,
        "is_deleted": False,
        "created_by": system_author,
        "created_at": now,
        "updated_at": now,
    })

    for s in schemas:
        await db.category_schemas.update_one(
            {"group": s["group"]},
            {
                "$set": {k: v for k, v in s.items() if k not in ("created_at", "created_by", "uuid")},
                "$setOnInsert": {
                    "uuid": s["uuid"],
                    "created_at": s["created_at"],
                    "created_by": s["created_by"],
                },
            },
            upsert=True,
        )
