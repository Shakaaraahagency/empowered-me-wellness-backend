def serialize_booking(b):
    return {
        "id": b.id,
        "status": b.status,
        "created_at": b.created_at.isoformat(),
        "cancelled_at": b.cancelled_at.isoformat() if b.cancelled_at else None,
        "contact_name": b.contact_name(),
        "contact_email": b.contact_email(),
        "session": {
            "id": b.session.id,
            "title": b.session.title,
            "start_time": b.session.start_time.isoformat(),
            "location": b.session.location,
        },
    }
