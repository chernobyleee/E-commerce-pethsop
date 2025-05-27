# app/routes/orders.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from flask_login import current_user, login_required
from datetime import datetime, timedelta
import uuid
from decimal import Decimal

# Import models
from app.models.order import Order
from app.models.order_detail import OrderDetail
from app.models.cart import Cart
from app.models.shipment import Shipment
from app.models.product import Product
from app import db # Import db instance dari app/__init__.py

# Import services
from app.services.midtrans import MidtransService # Pastikan ini path yang benar ke MidtransService Anda
from app.services.shipping_service import ShippingService
from app.services.location_service import LocationService 

# Import decorators
from app.decorators import customer_required # <--- TAMBAHKAN INI

orders_bp = Blueprint('orders', __name__)

def get_midtrans_service():
    server_key = current_app.config.get('MIDTRANS_SERVER_KEY')
    client_key = current_app.config.get('MIDTRANS_CLIENT_KEY')
    is_production = current_app.config.get('MIDTRANS_IS_PRODUCTION', False)
    if not server_key or not client_key:
        current_app.logger.error("Midtrans keys tidak ditemukan di config!")
    return MidtransService(server_key, client_key, is_production)

def get_shipping_service():
    if not hasattr(current_app, 'shipping_service'):
        # Asumsi ShippingService Anda mengelola config dengan benar
        current_app.shipping_service = ShippingService(current_app.config) 
    return current_app.shipping_service

def get_location_service():
    if not hasattr(current_app, 'location_service'):
        current_app.location_service = LocationService(current_app.config.get('KOMSHIP_API_KEY')) 
    return current_app.location_service

