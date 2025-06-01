# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask_apscheduler import APScheduler
from .utils import generate_whatsapp_refund_link

# --- TAMBAHKAN IMPOR INI ---
from jinja2 import FileSystemLoader, Environment
# --- AKHIR TAMBAHAN ---

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # --- TAMBAHKAN KONFIGURASI JINJA2 DI SINI ---
    # Mendapatkan path absolut ke folder 'app'
    app_root = os.path.dirname(os.path.abspath(__file__))
    
    # Buat loader Jinja2 yang akan mencari di folder 'templates' DAN 'macros'
    app.jinja_env.loader = Environment(
        loader=FileSystemLoader([
            os.path.join(app_root, 'templates'), # Folder templates standar
            os.path.join(app_root, 'macros')    # Folder macros baru Anda
        ])
    ).loader # Ambil loader dari Environment yang baru dibuat
    # --- AKHIR TAMBAHAN ---

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'users.login'
    login_manager.login_message_category = 'info'

    from app.models.user import User
    from app.models.product import Product
    from app.models.category import Category
    from app.models.product_image import ProductImage
    from app.models.cart import Cart
    from app.models.order import Order
    from app.models.order_detail import OrderDetail 
    from app.models.payment import Payment 
    from app.models.shipment import Shipment 

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

     # Context processor untuk inject variabel/fungsi ke semua template
    @app.context_processor
    def inject_global_vars():
        return dict(
            datetime=datetime, # Jika Anda butuh datetime di template
            generate_whatsapp_refund_link=generate_whatsapp_refund_link # Daftarkan fungsi di sini
        )

    
    @app.context_processor
    def inject_datetime():
        return {'datetime': datetime}

    
    # Register blueprints
    from .routes.main import main_bp
    from .routes.products import products_bp
    from .routes.users import users_bp
    from .routes.cart import cart_bp
    from .routes.orders import orders_bp
    from .routes.admin import admin_bp
    from .routes.midtrans import midtrans_bp


    app.register_blueprint(main_bp)
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(midtrans_bp)

    scheduler.init_app(app)
    scheduler.start()

    from app.tasks import check_delivered_orders

    scheduler.add_job(id='auto_receive_orders', func=lambda: app.app_context().push() or check_delivered_orders(app), trigger='interval', hours=1, replace_existing=True)

    
    return app