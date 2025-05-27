import uuid
from datetime import datetime

from app import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

class ProductImage(db.Model):
    __tablename__ = 'product_images'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    
    name = db.Column(db.String(255), nullable=False)
    is_thumbnail = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    product = relationship('Product', back_populates='images')

    def __repr__(self):
        return f"<ProductImage {self.name} (Thumbnail: {self.is_thumbnail})>"
