# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, DecimalField, IntegerField, SelectField, BooleanField,HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, ValidationError
from flask_wtf.file import FileField, FileAllowed, MultipleFileField # <<< IMPORT MultipleFileField
from app.models.user import User
from app.models.category import Category 

class UpdateProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')

class AddProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=255)])
    
    category_id = SelectField('Category', coerce=str, validators=[DataRequired()])

    description = TextAreaField('Description')
    price = DecimalField('Price', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    weight = IntegerField('Weight (grams)', validators=[Optional(), NumberRange(min=0)])
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    
    # --- MODIFIKASI UNTUK MULTI-IMAGE ---
    # Field untuk thumbnail utama (opsional, karena bisa dipilih dari galeri)
    thumbnail_upload = FileField('Upload Main Thumbnail (Optional)', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    
    # Field untuk gambar galeri tambahan
    gallery_uploads = MultipleFileField('Upload Additional Product Images (Optional)', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    # --- AKHIR MODIFIKASI ---
    
    submit = SubmitField('Add Product')

    def __init__(self, *args, **kwargs):
        super(AddProductForm, self).__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(deleted_at=None).order_by(Category.name).all()]
        self.category_id.choices.insert(0, ('', '--- Select Category ---'))


class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    role = SelectField('Role', choices=[('customer', 'Customer'), ('admin', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Save User')

    def __init__(self, original_email=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already taken. Please choose a different one.')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Save Category')

    def __init__(self, original_name=None, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            category = Category.query.filter_by(name=name.data, deleted_at=None).first()
            if category:
                raise ValidationError('That category name already exists. Please choose a different one.')
            
class CancellationRequestForm(FlaskForm):
    reason = TextAreaField('Alasan Pembatalan', 
                           validators=[DataRequired(message="Alasan pembatalan tidak boleh kosong."), 
                                       Length(min=10, max=500, message="Alasan harus antara 10 dan 500 karakter.")],
                           render_kw={"rows": 4, "placeholder": "Mohon berikan alasan Anda membatalkan pesanan ini..."})
    order_id = HiddenField() # Untuk menyimpan order_id jika diperlukan di form
    submit = SubmitField('Kirim Permintaan Pembatalan')