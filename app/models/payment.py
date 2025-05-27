# app/models/payment.py (Contoh, jika Anda punya)
import uuid
from datetime import datetime

from app import db

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = db.Column(db.String(36), db.ForeignKey('orders.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(50), nullable=False) # e.g., credit_card, bank_transfer
    status = db.Column(db.String(50), default='pending', nullable=False) # e.g., pending, completed, failed

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    order = db.relationship('Order', back_populates='payments') # Perubahan di sini!

    def __repr__(self):
        return f"<Payment {self.id} for Order {self.order_id} - {self.amount}>"