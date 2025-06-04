# app/routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models.product import Product
from app.models.user import User
from app.models.order import Order
from app.models.order_detail import OrderDetail
from app.models.shipment import Shipment
from app.models.category import Category # <<< UNCOMMENT INI
from app.models.product_image import ProductImage # Import ProductImage
from app import db
from app.decorators import admin_required
import uuid
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from app.forms import UpdateProfileForm, AddProductForm, UserForm # Import UserForm
from decimal import Decimal
from datetime import datetime, timedelta # <-- TAMBAHKAN 'timedelta' DI SINI
from sqlalchemy import func 

# --- Import Form Baru untuk Kategori ---
from app.forms import AddProductForm, UserForm # Pastikan AddProductForm dan UserForm sudah ada
# Kita akan menambahkan form baru untuk Category nanti jika belum ada
# Jika Anda berencana membuat CategoryForm terpisah, import di sini juga:
# from app.forms import CategoryForm 

admin_bp = Blueprint('admin', __name__)

# Helper function untuk menyimpan gambar (lebih generik)
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_IMAGE_EXTENSIONS']

def save_image_file(image_file):
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        # Tambahkan UUID agar nama file unik
        unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True) # Pastikan folder ada
        
        image_path = os.path.join(upload_folder, unique_filename)
        image_file.save(image_path)
        
        # Kembalikan hanya nama unik file (bukan URL lengkap)
        return unique_filename 
    return None

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    # Product Statistics
    total_active_products = Product.query.filter(Product.deleted_at.is_(None)).count()
    low_stock_threshold = current_app.config.get('LOW_STOCK_THRESHOLD', 5)
    products_low_stock = Product.query.filter(
        Product.deleted_at.is_(None), 
        Product.stock > 0,  # Pastikan produk masih ada stok, tapi di bawah threshold
        Product.stock <= low_stock_threshold
    ).count()
    products_out_of_stock = Product.query.filter(Product.deleted_at.is_(None), Product.stock == 0).count()

    # User Statistics
    total_users = User.query.count() 

    # Order Statistics
    total_orders = Order.query.count()
    
    orders_pending_payment = Order.query.filter(
        Order.status.in_(['pending', 'pending_payment']), # Mencakup kedua status jika alur Anda begitu
        Order.payment_status == 'unpaid'
    ).count()
    
    orders_awaiting_shipment = Order.query.filter(Order.status == 'processing').count()
    orders_shipped = Order.query.filter_by(status='shipped').count()
    orders_completed = Order.query.filter_by(status='completed').count()
    orders_cancelled = Order.query.filter_by(status='cancelled').count()
    
    orders_awaiting_refund = Order.query.filter(
        Order.status == 'cancelled', 
        Order.payment_status == 'refund_requested'
    ).count()

    # Revenue Statistics
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    next_month_num = current_month_start.month % 12 + 1
    year_offset = 1 if current_month_start.month == 12 else 0
    next_month_start_date = current_month_start.replace(year=current_month_start.year + year_offset, month=next_month_num, day=1)
    current_month_end = next_month_start_date - timedelta(seconds=1)

    paid_at_is_not_null = Order.paid_at.isnot(None) # Kondisi untuk memastikan paid_at tidak null

    total_revenue_today = db.session.query(func.sum(Order.total)).filter(
        Order.status == 'completed', 
        paid_at_is_not_null,
        Order.paid_at >= today_start, 
        Order.paid_at < (today_start + timedelta(days=1)) 
    ).scalar() or 0

    total_revenue_this_month = db.session.query(func.sum(Order.total)).filter(
        Order.status == 'completed', 
        paid_at_is_not_null,
        Order.paid_at >= current_month_start, 
        Order.paid_at <= current_month_end
    ).scalar() or 0

    total_revenue_all_time = db.session.query(func.sum(Order.total)).filter(
        Order.status == 'completed',
        paid_at_is_not_null
    ).scalar() or 0
    
    # Recent activities untuk notifikasi sederhana
    limit_recent = 3 # Batasi jumlah notifikasi
    recent_pending_payment_orders = Order.query.filter(
        Order.status.in_(['pending', 'pending_payment']),
        Order.payment_status == 'unpaid'
    ).order_by(Order.created_at.desc()).limit(limit_recent).all()

    recent_processing_orders = Order.query.filter(
        Order.status == 'processing'
    ).order_by(Order.paid_at.desc() if hasattr(Order, 'paid_at') and Order.paid_at is not None else Order.created_at.desc()).limit(limit_recent).all()

    recent_cancelled_for_refund = Order.query.filter(
        Order.status == 'cancelled',
        Order.payment_status == 'refund_requested'
    ).order_by(Order.cancelled_at.desc() if hasattr(Order, 'cancelled_at') and Order.cancelled_at is not None else Order.created_at.desc()).limit(limit_recent).all()
    
    current_app.logger.debug(f"Admin Dashboard Stats - Low Stock: {products_low_stock}, Out of Stock: {products_out_of_stock}, Awaiting Refund: {orders_awaiting_refund}, Total Users: {total_users}")


    return render_template('admin/dashboard.html',
                           title='Dasbor Admin',
                           # Product stats
                           total_active_products=total_active_products,
                           products_low_stock=products_low_stock,
                           products_out_of_stock=products_out_of_stock,
                           # User stats
                           total_users=total_users,
                           # Order stats
                           total_orders=total_orders,
                           orders_pending_payment=orders_pending_payment,
                           orders_awaiting_shipment=orders_awaiting_shipment,
                           orders_shipped=orders_shipped,
                           orders_completed=orders_completed,
                           orders_cancelled=orders_cancelled,
                           orders_awaiting_refund=orders_awaiting_refund,
                           # Revenue stats
                           total_revenue_today=total_revenue_today,
                           total_revenue_this_month=total_revenue_this_month,
                           total_revenue_all_time=total_revenue_all_time,
                           # Recent activities
                           recent_pending_payment_orders=recent_pending_payment_orders,
                           recent_processing_orders=recent_processing_orders,
                           recent_cancelled_for_refund=recent_cancelled_for_refund
                           )

