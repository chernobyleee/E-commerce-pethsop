# app/routes/midtrans.py
from flask import Blueprint, request, jsonify, current_app
from app import db
from datetime import datetime
from app.services.midtrans import MidtransService
from app.models.order import Order

midtrans_bp = Blueprint('midtrans', __name__, url_prefix='/midtrans')

def get_midtrans_service():
    server_key = current_app.config.get('MIDTRANS_SERVER_KEY')
    client_key = current_app.config.get('MIDTRANS_CLIENT_KEY')
    is_production = current_app.config.get('MIDTRANS_IS_PRODUCTION', False)
    return MidtransService(server_key, client_key, is_production)

@midtrans_bp.route('/notification', methods=['POST'])
def notification():
    current_app.logger.info("=== MIDTRANS NOTIFICATION RECEIVED ===")
    current_app.logger.info(f"Request Headers: {dict(request.headers)}")
    current_app.logger.info(f"Request Method: {request.method}")
    current_app.logger.info(f"Content-Type: {request.content_type}")

    # Log raw data
    raw_data = request.get_data(as_text=True)
    current_app.logger.info(f"Raw Request Data: {raw_data}")

    midtrans_service_instance = get_midtrans_service()

    notification_data = request.json
    if not notification_data:
        current_app.logger.warning("No JSON data received in notification")
        try:
            notification_data = request.get_json(force=True)
        except:
            current_app.logger.error("Failed to parse JSON from notification")
            return jsonify({"message": "Invalid JSON"}), 400

    current_app.logger.info(f"Parsed Notification Data: {notification_data}")

    processed_data = midtrans_service_instance.handle_notification(notification_data)

    if "error" in processed_data:
        current_app.logger.error(f"Error handling Midtrans notification: {processed_data['error']}")
        return jsonify({"message": processed_data['error']}), 500

    order_id = processed_data.get('order_id')
    payment_status = processed_data.get('payment_status')

    if not order_id or not payment_status:
        current_app.logger.error(f"Processed data incomplete: order_id={order_id}, payment_status={payment_status}")
        return jsonify({"message": "Incomplete processed notification data"}), 500

    current_app.logger.info(f"Looking for order with invoice_number: {order_id}")

    order = Order.query.filter_by(invoice_number=order_id).first()

    if not order:
        current_app.logger.error(f"Order with invoice number {order_id} not found")
        all_orders = Order.query.all()
        current_app.logger.debug(f"Available invoice numbers: {[o.invoice_number for o in all_orders[-5:]]}")
        return jsonify({"message": "Order not found"}), 404

    current_app.logger.info(f"Found order ID: {order.id}, Current status: {order.status}, Payment status: {order.payment_status}")

    if payment_status == "success":
        if order.payment_status != 'paid':
            order.payment_status = 'paid'
            order.status = 'processing'
            order.paid_at = datetime.utcnow()
            current_app.logger.info(f"Order {order.invoice_number} updated to PAID")
        else:
            current_app.logger.info(f"Order {order.invoice_number} already paid")
    elif payment_status == "pending":
        if order.payment_status != 'pending':
            order.payment_status = 'pending'
            order.status = 'pending_payment'
            current_app.logger.info(f"Order {order.invoice_number} updated to PENDING")
    elif payment_status == "failed":
        if order.payment_status != 'failed' and order.status != 'cancelled':
            order.payment_status = 'failed'
            order.status = 'cancelled'
            current_app.logger.info(f"Order {order.invoice_number} updated to FAILED")
    elif payment_status == "challenge":
        if order.payment_status != 'challenge':
            order.payment_status = 'challenge'
            order.status = 'on_hold'
            current_app.logger.info(f"Order {order.invoice_number} updated to CHALLENGE")

    try:
        db.session.commit()
        current_app.logger.info(f"Database commit successful for order {order.invoice_number}")
        current_app.logger.info("=== NOTIFICATION PROCESSING COMPLETED ===")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing order status: {e}", exc_info=True)
        return jsonify({"message": "Failed to update order status"}), 500

    return jsonify({"message": "Notification processed successfully"}), 200