# app/models/cart.py
import uuid
from datetime import datetime

from app import db
# from sqlalchemy.orm import relationship # Tidak perlu import di sini jika sudah ada di db

class Cart(db.Model):
    __tablename__ = 'carts'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship ke User dan Product
    # back_populates="cart_items" harus sesuai dengan nama relasi di User model
    user = db.relationship("User", back_populates="cart_items") # Perubahan di sini!
    
    # back_populates="carts" di Product model (jika ada) harus sesuai dengan nama relasi di Product model
    product = db.relationship("Product", back_populates="carts") # Asumsi ini sudah benar di Product model

    def __repr__(self):
        return f"<Cart {self.user_id} - {self.product_id} - Qty: {self.quantity}>"

    @staticmethod
    def available_items():
        # Import Product dari tempat yang benar
        from app.models.product import Product 
        return Cart.query.join(Cart.product).filter(
            Product.stock > 0,
            Product.deleted_at.is_(None)
        )

    @staticmethod
    def unavailable_items():
        # Import Product dari tempat yang benar
        from app.models.product import Product
        return Cart.query.join(Cart.product).filter(
            (Product.stock == 0) | (Product.deleted_at.isnot(None))
        )