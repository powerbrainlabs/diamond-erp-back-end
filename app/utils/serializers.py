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
    """
    Serialize user document, converting ObjectIds and datetimes to JSON-safe types.
    """
    if not doc:
        return doc
    
    d = dict(doc)
    
    # Convert _id to id and string
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    
    # Convert datetime fields
    for dt_key in ["created_at", "updated_at"]:
        if dt_key in d and isinstance(d[dt_key], datetime):
            d[dt_key] = d[dt_key].isoformat()
    
    return d

def dump_job(doc) -> dict:
    """
    Serialize job document, converting ObjectIds and datetimes to JSON-safe types.
    """
    if not doc:
        return doc
    
    d = dict(doc)
    
    # Convert _id to id and string
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    
    # Serialize created_by
    if "created_by" in d and isinstance(d["created_by"], dict):
        created_by = d["created_by"].copy()
        if isinstance(created_by.get("user_id"), ObjectId):
            created_by["user_id"] = str(created_by["user_id"])
        d["created_by"] = created_by
    
    # Serialize assigned_to if present
    if "assigned_to" in d and isinstance(d["assigned_to"], dict):
        assigned_to = d["assigned_to"].copy()
        if isinstance(assigned_to.get("user_id"), ObjectId):
            assigned_to["user_id"] = str(assigned_to["user_id"])
        d["assigned_to"] = assigned_to
    
    # Serialize work_progress (nested structure)
    if "work_progress" in d and isinstance(d["work_progress"], dict):
        work_progress = {}
        for key, value in d["work_progress"].items():
            if isinstance(value, dict):
                progress_item = value.copy()
                # Handle done_by - can be ObjectId or dict with user_id as ObjectId
                if isinstance(progress_item.get("done_by"), ObjectId):
                    progress_item["done_by"] = str(progress_item["done_by"])
                elif isinstance(progress_item.get("done_by"), dict):
                    done_by = progress_item["done_by"].copy()
                    if isinstance(done_by.get("user_id"), ObjectId):
                        done_by["user_id"] = str(done_by["user_id"])
                    progress_item["done_by"] = done_by
                # Convert datetime fields
                for dt_key in ["started_at", "done_at"]:
                    if dt_key in progress_item and isinstance(progress_item[dt_key], datetime):
                        progress_item[dt_key] = progress_item[dt_key].isoformat()
                work_progress[key] = progress_item
            else:
                work_progress[key] = value
        d["work_progress"] = work_progress
    
    # Convert datetime fields
    for dt_key in ["created_at", "updated_at", "received_date", "received_datetime", "expected_delivery_date", "actual_delivery_date"]:
        if dt_key in d and isinstance(d[dt_key], datetime):
            d[dt_key] = d[dt_key].isoformat()
    
    return d

def dump_client(doc):
    if not doc:
        return None
    # Serialize created_by to handle ObjectId in user_id
    created_by = doc.get("created_by", {})
    if created_by and isinstance(created_by.get("user_id"), ObjectId):
        created_by = created_by.copy()
        created_by["user_id"] = str(created_by["user_id"])
    
    return {
        "id": doc["uuid"],
        "name": doc["name"],
        "contact_person": doc.get("contact_person"),
        "email": doc.get("email"),
        "phone": doc.get("phone"),
        "address": doc.get("address"),
        "gst_number": doc.get("gst_number"),
        "notes": doc.get("notes"),
        "created_by": created_by,
        "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at"),
        "updated_at": doc["updated_at"].isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at"),
    }

def dump_manufacturer(doc):
    if not doc:
        return None
    # Serialize created_by to handle ObjectId in user_id
    created_by = doc.get("created_by", {})
    if created_by and isinstance(created_by.get("user_id"), ObjectId):
        created_by = created_by.copy()
        created_by["user_id"] = str(created_by["user_id"])
    
    return {
        "id": doc["uuid"],
        "name": doc["name"],
        "contact_person": doc.get("contact_person"),
        "email": doc.get("email"),
        "phone": doc.get("phone"),
        "address": doc.get("address"),
        "gst_number": doc.get("gst_number"),
        "notes": doc.get("notes"),
        "created_by": created_by,
        "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at"),
        "updated_at": doc["updated_at"].isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at"),
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