# --- Checkout Route ---
@orders_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@customer_required # <--- TAMBAHKAN INI
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash('Keranjang belanja kosong', 'warning')
        return redirect(url_for('main.home'))

    total_price = Decimal(0)
    for item in cart_items:
        total_price += item.product.price * item.quantity 

    total_weight_grams = sum(item.product.weight * item.quantity for item in cart_items)
    total_weight_kg = total_weight_grams / 1000.0 if total_weight_grams > 0 else 0.1

    selected_shipping_option = None
    if 'selected_shipping' in session:
        selected_shipping_option = session['selected_shipping']

    if request.method == 'POST':
        receiver_name = request.form.get('receiver_name')
        receiver_phone = request.form.get('receiver_phone')
        receiver_address = request.form.get('receiver_address')
        receiver_destination_id = request.form.get('receiver_destination_id')
        province_name = request.form.get('province_name')
        city_name = request.form.get('city_name')
        district_name = request.form.get('district_name')
        subdistrict_name = request.form.get('subdistrict_name')
        zip_code = request.form.get('zip_code')

        courier_code = request.form.get('courier_code') 
        courier_service = request.form.get('courier_service') 
        courier_estimate = request.form.get('courier_estimate')
        
        try:
            courier_cost_str = request.form.get('courier_cost', '0')
            courier_cost = Decimal(courier_cost_str)
        except Exception as e:
            current_app.logger.error(f"Error converting courier_cost to Decimal: {e}")
            flash('Terjadi kesalahan dengan biaya pengiriman. Mohon coba lagi.', 'danger')
            return redirect(url_for('orders.checkout'))

        if not all([receiver_name, receiver_phone, receiver_address, receiver_destination_id, courier_code, courier_service, courier_estimate, courier_cost is not None]):
            flash('Mohon lengkapi semua data pengiriman dan pilih kurir.', 'danger')
            return redirect(url_for('orders.checkout'))

        try:
            now = datetime.now() 
            invoice_number = f"INV-{now.strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"

            new_order = Order(
                user_id=current_user.id,
                invoice_number=invoice_number,
                total=total_price + courier_cost,
                status='pending', # Initial status is 'pending'
                shipping_address=f"{receiver_address}, {subdistrict_name}, {district_name}, {city_name}, {province_name}, {zip_code}",
                payment_method='Belum Dibayar', 
            )
            
            db.session.add(new_order)
            db.session.flush() # Flush to get new_order.id

            for item in cart_items:
                order_detail = OrderDetail(
                    order_id=new_order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=Decimal(str(item.product.price)),
                    weight=item.product.weight,
                )
                db.session.add(order_detail)

                product = Product.query.get(item.product_id)
                if product:
                    product.stock -= item.quantity
                    if product.stock < 0:
                        product.stock = 0
                    db.session.add(product)
            
            shipment = Shipment(
                order_id=new_order.id,
                name=receiver_name,
                phone=receiver_phone,
                province=province_name,
                city=city_name,
                district=district_name,
                subdistrict=subdistrict_name, 
                zip_code=zip_code,
                address=receiver_address,
                courier=courier_code, 
                service=courier_service,
                estimate=courier_estimate,
                cost=courier_cost,
            )
            db.session.add(shipment)

            Cart.query.filter_by(user_id=current_user.id).delete()

            db.session.commit()

            flash('Pesanan berhasil dibuat! Lanjutkan ke pembayaran.', 'success')
            return redirect(url_for('orders.payment', order_id=new_order.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error during checkout: {str(e)}", exc_info=True)
            flash('Terjadi kesalahan saat membuat pesanan. Mohon coba lagi.', 'danger')
            return redirect(url_for('orders.checkout'))

    return render_template('orders/checkout.html',
                           title='Checkout',
                           cart_items=cart_items,
                           total_price=total_price,
                           total_weight_kg=total_weight_kg,
                           selected_shipping=selected_shipping_option)

# --- API Location and Shipping ---
@orders_bp.route('/api/search-location', methods=['GET'])
@login_required
@customer_required # <--- TAMBAHKAN INI (opsional, tergantung apakah admin boleh nyari lokasi)
def api_search_location():
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return jsonify({"success": False, "error": "Keyword is required."}), 400

    location_service_instance = get_location_service() 
    response = location_service_instance.search_destination(keyword)
    return jsonify(response)

@orders_bp.route('/api/calculate-shipping', methods=['POST'])
@login_required
@customer_required # <--- TAMBAHKAN INI (opsional, tergantung apakah admin boleh menghitung ongkir)
def api_calculate_shipping():
    try:
        data = request.get_json()
        receiver_destination_id = data.get('receiver_destination_id')
        total_weight_kg = data.get('total_weight_kg')
        total_item_value = data.get('total_item_value')

        if not all([receiver_destination_id, total_weight_kg, total_item_value is not None]):
            return jsonify({"success": False, "error": "Missing required parameters."}), 400

        origin_id = current_app.config.get('SHOP_ORIGIN_REGION_ID')
        if not origin_id:
            current_app.logger.error("SHOP_ORIGIN_REGION_ID is not configured in current_app.config.")
            return jsonify({"success": False, "error": "Shop origin not configured."}), 500

        shipping_service_instance = get_shipping_service() 
        response = shipping_service_instance.calculate_shipping_cost(
            origin_id=origin_id,
            destination_id=receiver_destination_id,
            weight=total_weight_kg,
            item_value=total_item_value
        )
        return jsonify(response)
    except Exception as e:
        current_app.logger.error(f"Error in /api/calculate-shipping: {str(e)}")
        return jsonify({"success": False, "error": "Terjadi kesalahan saat menghitung ongkir."}), 500


# --- MODIFIKASI: Route untuk halaman pembayaran (Hanya merender template) ---
@orders_bp.route('/payment/<string:order_id>')
@login_required
@customer_required # <--- TAMBAHKAN INI
def payment(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    # Periksa status order. Hanya izinkan akses jika 'pending' atau 'pending_payment'
    # Jika sudah 'paid', 'completed', atau 'cancelled', redirect ke halaman detail order
    if order.status not in ['pending', 'pending_payment']:
        flash('Pesanan ini tidak lagi dalam status menunggu pembayaran. Status saat ini: {}.'.format(order.status.replace('_', ' ').title()), 'info')
        return redirect(url_for('orders.order_detail', order_id=order.id))

    midtrans_service_instance = get_midtrans_service()
    
    # Kita tidak lagi meng-generate snap_token di sini.
    # JavaScript di payment.html akan memanggil endpoint API untuk itu.
    
    return render_template('orders/payment.html',
                           title='Pembayaran',
                           order=order,
                           client_key=current_app.config['MIDTRANS_CLIENT_KEY'],
                           midtrans_service=midtrans_service_instance) # midtrans_service_instance digunakan untuk snap_js_url

# --- TAMBAHKAN: Endpoint API baru untuk mendapatkan snap_token ---
@orders_bp.route('/api/get-snap-token/<string:order_id>', methods=['GET'])
@login_required
@customer_required
def api_get_snap_token(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()

    if not order or order.status not in ['pending', 'pending_payment']:
        current_app.logger.warning(f"API Get Snap Token: Order {order_id} not found or not in valid status for user {current_user.id}")
        return jsonify({'error': 'Order not found or not in pending payment status'}), 404

    # --- BAGIAN REGENERASI INVOICE_NUMBER DIHAPUS ---
    # Logika untuk mengubah order.invoice_number di sini telah dihilangkan.
    # Invoice number di database akan tetap seperti saat pertama kali dibuat.
    current_app.logger.info(f"API Get Snap Token: Processing order {order.id} with original invoice_number {order.invoice_number}")

    midtrans_service_instance = get_midtrans_service()
    order_details = OrderDetail.query.filter_by(order_id=order.id).all()
    shipment = Shipment.query.filter_by(order_id=order.id).first()

    shipping_fee = Decimal(0)
    if shipment and shipment.cost is not None: # Pastikan shipment.cost tidak None
        try:
            shipping_fee = Decimal(shipment.cost)
        except Exception as e:
            current_app.logger.error(f"Error converting shipment.cost to Decimal for order {order.id}: {e}")
            shipping_fee = Decimal(0) # Fallback jika konversi gagal
    
    current_app.logger.debug(f"API Get Snap Token: Order ID: {order.id}, Invoice: {order.invoice_number}, Shipping Fee: {shipping_fee}")

    # Panggil service. Service akan menangani pembuatan ID unik untuk Midtrans.
    transaction_result = midtrans_service_instance.generate_transaction_token(
        order=order, # Mengirim objek order dengan invoice_number asli
        customer=current_user,
        items=order_details,
        shipping_fee=shipping_fee
    )

    if "error" in transaction_result:
        error_message = transaction_result['error']
        # Log invoice_number asli, bukan yang mungkin sudah diubah (jika kode lama masih ada)
        current_app.logger.error(f"Midtrans token generation failed for order {order.id} (invoice: {order.invoice_number}): {error_message}")
        return jsonify({'error': error_message}), 500
    else:
        snap_token = transaction_result['token']
        # Opsional: Simpan snap_token ke order jika Anda ingin melacaknya
        # Namun, jangan commit perubahan invoice_number di sini.
        order.payment_token = snap_token # Simpan token ke order
        try:
            db.session.commit() # Commit hanya untuk payment_token
            current_app.logger.info(f"Snap token generated and saved for order {order.id}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to save snap_token for order {order.id}: {e}")
            # Tidak perlu return error ke client karena token sudah berhasil dibuat
        return jsonify({'snap_token': snap_token})    

@orders_bp.route('/midtrans-notification', methods=['POST'])
def midtrans_notification():
    current_app.logger.info("=== MIDTRANS NOTIFICATION RECEIVED ===")
    # ... (logging request headers, method, content-type, raw_data tetap sama)
    raw_data = request.get_data(as_text=True)
    current_app.logger.info(f"Raw Request Data: {raw_data}")

    notification_data = request.json
    if not notification_data:
        current_app.logger.warning("No JSON data received in notification")
        try:
            notification_data = request.get_json(force=True) # Coba parse manual
        except Exception as e:
            current_app.logger.error(f"Failed to parse JSON from notification: {e}")
            return jsonify({"message": "Invalid JSON"}), 400
    
    current_app.logger.info(f"Parsed Notification Data: {notification_data}")

    # Dapatkan order_id dari Midtrans (yang sekarang berisi sufiks unik)
    midtrans_order_id_with_suffix = notification_data.get('order_id')
    if not midtrans_order_id_with_suffix:
        current_app.logger.error("order_id missing from Midtrans notification payload.")
        return jsonify({"message": "order_id is missing from notification"}), 400

    # --- EKSTRAK INVOICE_NUMBER ASLI ---
    # Asumsi format: ORIGINAL_INVOICE_NUMBER-SUFFIX
    # Contoh: "INV-20240527-XYZ-1234-abcd" menjadi "INV-20240527-XYZ-1234"
    try:
        parts = midtrans_order_id_with_suffix.split('-')
        if len(parts) > 1: # Pastikan ada tanda '-' untuk di-split
            # Ambil semua bagian kecuali yang terakhir (sufiks)
            original_invoice_number = '-'.join(parts[:-1])
        else:
            # Jika tidak ada '-', anggap itu adalah invoice asli (fallback, seharusnya tidak terjadi dengan implementasi baru)
            original_invoice_number = midtrans_order_id_with_suffix
            current_app.logger.warning(f"Midtrans order_id '{midtrans_order_id_with_suffix}' does not seem to have a suffix. Using as is.")
    except Exception as e:
        current_app.logger.error(f"Error parsing original_invoice_number from '{midtrans_order_id_with_suffix}': {e}")
        original_invoice_number = midtrans_order_id_with_suffix # Fallback

    current_app.logger.info(f"Notification for Midtrans Order ID: {midtrans_order_id_with_suffix}. Extracted original invoice_number for DB lookup: {original_invoice_number}")

    midtrans_service_instance = get_midtrans_service()
    # Validasi signature key tetap menggunakan order_id yang dikirim Midtrans (dengan sufiks)
    processed_data = midtrans_service_instance.handle_notification(notification_data)

    if "error" in processed_data:
        current_app.logger.error(f"Error handling Midtrans notification (validation/processing): {processed_data['error']}")
        return jsonify({"message": processed_data['error']}), 500

    # `processed_data['order_id']` akan sama dengan `midtrans_order_id_with_suffix`
    # Kita sudah mengekstrak `original_invoice_number` untuk lookup DB.
    payment_status_from_midtrans = processed_data.get('payment_status')

    if not payment_status_from_midtrans: # Pastikan payment_status ada setelah diproses
        current_app.logger.error(f"Processed data incomplete: payment_status missing. Original order_id: {midtrans_order_id_with_suffix}")
        return jsonify({"message": "Incomplete processed notification data (payment_status missing)"}), 500

    current_app.logger.info(f"Looking for order in DB with original invoice_number: {original_invoice_number}")
    order = Order.query.filter_by(invoice_number=original_invoice_number).first()

    if not order:
        current_app.logger.error(f"Order with original invoice_number '{original_invoice_number}' not found in database.")
        # Tambahkan debugging: cari semua order untuk debugging
        all_orders_sample = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        current_app.logger.debug(f"Sample of recent invoice numbers in DB: {[o.invoice_number for o in all_orders_sample]}")
        return jsonify({"message": "Order not found in DB"}), 404

    current_app.logger.info(f"Found order in DB: ID {order.id}, Current status: {order.status}, Payment status: {order.payment_status}")

    # Update status logic (gunakan payment_status_from_midtrans)
    if payment_status_from_midtrans == "success":
        if order.payment_status != 'paid': # Hanya update jika belum paid
            order.payment_status = 'paid'
            order.status = 'processing' # Atau status lain yang sesuai setelah pembayaran
            order.paid_at = datetime.utcnow()
            current_app.logger.info(f"Order {order.invoice_number} (DB ID: {order.id}) updated to PAID and PROCESSING.")
        else:
            current_app.logger.info(f"Order {order.invoice_number} (DB ID: {order.id}) already paid. No status change.")
    elif payment_status_from_midtrans == "pending":
        if order.payment_status != 'pending' and order.payment_status != 'paid': # Jangan override jika sudah paid
            order.payment_status = 'pending'
            order.status = 'pending_payment' # Atau status lain yang sesuai
            current_app.logger.info(f"Order {order.invoice_number} (DB ID: {order.id}) updated to PENDING.")
    elif payment_status_from_midtrans == "failed":
        if order.payment_status != 'failed' and order.status != 'cancelled' and order.payment_status != 'paid': # Jangan override jika sudah paid
            order.payment_status = 'failed'
            order.status = 'cancelled' # Atau status lain yang sesuai
            current_app.logger.info(f"Order {order.invoice_number} (DB ID: {order.id}) updated to FAILED/CANCELLED.")
    elif payment_status_from_midtrans == "challenge":
         if order.payment_status != 'challenge' and order.payment_status != 'paid': # Jangan override jika sudah paid
            order.payment_status = 'challenge'
            order.status = 'on_hold' # Atau status lain yang sesuai
            current_app.logger.info(f"Order {order.invoice_number} (DB ID: {order.id}) updated to CHALLENGE/ON_HOLD.")
    # Tambahkan kondisi lain jika perlu (expire, deny, dll.)

    try:
        db.session.commit()
        current_app.logger.info(f"Database commit successful for order {order.invoice_number} (DB ID: {order.id})")
        current_app.logger.info("=== NOTIFICATION PROCESSING COMPLETED ===")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error committing order status for {order.invoice_number} (DB ID: {order.id}): {e}", exc_info=True)
        return jsonify({"message": "Failed to update order status in DB"}), 500

    return jsonify({"message": "Notification processed successfully"}), 200

# --- Order List Route ---
@orders_bp.route('/orders')
@login_required
@customer_required # <--- TAMBAHKAN INI
def order_list():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Pastikan pagination bekerja dengan baik
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('orders/order_list.html',
                           title='Daftar Pesanan',
                           orders=orders)

# --- Order Detail Route ---
@orders_bp.route('/order/<string:order_id>')
@login_required
@customer_required # <--- TAMBAHKAN INI
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    
    order_details = OrderDetail.query.filter_by(order_id=order.id).all()
    
    subtotal = Decimal(0)
    for detail in order_details:
        price = Decimal(str(detail.price)) if not isinstance(detail.price, Decimal) else detail.price
        quantity = Decimal(str(detail.quantity)) if not isinstance(detail.quantity, Decimal) else detail.quantity
        subtotal += price * quantity
            
    shipment = order.shipment 

    tracking_history = None # Ubah dari [] ke None untuk indikator awal
    tracking_error = None
    last_manifest_status = None
    last_manifest_date = None

    show_receive_button = False
    delivered_status_found = False
    
    if shipment and shipment.tracking_number and shipment.courier: 
        shipping_service_instance = get_shipping_service()
        current_app.logger.debug(f"Attempting to track AWB: {shipment.tracking_number} for courier: {shipment.courier}")

        track_result = shipping_service_instance.get_airway_bill_history(
            courier_code=shipment.courier, 
            airway_bill_number=shipment.tracking_number 
        )
        
        if track_result['success']:
            tracking_history = track_result['data']
            current_app.logger.info(f"Successfully retrieved tracking history for AWB {shipment.tracking_number}.")

            if tracking_history and tracking_history.get('manifest'):
                # Iterate in reverse to find the latest 'DELIVERED' status
                for item in reversed(tracking_history['manifest']):
                    desc = item.get('manifest_description', '').upper()
                    if "DELIVERED" in desc or "TELAH DITERIMA" in desc or "SUDAH DITERIMA" in desc:
                        delivered_status_found = True
                        last_manifest_status = item.get('manifest_description')
                        try:
                            date_str = item.get('manifest_date')
                            time_str = item.get('manifest_time')
                            if date_str and time_str:
                                last_manifest_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        except ValueError:
                            current_app.logger.warning(f"Could not parse manifest date/time for order {order.id}")
                            last_manifest_date = None
                        break # Stop after finding the latest delivered status
            
            # Update delivered_api_at if a new delivered status is found from API
            if delivered_status_found and last_manifest_date:
                if order.delivered_api_at is None or last_manifest_date > order.delivered_api_at:
                    order.delivered_api_at = last_manifest_date
                    db.session.add(order)
                    try:
                        db.session.commit()
                        current_app.logger.info(f"Updated delivered_api_at for order {order.id} to {order.delivered_api_at}")
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error updating delivered_api_at for order {order.id}: {e}")

            # Show receive button if order is 'shipped' AND delivered status found from API AND not yet marked as delivered by user
            if order.status == 'shipped' and delivered_status_found and order.delivered_at is None:
                show_receive_button = True

        else:
            tracking_error = f"Gagal mengambil riwayat pelacakan: {track_result.get('error', 'Unknown error')}"
            current_app.logger.error(f"Tracking error for order {order.id}: {tracking_error}")

    return render_template('orders/order_detail.html',
                           title='Detail Pesanan',
                           order=order,
                           order_details=order_details,
                           subtotal=subtotal,
                           shipment=shipment,
                           tracking_history=tracking_history, # Bisa None, atau dict
                           tracking_error=tracking_error,
                           show_receive_button=show_receive_button)

# --- Route untuk menandai pesanan diterima ---
@orders_bp.route('/order/<string:order_id>/mark_as_received', methods=['POST'])
@login_required
@customer_required # <--- TAMBAHKAN INI
def mark_as_received(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if order.status == 'shipped' and order.delivered_at is None:
        order.status = 'completed'
        order.payment_status = 'paid' 
        order.delivered_at = datetime.utcnow()
        try:
            db.session.commit()
            flash('Pesanan berhasil ditandai sebagai diterima!', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error marking order {order.id} as received: {e}")
            flash('Terjadi kesalahan saat menandai pesanan sebagai diterima.', 'danger')
    else:
        flash('Pesanan tidak dapat ditandai sebagai diterima.', 'warning')
    
    return redirect(url_for('orders.order_detail', order_id=order.id))