@admin_bp.route('/products')
@login_required
@admin_required
def product_management():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    products = Product.query.filter_by(deleted_at=None).order_by(Product.name.asc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin/product_management.html',
                           title='Manage Products',
                           products=products)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    form = AddProductForm()

    if form.validate_on_submit():
        try:
            new_product = Product(
                name=form.name.data,
                description=form.description.data,
                price=form.price.data,
                weight=form.weight.data,
                stock=form.stock.data,
                category_id=form.category_id.data if form.category_id.data else None # Handle empty category
            )
            db.session.add(new_product)
            db.session.flush() # Flush to get product.id before committing

            # Handle thumbnail image upload
            if form.thumbnail_upload.data:
                thumbnail_filename = save_image_file(form.thumbnail_upload.data)
                if thumbnail_filename:
                    # Hapus thumbnail lama jika ada
                    if new_product.image_url: # image_url di Product adalah thumbnail utama
                        try:
                            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], new_product.image_url.split('/')[-1]))
                        except OSError as e:
                            current_app.logger.warning(f"Error deleting old thumbnail: {e}")
                    new_product.image_url = url_for('static', filename=f'uploads/products/{thumbnail_filename}')
                    
                    # Tambahkan ke ProductImage juga sebagai thumbnail
                    new_product_image = ProductImage(
                        product_id=new_product.id,
                        name=thumbnail_filename,
                        is_thumbnail=True
                    )
                    db.session.add(new_product_image)

            # Handle additional gallery images upload
            for file_storage in request.files.getlist('gallery_uploads'): # Ambil langsung dari request.files
                if file_storage and allowed_file(file_storage.filename):
                    gallery_filename = save_image_file(file_storage)
                    if gallery_filename:
                        new_gallery_image = ProductImage(
                            product_id=new_product.id,
                            name=gallery_filename,
                            is_thumbnail=False
                        )
                        db.session.add(new_gallery_image)
            
            db.session.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin.product_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {e}', 'danger')
            current_app.logger.error(f"Error adding product: {e}")

    else:
        current_app.logger.debug("Form validation failed. Errors:")
        for field, errors in form.errors.items():
            for error in errors:
                current_app.logger.debug(f"Field '{field}': {error}")

    return render_template('admin/product_form.html', title='Add New Product', form=form)

