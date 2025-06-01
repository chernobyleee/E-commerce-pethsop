from flask import Blueprint, render_template, request, redirect, url_for,current_app, flash
from flask_login import current_user
from app.models.product import Product
from app.models.category import Category
from app.models.product_image import ProductImage
from app.models.order import Order
main_bp = Blueprint('main', __name__)


def get_shipping_service_instance():
    # Cara ini akan membuat instance baru setiap kali dipanggil jika tidak di-cache di current_app
    # Sebaiknya gunakan pola yang sama seperti di orders.py jika memungkinkan
    # (misal, menyimpan instance di current_app)
    # from app.services.shipping_service import ShippingService # Import di dalam fungsi jika perlu
    # return ShippingService(current_app.config)

    # Mengikuti pola dari orders.py Anda:
    if not hasattr(current_app, 'shipping_service_main'): # Gunakan nama berbeda agar tidak konflik jika sudah ada di orders.py
        from app.services.shipping_service import ShippingService
        current_app.shipping_service_main = ShippingService(current_app.config)
    return current_app.shipping_service_main

@main_bp.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    # Get featured products (you can customize the query based on your needs)
    products = Product.query.filter_by(deleted_at=None).order_by(Product.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Get all categories for the navbar
    categories = Category.query.filter_by(deleted_at=None).all()
    
    return render_template('main/home.html', 
                          title='Home', 
                          products=products,
                          categories=categories)

@main_bp.route('/product/<string:slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug, deleted_at=None).first_or_404()
    product_images = ProductImage.query.filter_by(product_id=product.id).all()
    
    # Get thumbnail image
    thumbnail = next((img for img in product_images if img.is_thumbnail), None)
    if not thumbnail and product_images:
        thumbnail = product_images[0]
    
    related_products = Product.query.filter_by(
        category_id=product.category_id, 
        deleted_at=None
    ).filter(Product.id != product.id).limit(4).all()
    
    return render_template('products/product_detail.html',
                          title=product.name,
                          product=product,
                          product_images=product_images,
                          thumbnail=thumbnail,
                          related_products=related_products)

@main_bp.route('/category/<string:slug>')
def category_products(slug):
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    category = Category.query.filter_by(slug=slug, deleted_at=None).first_or_404()
    products = Product.query.filter_by(
        category_id=category.id, 
        deleted_at=None
    ).paginate(page=page, per_page=per_page)
    
    categories = Category.query.filter_by(deleted_at=None).all()
    
    return render_template('main/category_products.html',
                          title=category.name,
                          category=category,
                          products=products,
                          categories=categories)

@main_bp.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    products = Product.query.filter(
        Product.name.ilike(f'%{query}%'),
        Product.deleted_at == None
    ).paginate(page=page, per_page=per_page)
    
    categories = Category.query.filter_by(deleted_at=None).all()
    
    return render_template('main/search_results.html',
                          title=f'Hasil Pencarian: {query}',
                          query=query,
                          products=products,
                          categories=categories)
    
# --- MODIFIKASI ROUTE UNTUK TRACKING ORDER (AWB & INVOICE WAJIB) ---
@main_bp.route('/track-order', methods=['GET', 'POST'])
def track_order_page():
    tracking_result = None
    internal_order_status = None
    error_message = None
    
    # Simpan input pengguna untuk ditampilkan kembali di form
    invoice_query = request.form.get('invoice_number_input', '').strip()
    awb_query = request.form.get('airway_bill_input', '').strip()
    courier_query = request.form.get('courier_code', '').strip().lower()

    if request.method == 'POST':
        if not awb_query or not courier_query or not invoice_query:
            flash('Mohon masukkan Nomor Invoice, Nomor Resi, dan pilih Kurir.', 'danger')
        else:
            current_app.logger.info(f"TRACKING: Attempting to find order by INVOICE: {invoice_query} and AWB: {awb_query} for COURIER: {courier_query}")
            order = Order.query.filter_by(invoice_number=invoice_query).first()

            if order:
                # Isi data internal order terlebih dahulu
                internal_order_status = {
                    'invoice_number': order.invoice_number,
                    'status': order.status.replace('_', ' ').title(),
                    'payment_status': order.payment_status.title(),
                    'created_at': order.created_at.strftime('%d %B %Y, %H:%M') if order.created_at else 'N/A',
                    'paid_at': order.paid_at.strftime('%d %B %Y, %H:%M') if order.paid_at else 'Belum Dibayar',
                    'customer_name': order.customer.name if order.customer else 'N/A',
                    'awb_from_db': None, # Nomor resi dari database
                    'courier_from_db': None # Kurir dari database
                }

                if order.shipment and order.shipment.tracking_number and order.shipment.courier:
                    internal_order_status['awb_from_db'] = order.shipment.tracking_number
                    internal_order_status['courier_from_db'] = order.shipment.courier.upper()

                    # Validasi AWB yang dimasukkan pengguna dengan yang ada di database
                    if order.shipment.tracking_number.lower() != awb_query.lower():
                        error_message = f"Nomor Resi (AWB) yang Anda masukkan ({awb_query}) tidak cocok dengan nomor resi yang terdaftar untuk Invoice {invoice_query}."
                        flash(error_message, 'danger')
                    # Validasi Kurir yang dipilih pengguna dengan yang ada di database (jika perlu, atau biarkan API yang menentukan)
                    # Untuk saat ini, kita akan tetap menggunakan courier_query dari input pengguna untuk API call
                    elif order.shipment.courier.lower() != courier_query:
                        # Anda bisa memilih untuk error atau tetap lanjut dengan courier_query
                        flash(f"Kurir yang dipilih ({courier_query.upper()}) berbeda dengan kurir terdaftar ({order.shipment.courier.upper()}) untuk pesanan ini. Melanjutkan pelacakan dengan kurir yang dipilih.", 'warning')
                        # Lanjutkan ke tracking eksternal
                        shipping_service = get_shipping_service_instance()
                        api_response = shipping_service.get_airway_bill_history(
                            courier_code=courier_query, # Gunakan kurir dari input form
                            airway_bill_number=awb_query # Gunakan AWB dari input form
                        )
                        if api_response and api_response.get('success'):
                            tracking_result = api_response.get('data')
                            if not tracking_result or not tracking_result.get('manifest'):
                                error_message = "Data pelacakan ditemukan, tetapi tidak ada riwayat manifest dari ekspedisi."
                                tracking_result = None 
                        else:
                            error_message = api_response.get('error', 'Gagal melacak nomor resi dari ekspedisi.')
                            flash(error_message, 'warning')
                    else: # AWB dan Kurir cocok (atau kurir tidak divalidasi ketat)
                        shipping_service = get_shipping_service_instance()
                        api_response = shipping_service.get_airway_bill_history(
                            courier_code=courier_query, # Gunakan kurir dari input form
                            airway_bill_number=awb_query # Gunakan AWB dari input form
                        )
                        if api_response and api_response.get('success'):
                            tracking_result = api_response.get('data')
                            if not tracking_result or not tracking_result.get('manifest'):
                                error_message = "Data pelacakan ditemukan, tetapi tidak ada riwayat manifest dari ekspedisi."
                                tracking_result = None 
                        else:
                            error_message = api_response.get('error', 'Gagal melacak nomor resi dari ekspedisi.')
                            flash(error_message, 'warning')
                else: # Order ditemukan tapi belum ada resi di database
                    internal_order_status['shipping_info'] = "Nomor resi belum terdaftar untuk pesanan ini di sistem kami."
                    flash("Nomor resi belum terdaftar untuk pesanan ini di sistem kami. Tidak dapat melakukan pelacakan eksternal.", 'info')
            else:
                error_message = f"Nomor Invoice '{invoice_query}' tidak ditemukan."
                flash(error_message, 'danger')
                
    supported_couriers = {
        "jne": "JNE", "pos": "POS Indonesia", "tiki": "TIKI",
        "sicepat": "SiCepat", "jnt": "J&T Express", "anteraja": "AnterAja",
        "wahana": "Wahana", "ninja": "Ninja Xpress", "lion": "Lion Parcel",
        "ide": "ID Express", "sap": "SAP Express"
    }

    return render_template('main/track_order.html', 
                           title='Lacak Pesanan Anda',
                           tracking_result=tracking_result,
                           internal_order_status=internal_order_status,
                           error_message=error_message,
                           invoice_query=invoice_query, # Kirim nilai query terakhir
                           awb_query=awb_query,         # Kirim nilai query terakhir
                           courier_query=courier_query,
                           supported_couriers=supported_couriers)