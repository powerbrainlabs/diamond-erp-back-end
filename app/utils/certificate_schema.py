async def legacy_mounted_schema(db, doc, cache):
    """Resolve the legacy type spelling on reads, without rewriting certificates.

    Explicit schema references always win. Cache per request, including misses,
    so listing or printing a batch only performs one compatibility lookup.
    """
    if doc.get("type") != "single_mounted" or any(
        doc.get(key) for key in ("schema_uuid", "category_uuid", "category_id")
    ):
        return None
    group = "single_mounded"
    if group not in cache:
        cache[group] = await db.category_schemas.find_one({
            "group": group, "is_deleted": False, "is_active": True,
        })
    return cache[group]
