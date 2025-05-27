import uuid
from datetime import datetime

from slugify import slugify
from app import db
from sqlalchemy.orm import relationship
from sqlalchemy import event

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)

    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship ke Product
    products = relationship('Product', back_populates='category', lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"

    def generate_slug(self):
        self.slug = slugify(self.name)

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()

# Optional: event listener untuk otomatis generate slug sebelum insert/update
@event.listens_for(Category, 'before_insert')
@event.listens_for(Category, 'before_update')
def receive_before_insert_update(mapper, connection, target):
    if not target.slug and target.name:
        target.generate_slug()
