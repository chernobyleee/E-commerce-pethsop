# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-default-key'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL','mysql+pymysql://root:@localhost/petshop?charset=utf8mb4')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)),'app', 'static', 'uploads', 'products')
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_IMAGE_FILESIZE = 16 * 1024 * 1024 # 16 MB

    # Konfigurasi Midtrans - PERBAIKAN DI SINI
    MIDTRANS_SERVER_KEY = os.environ.get('MIDTRANS_SERVER_KEY')
    MIDTRANS_CLIENT_KEY = os.environ.get('MIDTRANS_CLIENT_KEY')
    MIDTRANS_PRODUCTION = os.environ.get('MIDTRANS_PRODUCTION', 'false').lower() == 'true'
    MIDTRANS_IS_PRODUCTION = os.environ.get('MIDTRANS_PRODUCTION', 'false').lower() == 'true'  # TAMBAHKAN INI
    MIDTRANS_NOTIFICATION_URL = os.environ.get('MIDTRANS_NOTIFICATION_URL') 

    KOMSHIP_API_KEY = os.environ.get('KHOMSIP_API_KEY') 
    RAJA_ONGKIR_TRACKING_API_KEY = os.environ.get('RAJA_ONGKIR_API_KEY') 

    SHOP_ORIGIN_REGION_ID = 8240 
    SHOP_ORIGIN_PROVINCE = "Jawa Barat" 
    SHOP_ORIGIN_CITY = "Bogor" 
    SHOP_ORIGIN_DISTRICT = "Ciampea" 
    SHOP_ORIGIN_ZIP_CODE = "16620" 
    SHOP_ORIGIN_ADDRESS = "Jalan Cibuntu 01 Rt 02 Rw 04"

    LOW_STOCK_THRESHOLD = os.environ.get('LOW_STOCK_THRESHOLD',2)