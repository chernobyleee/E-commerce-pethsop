# app/decorators.py
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Anda harus login untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('users.login'))
        if current_user.role != 'admin': # Asumsi role 'admin'
            flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Anda harus login untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('users.login'))
        # Periksa apakah role bukan 'admin' (atau secara eksplisit 'customer')
        # Jika Anda hanya memiliki 'admin' dan 'customer', cukup periksa 'admin'
        # Jika ada role lain, lebih baik eksplisit memeriksa 'customer'
        if current_user.role == 'admin': # Asumsi admin tidak boleh belanja
            flash('Admin tidak dapat melakukan order pada halaman ini.', 'danger')
            return redirect(url_for('admin.dashboard')) # Atau ke halaman lain yang sesuai
        return f(*args, **kwargs)
    return decorated_function