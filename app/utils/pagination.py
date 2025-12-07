from typing import Any, Dict

async def paginate_cursor(cursor, page: int = 1, limit: int = 20, count: int | None = None):
    page = max(page, 1)
    limit = max(min(limit, 200), 1)
    skip = (page - 1) * limit
    items = [doc async for doc in cursor.skip(skip).limit(limit)]
    if count is None:
        # caller should provide total when possible for performance
        count = len(items) if page == 1 and len(items) < limit else None
    result = {
        "page": page,
        "limit": limit,
        "data": items,
    }
    if count is not None:
        total_pages = (count + limit - 1) // limit
        result.update({
            "total": count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        })
    return result