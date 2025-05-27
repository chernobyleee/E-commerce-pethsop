# app/routes/products.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models.product import Product
from app.models.category import Category 
from app.models.product_image import ProductImage # <<< Pastikan ini diimpor
from app import db 
from sqlalchemy import or_ 
from sqlalchemy.orm import joinedload # <<< IMPORT joinedload

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
def product_list():
    """
    Display a list of available products with filtering and search options.
    """
    page = request.args.get('page', 1, type=int)
    per_page = 12 # Misalnya 12 produk per halaman
    
    category_id = request.args.get('category_id', type=str) 
    search_query = request.args.get('search_query', type=str) 

    # Query dasar untuk produk yang tidak dihapus
    # Gunakan joinedload untuk memuat kategori secara efisien
    query = Product.query.filter_by(deleted_at=None).options(joinedload(Product.category))

    if category_id and category_id != 'all': 
        query = query.filter_by(category_id=category_id)

    if search_query:
        query = query.filter(or_(
            Product.name.ilike(f'%{search_query}%'),
            Product.description.ilike(f'%{search_query}%')
        ))

    products = query.order_by(Product.name.asc()).paginate(page=page, per_page=per_page)
    
    categories = Category.query.order_by(Category.name.asc()).all()
    
    return render_template('products/product_list.html',
                           title='Our Products',
                           products=products,
                           categories=categories, 
                           selected_category_id=category_id, 
                           search_query=search_query)

@products_bp.route('/<string:product_id>')
def product_detail(product_id):
    """
    Display details of a single product with all its images.
    """
    # Menggunakan joinedload untuk memuat kategori DAN gambar dalam satu query
    product = Product.query.filter_by(id=product_id, deleted_at=None).options(
        joinedload(Product.category),
        joinedload(Product.images) # <<< Memuat semua gambar terkait
    ).first_or_404()
    
    # Urutkan gambar berdasarkan is_thumbnail (true duluan), lalu nama (opsional)
    # Ini memastikan gambar thumbnail muncul sebagai slide pertama
    all_images = sorted(product.images, key=lambda img: (not img.is_thumbnail, img.name))

    return render_template('products/product_detail.html',
                           title=product.name,
                           product=product,
                           all_images=all_images) # <<< Kirim semua gambar ke template