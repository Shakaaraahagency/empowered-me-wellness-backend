def serialize_product(p, detail=False):
    data = {
        "id": p.id,
        "name": p.name,
        "price": str(p.price),
        "cover_image_url": p.cover_image_url,
        "category": p.category,
        "is_coming_soon": p.is_coming_soon,
        "release_date": p.release_date,
    }
    if detail:
        data["description"] = p.description
        data["file_path"] = p.file_path
        data["is_active"] = p.is_active
        # Show how many people are waiting for this coming-soon product
        if p.is_coming_soon and hasattr(p, "notifications"):
            data["notify_count"] = p.notifications.count()
        else:
            data["notify_count"] = 0
    return data

