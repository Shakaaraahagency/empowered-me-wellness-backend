def serialize_order(o):
    return {
        "id": o.id,
        "status": o.status,
        "total_amount": str(o.total_amount),
        "created_at": o.created_at.isoformat(),
        "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        "contact_email": o.contact_email(),
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product.name,
                "price_at_purchase": str(item.price_at_purchase),
            }
            for item in o.items
        ],
    }
