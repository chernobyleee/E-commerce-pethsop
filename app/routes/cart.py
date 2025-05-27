# app/routes/cart.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session, current_app # <-- Tambahkan current_app jika belum ada
from flask_login import login_required, current_user
from app.models.cart import Cart
from app.models.product import Product
from app import db
import uuid
from datetime import datetime # <-- Tambahkan ini jika Anda menggunakan datetime.utcnow di model/route

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/cart')
@login_required
def view_cart():
    """
    Display user's shopping cart
    """
    # Get all items in the user's cart
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    # Calculate cart totals
    total_price = 0
    total_weight = 0

    for item in cart_items:
        # Pastikan item.product tidak None
        if item.product:
            item.subtotal = item.quantity * item.product.price
            total_price += item.subtotal
            total_weight += item.quantity * (item.product.weight / 1000)   # Convert to kg
        else:
            # Handle case where product might be deleted or invalid
            current_app.logger.warning(f"Product for cart item {item.id} not found.")
            # Anda bisa memilih untuk menghapus item keranjang ini, atau abaikan saja dari total
            # db.session.delete(item)
            # db.session.commit()

    return render_template('cart/view_cart.html',
                           title='Shopping Cart',
                           cart_items=cart_items,
                           total_price=total_price,
                           total_weight=total_weight)

@cart_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    """
    Add product to cart
    """
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))

    # Cek untuk permintaan AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not product_id:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Invalid product ID'}), 400
        flash('Invalid product', 'danger')
        return redirect(request.referrer)

    # Check if product exists and has sufficient stock
    product = Product.query.filter_by(id=product_id, deleted_at=None).first()
    if not product:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
        flash('Product not found', 'danger')
        return redirect(request.referrer)

    if quantity <= 0:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Quantity must be positive'}), 400
        flash('Quantity must be positive', 'warning')
        return redirect(request.referrer)

    # Check if item already in cart
    cart_item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if cart_item:
        # Update existing cart item
        if product.stock < (cart_item.quantity + quantity):
            if is_ajax:
                return jsonify({'success': False, 'message': 'Not enough stock available'}), 400
            flash('Not enough stock available', 'warning')
            return redirect(request.referrer)

        cart_item.quantity += quantity
        # cart_item.updated_at = db.func.now() # Dihapus jika model menangani onupdate
    else:
        # Create new cart item
        cart_item = Cart(
            # id=str(uuid.uuid4()), # Dihapus jika model menangani default primary key
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity,
            # created_at=db.func.now(), # Dihapus jika model menangani default
            # updated_at=db.func.now() # Dihapus jika model menangani default dan onupdate
        )
        db.session.add(cart_item)

    try:
        db.session.commit()
        # Kurangi stok produk setelah berhasil ditambahkan ke keranjang
        product.stock -= quantity
        db.session.commit() # Commit lagi untuk update stok

        if is_ajax:
            # Hitung ulang jumlah item di keranjang untuk tampilan real-time jika diperlukan
            cart_item_count = Cart.query.filter_by(user_id=current_user.id).count()
            return jsonify({"status": "success", "message": "Product added to cart", "cart_item_count": cart_item_count})
        flash('Product added to cart', 'success')
        return redirect(url_for('cart.view_cart')) # Redirect ke halaman keranjang
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding product to cart: {e}") # Log error lengkap
        if is_ajax:
            return jsonify({'success': False, 'message': 'Error adding product to cart'}), 500
        flash('Error adding product to cart', 'danger')
        return redirect(request.referrer)

@cart_bp.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    """
    Update cart item quantity
    """
    cart_id = request.form.get('cart_id')
    quantity = int(request.form.get('quantity', 1))

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not cart_id:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Invalid cart item'}), 400
        flash('Invalid cart item', 'danger')
        return redirect(url_for('cart.view_cart'))

    # Check if cart item exists
    cart_item = Cart.query.filter_by(id=cart_id, user_id=current_user.id).first()
    if not cart_item:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Cart item not found'}), 404
        flash('Cart item not found', 'danger')
        return redirect(url_for('cart.view_cart'))

    # Dapatkan stok awal produk sebelum update
    original_quantity_in_cart = cart_item.quantity
    product = cart_item.product

    if quantity <= 0:
        # Jika kuantitas 0 atau kurang, hapus item dari keranjang
        db.session.delete(cart_item)
        try:
            db.session.commit()
            product.stock += original_quantity_in_cart # Kembalikan stok yang sebelumnya dikurangi
            db.session.commit()
            if is_ajax:
                return jsonify({"status": "success", "message": "Item removed from cart"})
            flash('Item removed from cart', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error removing cart item {cart_id}: {e}")
            if is_ajax:
                return jsonify({'success': False, 'message': 'Error removing item from cart'}), 500
            flash('Error removing item from cart', 'danger')
        return redirect(url_for('cart.view_cart'))
    else:
        # Hitung perubahan stok yang diperlukan
        stock_change = quantity - original_quantity_in_cart

        # Periksa ketersediaan stok untuk perubahan yang diminta
        if stock_change > 0 and product.stock < stock_change:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Not enough stock available for update'}), 400
            flash('Not enough stock available', 'warning')
            return redirect(url_for('cart.view_cart'))

        # Update quantity
        cart_item.quantity = quantity
        # cart_item.updated_at = db.func.now() # Dihapus jika model menangani onupdate

        try:
            db.session.commit()
            product.stock -= stock_change # Sesuaikan stok
            db.session.commit() # Commit perubahan stok

            if is_ajax:
                return jsonify({"status": "success", "message": "Cart updated"})
            flash('Cart updated', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating cart item {cart_id}: {e}")
            if is_ajax:
                return jsonify({'success': False, 'message': 'Error updating cart'}), 500
            flash('Error updating cart', 'danger')

    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/cart/remove/<string:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    """
    Remove item from cart
    """
    cart_item = Cart.query.filter_by(id=cart_id, user_id=current_user.id).first()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not cart_item:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Cart item not found'}), 404
        flash('Cart item not found', 'danger')
        return redirect(url_for('cart.view_cart'))

    try:
        # Kembalikan stok produk sebelum menghapus item keranjang
        product = cart_item.product
        quantity_to_return = cart_item.quantity

        db.session.delete(cart_item)
        db.session.commit()

        if product: # Pastikan produk masih ada
            product.stock += quantity_to_return
            db.session.commit()

        if is_ajax:
            return jsonify({"status": "success", "message": "Item removed from cart"})
        flash('Item removed from cart', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing item from cart: {e}")
        if is_ajax:
            return jsonify({'success': False, 'message': 'Error removing item from cart'}), 500
        flash('Error removing item from cart', 'danger')

    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    """
    Clear all items from cart
    """
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        for item in cart_items:
            product = item.product
            if product:
                product.stock += item.quantity # Kembalikan stok produk
            db.session.delete(item)
        db.session.commit()
        flash('Cart cleared', 'success')
        if is_ajax:
            return jsonify({"status": "success", "message": "Cart cleared"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing cart: {e}")
        flash('Error clearing cart', 'danger')
        if is_ajax:
            return jsonify({'success': False, 'message': 'Error clearing cart'}), 500

    return redirect(url_for('cart.view_cart'))