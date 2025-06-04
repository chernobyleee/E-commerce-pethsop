# app/models/order.py
from app import db
from datetime import datetime
import uuid

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    invoice_number = db.Column(db.String(100), unique=True, nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False) 
    shipping_address = db.Column(db.Text, nullable=False)
    payment_status = db.Column(db.String(50), default='unpaid', nullable=False) 
    payment_method = db.Column(db.String(50), nullable=False)
    resi_number = db.Column(db.String(100), nullable=True) 
    payment_token = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True) # Ini adalah delivered yang diupdate manual/otomatis
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancellation_requested_at = db.Column(db.DateTime, nullable=True) 
    # Kolom BARU
    delivered_api_at = db.Column(db.DateTime, nullable=True) # Tanggal status 'DELIVERED' terakhir dari API tracking
    received_at = db.Column(db.DateTime, nullable=True) # Tanggal ketika customer klik 'Produk Diterima' atau otomatis

    # Hubungan dengan User (melalui backref 'customer' dari User model)
    # user = db.relationship('User', back_populates='orders') # Ini opsional, bisa pakai backref saja

    # RELASI KE ORDERDETAIL - PERBAIKAN DI SINI
    order_details = db.relationship('OrderDetail', back_populates='order', lazy=True, cascade="all, delete-orphan")
    
    # RELASI KE PAYMENTS - PASTIKAN BACK_POPULATES ADA DI MODEL PAYMENT
    payments = db.relationship('Payment', back_populates='order', lazy=True, cascade="all, delete-orphan")
    
    # RELASI KE SHIPMENT - PASTIKAN BACK_POPULATES ADA DI MODEL SHIPMENT
    shipment = db.relationship('Shipment', back_populates='order', lazy=True, uselist=False) # uselist=False karena 1 order hanya punya 1 shipment

    def __repr__(self):
        return f'<Order {self.invoice_number}>'
    
    def can_be_cancelled_by_customer(self):
        """
        Cek apakah order bisa dibatalkan oleh customer setelah pembayaran.
        Bisa dibatalkan jika statusnya 'processing' (sudah dibayar, menunggu dikirim oleh admin)
        DAN belum ada nomor resi di shipment (atau shipment.shipped_at belum diisi).
        """
        # Pastikan self.shipment ada sebelum mengakses tracking_number atau shipped_at
        shipment_exists_and_not_shipped = True
        if self.shipment:
            # Jika ada shipment, cek apakah sudah dikirim (berdasarkan tracking_number atau shipped_at di shipment)
            # Asumsi jika shipment.shipped_at diisi, berarti sudah dikirim.
            # Atau, jika Anda hanya mengandalkan tracking_number:
            if self.shipment.tracking_number or self.shipment.shipped_at:
                shipment_exists_and_not_shipped = False
        else:
            # Jika tidak ada record shipment sama sekali, anggap belum dikirim (tergantung alur bisnis Anda)
            # Namun, biasanya jika sudah 'processing', record shipment sudah dibuat walau resi kosong.
            # Jika shipment selalu dibuat saat order, maka kondisi `not self.shipment` mungkin tidak relevan di sini.
            pass # Asumsi jika tidak ada shipment, berarti belum dikirim.

        return self.status == 'processing' and shipment_exists_and_not_shipped

    def can_be_cancelled_before_payment(self):
        """
        Cek apakah order bisa dibatalkan sebelum pembayaran atau saat pembayaran pending.
        """
        return self.status in ['pending', 'pending_payment'] and self.payment_status == 'unpaid'
    
    
    def can_request_cancellation(self):
        """
        Menentukan apakah pelanggan bisa meminta pembatalan.
        Contoh: Bisa jika statusnya 'pending_payment', 'paid', atau 'processing'
                 DAN belum 'shipped', 'completed', atau 'cancelled'.
        """
        return self.status in ['pending_payment', 'paid', 'processing'] and \
               self.status not in ['shipped', 'completed', 'cancelled']
