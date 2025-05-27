# app/routes/users.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db # Pastikan ini diimpor
from werkzeug.security import generate_password_hash, check_password_hash # Pastikan ini diimpor
import uuid # Untuk UUID
from app.forms import UpdateProfileForm

users_bp = Blueprint('users', __name__)

@users_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('users.register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('users.register'))

        new_user = User(
            id=str(uuid.uuid4()), # Generate UUID for ID
            name=name,
            email=email,
            # Password akan di-hash oleh setter properti 'password' di model
            role='customer' # Default role
        )
        new_user.password = password # Gunakan setter properti untuk hashing

        db.session.add(new_user)
        try:
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('users.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('users.register'))

    return render_template('auth/register.html', title='Register')

@users_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = True if request.form.get('remember_me') else False

        user = User.query.filter_by(email=email).first()

        # BARIS INI YANG DIUBAH
        # Anda harus membandingkan password yang dimasukkan dengan password_hash yang tersimpan di database
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password!', 'danger')
            return redirect(url_for('users.login'))

        login_user(user, remember=remember_me)
        flash('Logged in successfully!', 'success')
        
        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.home'))

    return render_template('auth/login.html', title='Login')

@users_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

@users_bp.route('/profile')
@login_required
def profile():
    # Anda bisa menambahkan logika untuk menampilkan/mengedit profil user di sini
    return render_template('users/profile.html', title='User Profile')

@users_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = UpdateProfileForm() # Ini akan memerlukan definisi form di app/forms.py

    if form.validate_on_submit():
        # Logic untuk menyimpan perubahan profil ke database
        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.phone_number = form.phone_number.data
        # Jika ada field lain yang bisa diedit, tambahkan di sini

        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('users.profile'))
    elif request.method == 'GET':
        # Pre-fill form with current user data
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.phone_number.data = current_user.phone_number

    return render_template('users/edit_profile.html', title='Edit Profile', form=form)

