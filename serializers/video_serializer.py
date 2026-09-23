def serialize_video(v):
    return {
        "id": v.id,
        "title": v.title,
        "description": v.description,
        "youtube_url": v.youtube_url,
        "youtube_id": v.youtube_id,
        "category": v.category,
        "published_at": v.published_at.isoformat() if v.published_at else None,
    }


def serialize_video_admin(v):
    data = serialize_video(v)
    data["status"] = v.status
    data["created_at"] = v.created_at.isoformat()
    data["updated_at"] = v.updated_at.isoformat()
    return data
