from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import current_user
from app.models.product import Product
from app.models.category import Category
from app.models.product_image import ProductImage

main_bp = Blueprint('main', __name__)

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