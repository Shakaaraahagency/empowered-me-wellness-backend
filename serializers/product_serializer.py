def serialize_product(p, detail=False):
    data = {
        "id": p.id,
        "name": p.name,
        "price": str(p.price),
        "cover_image_url": p.cover_image_url,
        "category": p.category,
    }
    if detail:
        data["description"] = p.description
        data["file_path"] = p.file_path
        data["is_active"] = p.is_active
    return data