@admin_bp.route('/products/edit/<string:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.filter_by(id=product_id, deleted_at=None).options(
        db.joinedload(Product.images) # Eager load images for display and management
    ).first_or_404()
    
    form = AddProductForm(obj=product) # Pre-populate form with product data

    if form.validate_on_submit():
        try:
            # Update product basic info
            product.name = form.name.data
            product.description = form.description.data
            product.price = form.price.data
            product.stock = form.stock.data
            product.weight = form.weight.data
            product.category_id = form.category_id.data if form.category_id.data else None
            product.updated_at = datetime.utcnow()

            # Handle new thumbnail upload
            if form.thumbnail_upload.data:
                # Dapatkan nama file lama dari product.image_url jika ada
                old_thumbnail_filename = None
                if product.image_url:
                    old_thumbnail_filename = product.image_url.split('/')[-1]

                new_thumbnail_filename = save_image_file(form.thumbnail_upload.data)
                if new_thumbnail_filename:
                    # Hapus thumbnail lama dari Product.image_url jika ada
                    if old_thumbnail_filename:
                        try:
                            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], old_thumbnail_filename))
                        except OSError as e:
                            current_app.logger.warning(f"Error deleting old product.image_url file: {e}")

                    # Update Product.image_url ke URL gambar baru
                    product.image_url = url_for('static', filename=f'uploads/products/{new_thumbnail_filename}')

                    # Perbarui atau buat ProductImage yang baru sebagai thumbnail
                    # Hapus is_thumbnail dari gambar sebelumnya
                    ProductImage.query.filter_by(product_id=product.id, is_thumbnail=True).update({'is_thumbnail': False})
                    db.session.flush() # Penting agar perubahan tercatat sebelum menambah yang baru

                    # Cek apakah gambar yang baru diupload sudah ada sebagai ProductImage non-thumbnail
                    existing_image = ProductImage.query.filter_by(product_id=product.id, name=new_thumbnail_filename).first()
                    if existing_image:
                        existing_image.is_thumbnail = True
                    else:
                        new_product_image = ProductImage(
                            product_id=product.id,
                            name=new_thumbnail_filename,
                            is_thumbnail=True
                        )
                        db.session.add(new_product_image)

            # Handle additional gallery images upload
            for file_storage in request.files.getlist('gallery_uploads'):
                if file_storage and allowed_file(file_storage.filename):
                    gallery_filename = save_image_file(file_storage)
                    if gallery_filename:
                        new_gallery_image = ProductImage(
                            product_id=product.id,
                            name=gallery_filename,
                            is_thumbnail=False
                        )
                        db.session.add(new_gallery_image)
            
            # Handle existing images: delete selected images
            # (Ini akan memerlukan perubahan di template untuk input hidden)
            images_to_delete_ids = request.form.getlist('delete_image_ids')
            for img_id in images_to_delete_ids:
                img_to_delete = ProductImage.query.get(img_id)
                if img_to_delete and img_to_delete.product_id == product.id:
                    # Hapus file fisik
                    try:
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], img_to_delete.name))
                    except OSError as e:
                        current_app.logger.warning(f"Error deleting image file {img_to_delete.name}: {e}")
                    
                    db.session.delete(img_to_delete)
                    # Jika yang dihapus adalah thumbnail utama produk, reset product.image_url
                    if img_to_delete.is_thumbnail:
                        product.image_url = None

            # Handle existing images: change thumbnail status
            new_thumbnail_id = request.form.get('set_as_thumbnail_id')
            if new_thumbnail_id:
                # Reset semua is_thumbnail untuk produk ini
                ProductImage.query.filter_by(product_id=product.id).update({'is_thumbnail': False})
                db.session.flush()

                # Set yang baru
                selected_thumbnail = ProductImage.query.get(new_thumbnail_id)
                if selected_thumbnail and selected_thumbnail.product_id == product.id:
                    selected_thumbnail.is_thumbnail = True
                    # Update product.image_url
                    product.image_url = url_for('static', filename=f'uploads/products/{selected_thumbnail.name}')

            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.product_management'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating product {product_id}: {str(e)}")
            flash('Error updating product. Please try again.', 'danger')

    # Saat GET request atau form validation failed
    # Pastikan form fields memiliki nilai dari produk yang sedang diedit
    # form.name.data = product.name (sudah otomatis dengan obj=product)
    # dst.
    
    return render_template('admin/product_form.html',
                           title='Edit Product',
                           form=form,
                           product=product) # Kirim objek produk ke template
