from typing import Any
from bson import ObjectId
from datetime import datetime
from .minio_helpers import get_presigned_url

def oid(value) -> ObjectId:
    return value if isinstance(value, ObjectId) else ObjectId(str(value))

def dump_id(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    return doc

def get_permissions_for_role(role: str) -> list:
    from ..schemas.auth import ROLE_PERMISSIONS
    return ROLE_PERMISSIONS.get(role, [])

def dump_user(doc) -> dict:
    d = dump_id(dict(doc))
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
    d["permissions"] = get_permissions_for_role(d.get("role", ""))
    if "features" not in d:
        d["features"] = []
    return d

def dump_job(doc) -> dict:
    d = dump_id(dict(doc))
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
    return d

def dump_client(doc):
    if not doc:
        return None
    
    # Handle created_by field - can be string or dict with ObjectId
    created_by = doc.get("created_by")
    if isinstance(created_by, dict):
        # Convert ObjectId to string if present
        created_by = {
            "user_id": str(created_by.get("user_id")) if created_by.get("user_id") else None,
            "name": created_by.get("name"),
            "email": created_by.get("email"),
        }
    
    brand_logo_url = doc.get("brand_logo_url")
    rear_logo_url = doc.get("rear_logo_url")

    def _logo_signed_url(url):
        if not url:
            return None
        parts = url.split("/", 1)
        if len(parts) == 2:
            return get_presigned_url(parts[0], parts[1])
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
        "brand_logo_url": brand_logo_url,
        "rear_logo_url": rear_logo_url,
        "brand_logo_signed_url": _logo_signed_url(brand_logo_url),
        "rear_logo_signed_url": _logo_signed_url(rear_logo_url),
        "created_by": created_by,
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }

def dump_manufacturer(doc):
    if not doc:
        return None

    return {
        "id": doc["uuid"],
        "uuid": doc["uuid"],
        "name": doc["name"],
        "contact_person": doc.get("contact_person"),
        "email": doc.get("email"),
        "phone": doc.get("phone"),
        "address": doc.get("address"),
        "notes": doc.get("notes"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def dump_qc_report(doc) -> dict:
    d = dump_id(dict(doc))
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
    return d


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
