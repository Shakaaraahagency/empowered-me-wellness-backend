from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    user_id = db.Column(GUID(), db.ForeignKey("users.id"), nullable=True)  # nullable = guest checkout

    guest_email = db.Column(db.String(255), nullable=True)

    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    # pending / paid / failed

    stripe_checkout_session_id = db.Column(db.String(255), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship("OrderItem", backref="order", lazy="joined")

    def contact_email(self) -> str:
        if self.user_id and self.user:
            return self.user.email
        return self.guest_email or ""


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    order_id = db.Column(GUID(), db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(GUID(), db.ForeignKey("products.id"), nullable=False)
    price_at_purchase = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship("Product")


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    provider = db.Column(db.String(30), nullable=False, default="stripe")
    provider_ref = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="usd")
    status = db.Column(db.String(20), nullable=False, default="pending")

    # Polymorphic: exactly one of these should be set.
    booking_id = db.Column(GUID(), db.ForeignKey("bookings.id"), nullable=True)
    order_id = db.Column(GUID(), db.ForeignKey("orders.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


from models.user import User  # noqa: E402

Order.user = db.relationship("User", backref="orders")
