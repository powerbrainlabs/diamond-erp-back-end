from ..db.database import get_db

START_AT = 1001

async def next_job_number(organization_id: str | None = None) -> str:
    db = await get_db()
    counter_id = f"job_number:{organization_id or 'global'}"
    doc = await db.counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc.get("seq")
    if seq is None:
        await db.counters.update_one({"_id": counter_id}, {"$set": {"seq": START_AT}}, upsert=True)
        seq = START_AT
    return f"DIA{seq}"
