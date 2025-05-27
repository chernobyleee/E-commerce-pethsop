# app/tasks.py
from app import db # Import db dari app/__init__.py
from app.models.order import Order
from datetime import datetime, timedelta
from flask import current_app

def check_delivered_orders(app):
    with app.app_context(): # Pastikan ini dijalankan dalam application context
        current_app.logger.info("Running scheduled job: check_delivered_orders")
        
        # Cari pesanan yang statusnya 'shipped', sudah ada delivered_api_at,
        # belum received_at, dan sudah lewat 1 hari dari delivered_api_at
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        
        orders_to_complete = Order.query.filter(
            Order.status == 'shipped',
            Order.delivered_api_at.isnot(None),
            Order.received_at.is_(None), # Belum dikonfirmasi manual
            Order.delivered_api_at <= one_day_ago
        ).all()

        for order in orders_to_complete:
            order.status = 'completed'
            order.received_at = datetime.utcnow()
            order.delivered_at = datetime.utcnow() # Update delivered_at juga
            current_app.logger.info(f"Order {order.invoice_number} automatically completed.")
            
        try:
            db.session.commit()
            current_app.logger.info(f"Successfully auto-completed {len(orders_to_complete)} orders.")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error during auto-completion of orders: {e}")