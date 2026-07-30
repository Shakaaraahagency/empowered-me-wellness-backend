def serialize_post(p, detail=False):
    data = {
        "id": p.id,
        "title": p.title,
        "slug": p.slug,
        "excerpt": p.excerpt,
        "cover_image_url": p.cover_image_url,
        "published_at": p.published_at.isoformat() if p.published_at else None,
    }
    if detail:
        data["content"] = p.content
        data["seo_title"] = p.seo_title
        data["seo_description"] = p.seo_description
    return data


def serialize_post_admin(p):
    data = serialize_post(p, detail=True)
    data["status"] = p.status
    data["created_at"] = p.created_at.isoformat()
    data["updated_at"] = p.updated_at.isoformat()
    return data
