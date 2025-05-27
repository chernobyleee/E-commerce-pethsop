# app/models/product.py
import uuid
from datetime import datetime

from slugify import slugify
from app import db
from sqlalchemy.orm import relationship
from sqlalchemy import event

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    category_id = db.Column(db.String(36), db.ForeignKey('categories.id'), nullable=True) # Tambahkan ini jika ada kategori
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False) # <<< REKOMENDASI: Gunakan Numeric untuk harga
    weight = db.Column(db.Integer, nullable=True) # Tetap Integer jika berat dalam gram bulat
    stock = db.Column(db.Integer, nullable=False, default=0)
    image_url = db.Column(db.String(255), nullable=True) # Untuk menyimpan path/URL gambar
    
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship('Category', back_populates='products') # Tambahkan ini jika ada kategori
    # ... (relasi lainnya seperti images, carts, order_details, added_by_users) ...
    images = relationship('ProductImage', back_populates='product', lazy=True)
    carts = relationship('Cart', back_populates='product', lazy=True) 
    order_details = relationship('OrderDetail', back_populates='product', lazy=True)
    added_by_users = relationship('User', secondary='carts', viewonly=True) 


    def __repr__(self):
        return f"<Product {self.name} - Stock: {self.stock}>"

    def generate_slug(self):
        self.slug = slugify(self.name)

    @property
    def thumbnail_image(self):
        return next((img for img in self.images if img.is_thumbnail), None)

    @property
    def images_without_thumbnail(self):
        return [img for img in self.images if not img.is_thumbnail]

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()

# Optional: event listener untuk otomatis generate slug sebelum insert/update
@event.listens_for(Product, 'before_insert')
@event.listens_for(Product, 'before_update')
def receive_before_insert_update_product(mapper, connection, target):
    if not target.slug and target.name:
        target.generate_slug()