from ..db.database import get_db

START_AT = 1001

async def next_job_number() -> str:
    db = await get_db()
    doc = await db.counters.find_one_and_update(
        {"_id": "job_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = doc.get("seq")
    if seq is None:
        await db.counters.update_one({"_id": "job_number"}, {"$set": {"seq": START_AT}}, upsert=True)
        seq = START_AT
    return f"DIA{seq}"