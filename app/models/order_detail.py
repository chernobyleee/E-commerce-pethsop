import uuid
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class OrderDetail(db.Model):
    __tablename__ = 'order_details'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)


    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship('Order', back_populates='order_details')
    product = relationship('Product', back_populates='order_details')

    def __repr__(self):
        return f"<OrderDetail order_id={self.order_id} product_id={self.product_id} quantity={self.quantity}>"