@admin_bp.route('/products/delete/<string:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id, deleted_at=None).first_or_404()
    
    product.deleted_at = datetime.utcnow()

    try:
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting product {product_id}: {str(e)}")
        flash('Error deleting product. Please try again.', 'danger')
    
    return redirect(url_for('admin.product_management'))

@admin_bp.route('/orders')
@login_required
@admin_required
def order_management():
    page = request.args.get('page', 1, type=int)
    per_page = 10 
    status_filter = request.args.get('status_filter', 'all')

    query = Order.query

    if status_filter and status_filter != 'all':
        if status_filter == 'pending_payment':
            query = query.filter(Order.status.in_(['pending', 'pending_payment']), Order.payment_status == 'unpaid')
        elif status_filter == 'refund_requested':
             query = query.filter(Order.status == 'cancelled', Order.payment_status == 'refund_requested')
        elif status_filter == 'cancellation_requested': # Filter baru
            query = query.filter(Order.status == 'cancellation_requested')
        else:
            query = query.filter(Order.status == status_filter)
    
    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    order_statuses = [
        {'value': 'all', 'name': 'Semua Status'},
        {'value': 'pending', 'name': 'Pending (Pra Bayar)'},
        {'value': 'pending_payment', 'name': 'Menunggu Pembayaran'},
        {'value': 'cancellation_requested', 'name': 'Permintaan Pembatalan'}, # Opsi filter baru
        {'value': 'processing', 'name': 'Perlu Diproses'},
        {'value': 'shipped', 'name': 'Dikirim'},
        {'value': 'completed', 'name': 'Selesai'},
        {'value': 'cancelled', 'name': 'Dibatalkan'},
        {'value': 'failed', 'name': 'Gagal'},
        {'value': 'refund_requested', 'name': 'Menunggu Refund'}
    ]
    
    return render_template('admin/order_management.html', 
                           title='Manajemen Pesanan', 
                           orders=orders,
                           order_statuses=order_statuses,
                           current_status_filter=status_filter)


@admin_bp.route('/orders/<string:order_id>/ship', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_ship_order(order_id):
    order = Order.query.get_or_404(order_id)
    shipment = Shipment.query.filter_by(order_id=order.id).first()

    if not shipment:
        flash("Shipment details not found for this order.", "danger")
        return redirect(url_for('admin.admin_order_detail', order_id=order.id))

    if request.method == 'POST':
        tracking_number = request.form.get('tracking_number')
        if tracking_number:
            try:
                shipment.tracking_number = tracking_number
                shipment.shipped_at = datetime.utcnow()
                
                order.status = 'shipped'
                
                db.session.commit()
                flash('Nomor resi berhasil disimpan dan status pesanan diperbarui menjadi Dikirim!', 'success')
                return redirect(url_for('admin.admin_order_detail', order_id=order.id))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error updating tracking number for order {order_id}: {str(e)}")
                flash('Gagal menyimpan nomor resi. Silakan coba lagi.', 'danger')
        else:
            flash('Nomor resi tidak boleh kosong.', 'danger')

    return render_template('admin/ship_order.html',
                           title=f'Input Resi Pesanan #{order.invoice_number}',
                           order=order,
                           shipment=shipment)


@admin_bp.route('/orders/<string:order_id>')
@login_required
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get(order_id)
    if not order:
        current_app.logger.warning(f"Admin: Order with ID {order_id} not found.")
        flash("Order not found.", "danger")
        return redirect(url_for('admin.order_management'))

    order_details = OrderDetail.query.filter_by(order_id=order.id).all()
    shipment = Shipment.query.filter_by(order_id=order.id).first()

    subtotal = Decimal(0)
    for detail in order_details:
        subtotal += Decimal(str(detail.price)) * detail.quantity

    return render_template('admin/order_detail.html',
                           title=f'Detail Pesanan Admin #{order.invoice_number}',
                           order=order,
                           order_details=order_details,
                           shipment=shipment,
                           subtotal=subtotal)
    
# --- BARU: Route untuk menandai refund sudah diproses ---
@admin_bp.route('/orders/<string:order_id>/mark_refund_processed', methods=['POST']) # Pastikan ini POST
@login_required
@admin_required
def mark_refund_processed(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'cancelled' and order.payment_status == 'refund_requested':
        try:
            order.payment_status = 'refunded' 
            # Anda mungkin ingin menambahkan field order.refunded_at = datetime.utcnow()
            db.session.commit()
            flash(f'Refund untuk pesanan #{order.invoice_number} telah ditandai selesai.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal menandai refund selesai: {str(e)}', 'danger')
            current_app.logger.error(f"Error marking refund as processed for order {order.id}: {e}")
    else:
        flash('Status pesanan tidak valid untuk menandai refund selesai.', 'warning')
    return redirect(url_for('admin.admin_order_detail', order_id=order.id))


# --- Rute Manajemen User (tetap sama) ---

@admin_bp.route('/users')
@login_required
@admin_required
def user_management():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin/user_management.html',
                           title='Manage Users',
                           users=users)

@admin_bp.route('/users/edit/<string:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(original_email=user.email, obj=user)

    if form.validate_on_submit():
        if user == current_user and form.role.data != 'admin':
            flash('Anda tidak dapat mengubah role Anda sendiri dari admin.', 'danger')
            return redirect(url_for('admin.user_management'))
            
        user.name = form.name.data
        user.email = form.email.data
        user.phone_number = form.phone_number.data
        user.role = form.role.data
        user.updated_at = datetime.utcnow()

        try:
            db.session.commit()
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin.user_management'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating user {user_id}: {str(e)}")
            flash('Error updating user. Please try again.', 'danger')
    
    return render_template('admin/user_form.html',
                           title='Edit User',
                           form=form,
                           user=user)

@admin_bp.route('/users/delete/<string:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user == current_user:
        flash('Anda tidak dapat menghapus akun Anda sendiri.', 'danger')
        return redirect(url_for('admin.user_management'))

    try:
        # PENTING: Untuk menghindari IntegrityError, Anda harus menangani relasi dengan Order
        # Opsi:
        # 1. Set user_id di Order menjadi NULL (jika kolom diizinkan NULL)
        #    Order.query.filter_by(user_id=user.id).update({'user_id': None})
        # 2. Hapus semua order_detail dan order yang terkait
        #    OrderDetail.query.filter(OrderDetail.order.has(user_id=user.id)).delete(synchronize_session='fetch')
        #    Order.query.filter_by(user_id=user.id).delete(synchronize_session='fetch')
        # 3. Soft delete user jika ada `deleted_at` (yang sudah Anda lakukan sebelumnya)
        #    user.deleted_at = datetime.utcnow()
        #    db.session.commit()

        # Karena Anda memutuskan untuk TIDAK MENGHAPUS USER (secara permanen)
        # Baris db.session.delete(user) ini harus DIHAPUS atau DIKOMENTARI
        # Jika Anda ingin tetap soft delete, gunakan:
        user.soft_delete() # Menggunakan metode soft_delete yang sudah ada di model User
        db.session.commit()
        flash('User soft-deleted successfully!', 'success') # Ubah pesan
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id}: {str(e)}")
        flash('Error deleting user. Please try again.', 'danger')
    
    return redirect(url_for('admin.user_management'))

# --- RUTE MANAJEMEN KATEGORI BARU ---

# Route untuk menampilkan daftar kategori
@admin_bp.route('/categories')
@login_required
@admin_required
def category_management():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Ambil kategori yang tidak soft-deleted
    categories = Category.query.filter_by(deleted_at=None).order_by(Category.name.asc()).paginate(page=page, per_page=per_page)
    
    return render_template('admin/category_management.html',
                           title='Manage Categories',
                           categories=categories)

# Route untuk menambah kategori baru
@admin_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    # Buat CategoryForm baru. Kita akan definisikan ini nanti di app/forms.py
    # Untuk sementara, jika Anda belum membuat CategoryForm, Anda bisa menggunakan FlaskForm kosong dulu
    # atau definisikan CategoryForm sederhana di forms.py
    from app.forms import CategoryForm # <<< Import CategoryForm
    form = CategoryForm()

    if form.validate_on_submit():
        try:
            new_category = Category(
                name=form.name.data
                # Slug akan otomatis digenerate oleh event listener di model Category
            )
            db.session.add(new_category)
            db.session.commit()
            flash('Category added successfully!', 'success')
            return redirect(url_for('admin.category_management'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding category: {str(e)}")
            flash(f'Error adding category: {e}', 'danger')
    
    return render_template('admin/category_form.html',
                           title='Add New Category',
                           form=form)

# Route untuk mengedit kategori
@admin_bp.route('/categories/edit/<string:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    category = Category.query.filter_by(id=category_id, deleted_at=None).first_or_404()
    from app.forms import CategoryForm # <<< Import CategoryForm
    form = CategoryForm(obj=category) # Pre-fill form with existing category data

    if form.validate_on_submit():
        try:
            category.name = form.name.data
            # Slug akan otomatis diupdate oleh event listener di model Category
            category.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Category updated successfully!', 'success')
            return redirect(url_for('admin.category_management'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating category {category_id}: {str(e)}")
            flash(f'Error updating category: {e}', 'danger')
    
    return render_template('admin/category_form.html',
                           title='Edit Category',
                           form=form,
                           category=category)

# Route untuk soft-delete kategori
@admin_bp.route('/categories/delete/<string:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, deleted_at=None).first_or_404()

    # Sebelum menghapus kategori, Anda perlu mempertimbangkan produk yang terkait.
    # Ada 3 opsi utama:
    # 1. Hapus semua produk di bawah kategori ini (berisiko).
    #    Product.query.filter_by(category_id=category.id).delete()
    # 2. Set category_id produk yang terkait menjadi NULL.
    #    Product.query.filter_by(category_id=category.id).update({'category_id': None}, synchronize_session=False)
    # 3. Soft delete produk yang terkait juga (jika produk memiliki `deleted_at`).
    #    for product in category.products:
    #        product.soft_delete()

    # Karena Anda menggunakan soft delete di Product, mari kita soft delete produk terkait juga.
    # Atau, jika Anda ingin produk tetap ada tetapi tanpa kategori, set category_id ke None.
    # Pilihan saya: set category_id ke None.
    try:
        # Set category_id di semua produk yang terkait menjadi NULL
        # Ini akan memastikan tidak ada integrity error saat kategori dihapus
        for product in category.products:
            product.category_id = None
        
        category.soft_delete() # Gunakan soft delete untuk kategori
        db.session.commit()
        flash('Category soft-deleted successfully! Related products\' categories have been unset.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error soft-deleting category {category_id}: {str(e)}")
        flash(f'Error soft-deleting category: {e}', 'danger')
    
    return redirect(url_for('admin.category_management'))

@admin_bp.route('/orders/update_status/<string:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('new_status')

    # Validasi new_status jika perlu (misalnya, pastikan statusnya ada dalam daftar status yang valid)
    valid_statuses = ['pending', 'pending_payment', 'processing', 'shipped', 'completed', 'cancelled', 'failed'] # Sesuaikan dengan status Anda
    if new_status not in valid_statuses:
        flash(f"Status '{new_status}' tidak valid.", 'danger')
        return redirect(url_for('admin.admin_order_detail', order_id=order.id))

    # Logika tambahan berdasarkan perubahan status
    # Misalnya, jika status diubah menjadi 'shipped' dan belum ada nomor resi,
    # Anda mungkin ingin mencegahnya atau memberi peringatan.
    # Atau jika status 'completed', pastikan sudah 'shipped' dulu, dll.

    # Contoh sederhana:
    if order.status != new_status:
        order.status = new_status
        # Jika status 'shipped', catat tanggal pengiriman
        if new_status == 'shipped' and not order.shipped_at:
            order.shipped_at = datetime.utcnow()
            # Anda mungkin juga ingin mengirim notifikasi ke pelanggan di sini
        
        # Jika status 'completed', catat tanggal diterima
        elif new_status == 'completed' and not order.delivered_at:
            # Biasanya ini dikonfirmasi oleh pelanggan, tapi admin bisa override
            order.delivered_at = datetime.utcnow() 
        
        # Jika status 'cancelled'
        elif new_status == 'cancelled':
            if not order.cancelled_at:
                order.cancelled_at = datetime.utcnow()
            # Logika tambahan untuk pembatalan, misal kembalikan stok, cek payment_status
            if order.payment_status == 'paid': # Jika sudah dibayar dan dibatalkan admin
                order.payment_status = 'refund_requested' # atau logika refund Anda
                flash('Pesanan dibatalkan. Proses refund mungkin diperlukan jika sudah dibayar.', 'info')
            # Logika untuk mengembalikan stok jika pesanan dibatalkan
            # for item in order.order_details:
            #     product = Product.query.get(item.product_id)
            #     if product:
            #         product.stock += item.quantity
        
        db.session.commit()
        flash(f"Status pesanan #{order.invoice_number} berhasil diubah menjadi '{new_status.replace('_',' ').title()}'.", 'success')
    else:
        flash(f"Pesanan #{order.invoice_number} sudah dalam status '{new_status.replace('_',' ').title()}'. Tidak ada perubahan.", 'info')

    return redirect(url_for('admin.admin_order_detail', order_id=order.id))

@admin_bp.route('/orders/<string:order_id>/approve_cancellation', methods=['POST'])
@login_required
@admin_required
def approve_cancellation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'cancellation_requested':
        try:
            previous_status = order.status # Simpan status sebelum diubah
            order.status = 'cancelled'
            order.cancelled_at = datetime.utcnow()
            # Jika sudah dibayar, ubah status pembayaran untuk proses refund
            if order.payment_status == 'paid':
                order.payment_status = 'refund_requested' 
                # Di sini Anda juga bisa memicu pengembalian stok produk
                # for item in order.order_details:
                #     product = Product.query.get(item.product_id)
                #     if product:
                #         product.stock += item.quantity
                #         current_app.logger.info(f"Stock for product {product.id} restored by {item.quantity}")
            
            db.session.commit()
            flash(f'Permintaan pembatalan untuk pesanan #{order.invoice_number} telah DISETUJUI.', 'success')
            # Kirim notifikasi ke pelanggan bahwa pembatalan disetujui
            # ... (logika notifikasi Anda) ...
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal menyetujui pembatalan: {str(e)}', 'danger')
            current_app.logger.error(f"Error approving cancellation for order {order.id}: {e}")
    else:
        flash('Pesanan ini tidak dalam status menunggu persetujuan pembatalan.', 'warning')
    return redirect(url_for('admin.admin_order_detail', order_id=order.id))

@admin_bp.route('/orders/<string:order_id>/reject_cancellation', methods=['POST'])
@login_required
@admin_required
def reject_cancellation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status == 'cancellation_requested':
        try:
            # Kembalikan ke status sebelum 'cancellation_requested'
            # Ini memerlukan Anda untuk tahu apa status sebelumnya.
            # Untuk kesederhanaan, kita bisa kembalikan ke 'processing' jika sudah 'paid', atau 'pending_payment' jika 'unpaid'.
            # Atau, Anda bisa menyimpan 'previous_status' saat request cancel dibuat.
            if order.payment_status == 'paid':
                order.status = 'processing' 
            else: # unpaid
                order.status = 'pending_payment' 
            
            # Hapus alasan pembatalan dan tanggal permintaan
            order.cancellation_reason = None
            order.cancellation_requested_at = None
            
            db.session.commit()
            flash(f'Permintaan pembatalan untuk pesanan #{order.invoice_number} telah DITOLAK. Status dikembalikan.', 'info')
            # Kirim notifikasi ke pelanggan bahwa pembatalan ditolak
            # ... (logika notifikasi Anda) ...
        except Exception as e:
            db.session.rollback()
            flash(f'Gagal menolak pembatalan: {str(e)}', 'danger')
            current_app.logger.error(f"Error rejecting cancellation for order {order.id}: {e}")
    else:
        flash('Pesanan ini tidak dalam status menunggu persetujuan pembatalan.', 'warning')
    return redirect(url_for('admin.admin_order_detail', order_id=order.id))