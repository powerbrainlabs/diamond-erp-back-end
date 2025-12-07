from typing import Any
from bson import ObjectId
from datetime import datetime

def oid(value) -> ObjectId:
    return value if isinstance(value, ObjectId) else ObjectId(str(value))

def dump_id(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    return doc

def dump_user(doc) -> dict:
    d = dump_id(dict(doc))
    for k in ("created_at", "updated_at"):
        if k in d and isinstance(d[k], datetime):
            d[k] = d[k]
    return d

def dump_job(doc) -> dict:
    d = dump_id(dict(doc))
    return d

def dump_client(doc):
    if not doc:
        return None
    return {
        "id": doc["uuid"],
        "name": doc["name"],
        "contact_person": doc.get("contact_person"),
        "email": doc.get("email"),
        "phone": doc.get("phone"),
        "address": doc.get("address"),
        "gst_number": doc.get("gst_number"),
        "notes": doc.get("notes"),
        "created_by": doc["created_by"],
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


def serialize_mongo_doc(obj: Any) -> Any:
    """
    Recursively converts MongoDB documents (with ObjectIds, datetimes, etc.)
    into JSON-safe structures (strings, ISO timestamps).
    Works on dicts, lists, and single objects.
    """
    if isinstance(obj, list):
        return [serialize_mongo_doc(i) for i in obj]
    
    elif isinstance(obj, dict):
        new_obj = {}
        for key, value in obj.items():
            if isinstance(value, ObjectId):
                new_obj[key] = str(value)
            elif isinstance(value, datetime):
                new_obj[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                new_obj[key] = serialize_mongo_doc(value)
            else:
                new_obj[key] = value
        return new_obj
    
    else:
        # Direct value (string, int, etc.)
        return obj