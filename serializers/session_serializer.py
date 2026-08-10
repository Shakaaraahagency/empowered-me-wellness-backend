def serialize_class(c):
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "image_url": c.image_url,
        "category": c.category,
        "is_active": c.is_active,
    }


def serialize_session(s, detail=False):
    data = {
        "id": s.id,
        "title": s.title,
        "start_time": s.start_time.isoformat(),
        "end_time": s.end_time.isoformat(),
        "location": s.location,
        "price": str(s.price) if s.price is not None else None,
        "spots_remaining": s.spots_remaining,
        "is_full": s.is_full,
        "status": s.status,
        "image_url": s.image_url,
        "class_name": s.class_.name if s.class_ else None,
        "class_category": s.class_.category if s.class_ else None,
    }
    if detail:
        data["description"] = s.description
        data["capacity"] = s.capacity
    return data
