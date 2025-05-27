import re
import uuid
from datetime import datetime

from app import db
# from sqlalchemy.dialects.postgresql import UUID # Tidak diperlukan
from sqlalchemy.orm import relationship

class Shipment(db.Model):
    __tablename__ = 'shipments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=False)

    tracking_number = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)

    province = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(255), nullable=True)
    district = db.Column(db.String(255), nullable=True)
    subdistrict = db.Column(db.String(255), nullable=True)
    zip_code = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

    courier = db.Column(db.String(255), nullable=True)
    service = db.Column(db.String(255), nullable=True)
    estimate = db.Column(db.String(255), nullable=True)
    cost = db.Column(db.Float, nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True) 
    

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: Ubah backref menjadi back_populates
    order = relationship("Order", back_populates="shipment") # Perubahan di sini!

    def __repr__(self):
        return f"<Shipment {self.tracking_number} for Order {self.order_id}>"

    @property
    def largest_estimate(self):
        if not self.estimate:
            return None
        matches = re.findall(r'\d+', self.estimate)
        if matches:
            return max(map(int, matches))
        return None