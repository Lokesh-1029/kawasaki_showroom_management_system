from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

from streamlit import user
from bike_price_predictor import KawasakiPricePredictor 
from werkzeug.security import generate_password_hash, check_password_hash
from ml_engine import KawasakiML
import os
from flask_mail import Mail, Message 
from werkzeug.utils import secure_filename 

app = Flask(__name__)
app.secret_key = 'kawasaki_secret_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)
ml_engine = KawasakiML()

# ============================================
# EMAIL CONFIGURATION
# ============================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'lokeshm0070@gmail.com'
app.config['MAIL_PASSWORD'] = 'kvfo hdky tyyj tvdo'
app.config['MAIL_DEFAULT_SENDER'] = ('Kawasaki Admin', 'lokeshm0070@gmail.com')

mail = Mail(app)

# ============================================
# UPLOAD FOLDER SETUP
# ============================================
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================
# EMAIL FUNCTIONS
# ============================================

def send_order_status_email(user_email, user_name, order_type, order_id, new_status):
    subject = f"Your Kawasaki {order_type} Order #{order_id} Status Update"
    body = f"""
Dear {user_name},

Your {order_type} order (ID: {order_id}) status has been updated to: {new_status.upper()}

Thank you for choosing Kawasaki.

Best regards,
Kawasaki Admin Team
"""
    msg = Message(subject, recipients=[user_email], body=body)
    try:
        mail.send(msg)
        print(f"✅ Email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def send_otp_email(user_email, user_name, otp_code):
    subject = "Kawasaki Admin Login OTP"
    body = f"""
Dear {user_name},

Your OTP for admin login is: {otp_code}

This OTP is valid for 5 minutes.

Best regards,
Kawasaki Security Team
"""
    msg = Message(subject, recipients=[user_email], body=body)
    try:
        mail.send(msg)
        print(f"✅ OTP sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ OTP error: {e}")
        return False

# ============================================
# DATABASE MODELS
# ============================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    role = db.Column(db.String(20), default='customer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    security_question = db.Column(db.String(200), nullable=True)  
    security_answer = db.Column(db.String(200), nullable=True)     
    reset_token = db.Column(db.String(100), nullable=True)          # ADD THIS LINE
    token_expiry = db.Column(db.DateTime, nullable=True)            # ADD THIS LINE
    last_login = db.Column(db.DateTime, nullable=True)
    part_orders = db.relationship('PartOrder', backref='user', lazy=True)
    clothing_orders = db.relationship('ClothingOrder', backref='user', lazy=True)
    
class AdminOTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    def is_valid(self):
        return not self.is_used and datetime.utcnow() < self.expires_at

class PartOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    admin_remarks = db.Column(db.Text, default='')

class ClothingOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    size = db.Column(db.String(10), default='M')
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    admin_remarks = db.Column(db.Text, default='')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    old_price = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(200), nullable=True)
    stock = db.Column(db.Integer, default=0)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Bike fields - MAKE SURE THESE EXIST
    cc = db.Column(db.Integer, default=0)
    top_speed = db.Column(db.Integer, default=0)
    mileage = db.Column(db.Float, default=0.0)
    power = db.Column(db.String(50), default='')
    features = db.Column(db.Text, default='')

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Bike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    cc = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    old_price = db.Column(db.Integer, nullable=True)
    fuel_type = db.Column(db.String(20), nullable=False)
    mileage = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    features = db.Column(db.Text, nullable=False)
    top_speed = db.Column(db.Integer, nullable=False)
    power = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Float, default=0)

class Scooter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cc = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    old_price = db.Column(db.Integer, nullable=True)
    fuel_type = db.Column(db.String(20), nullable=False)
    mileage = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    top_speed = db.Column(db.Integer, nullable=False)
    power = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Float, default=0)

class TestRide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bike_name = db.Column(db.String(100), nullable=False)
    test_date = db.Column(db.String(20), nullable=False)
    test_time = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pending')
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)

class BikeBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bike_name = db.Column(db.String(100), nullable=False)
    booking_date = db.Column(db.String(20), nullable=False)
    down_payment = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# CREATE DATABASE WITH SAMPLE DATA
# ============================================
with app.app_context():
    db.create_all()
    
    if Bike.query.count() == 0:
        bikes = [
            Bike(name='Ninja 400', category='Sport', cc=399, price=550000, fuel_type='Petrol', mileage=25.0, image='ninja400.jpg', description='Entry sportbike', features='ABS, Slipper clutch', top_speed=188, power='45 PS'),
            Bike(name='Ninja 650', category='Sport', cc=649, price=720000, fuel_type='Petrol', mileage=22.0, image='ninja650.jpg', description='Mid sportbike', features='TFT display, ABS', top_speed=210, power='68 PS'),
            Bike(name='Z900', category='Naked', cc=948, price=930000, fuel_type='Petrol', mileage=18.0, image='z900.jpg', description='Streetfighter', features='Traction control', top_speed=235, power='125 PS'),
            Bike(name='Ninja H2', category='Superbike', cc=998, price=3500000, fuel_type='Petrol', mileage=15.0, image='h2.jpg', description='Supercharged', features='Launch control', top_speed=300, power='231 PS'),
            Bike(name='Versys 650', category='Touring', cc=649, price=750000, fuel_type='Petrol', mileage=21.0, image='versys650.jpg', description='Adventure', features='Wind protection', top_speed=195, power='66 PS'),
            Bike(name='Vulcan 900', category='Cruiser', cc=903, price=880000, fuel_type='Petrol', mileage=19.0, image='vulcan900.jpg', description='Cruiser', features='V-twin', top_speed=175, power='50 PS')
        ]
        for bike in bikes:
            db.session.add(bike)
        
        scooters = [
            Scooter(name='J300', cc=299, price=450000, fuel_type='Petrol', mileage=28.0, image='j300.jpg', description='Maxi scooter', top_speed=130, power='27 PS'),
            Scooter(name='J125', cc=125, price=250000, fuel_type='Petrol', mileage=35.0, image='j125.jpg', description='Urban scooter', top_speed=95, power='13 PS')
        ]
        for scooter in scooters:
            db.session.add(scooter)
        
        db.session.commit()

# ============================================
# API ROUTES
# ============================================

@app.route('/api/upload_product_image', methods=['POST'])
def upload_product_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        name_parts = filename.rsplit('.', 1)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name_parts[0]}.{name_parts[1]}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        return jsonify({
            'success': True, 
            'image_url': f'/static/uploads/{unique_filename}'
        })
    
    return jsonify({'success': False, 'message': 'Invalid file type'})

@app.route('/api/products')
def get_products():
    products = Product.query.filter(Product.stock > 0).order_by(Product.created_at.desc()).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category': p.category,
        'price': p.price,
        'old_price': p.old_price,
        'image': p.image,
        'description': p.description,
        'stock': p.stock
    } for p in products])

# ============================================
# MAIN ROUTES
# ============================================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user:
            if user.locked_until and user.locked_until > datetime.utcnow():
                remaining = (user.locked_until - datetime.utcnow()).seconds
                return jsonify({'success': False, 'locked': True, 'remaining': remaining})
            
            if check_password_hash(user.password, password):
                user.login_attempts = 0
                user.locked_until = None
                db.session.commit()
                session['user_id'] = user.id
                session['username'] = user.username
                session['user_full_name'] = user.full_name
                session['role'] = getattr(user, 'role', 'customer')
                
                # Update last login time
                user.last_login = datetime.utcnow()
                db.session.commit()

                return jsonify({'success': True, 'redirect': url_for('home')})
            else:
                user.login_attempts += 1
                if user.login_attempts >= 3:
                    user.locked_until = datetime.utcnow() + timedelta(seconds=30)
                    db.session.commit()
                    return jsonify({'success': False, 'locked': True, 'remaining': 30})
                db.session.commit()
                return jsonify({'success': False, 'message': 'Invalid password'})
        else:
            return jsonify({'success': False, 'message': 'User not found'})
    
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    hashed_password = generate_password_hash(request.form['password'])
    new_user = User(
        username=request.form['username'],
        password=hashed_password,
        full_name=request.form['full_name'],
        email=request.form['email'],
        phone=request.form['phone'],
        role='customer',
        security_question=request.form['security_question'],
        security_answer=request.form['security_answer']
    )
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False, 'message': 'Username exists'})
    
@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/select_role')
def select_role():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('role_select.html', user=user)

# ============================================
# USER LOGIN STATUS API (For Welcome Animation)
# ============================================

@app.route('/api/user_login_status')
def user_login_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'})
    
    user = User.query.get(session['user_id'])
    
    # Check if user is new (first time logging in)
    is_new_user = False
    if user.last_login is None:
        is_new_user = True
    else:
        # If last_login is very old, still consider returning user
        is_new_user = False
    
    return jsonify({
        'success': True,
        'user_name': user.full_name,
        'is_new_user': is_new_user,
        'is_returning_user': not is_new_user
    })
    
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    recommendations = ml_engine.get_ai_recommendations(session['user_id'], None)
    
    # Pass user login status to template
    is_new_user = (user.last_login is None)
    
    return render_template('dashboard.html', 
                         user=user, 
                         recommendations=recommendations,
                         is_new_user=is_new_user)

@app.route('/bikes')
def bikes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get bikes from Bike table
    bikes = Bike.query.all()
    
    # Get products from Product table with category 'bike'
    from app import Product
    product_bikes = Product.query.filter_by(category='bike').all()
    
    # Combine both lists
    all_bikes = list(bikes) + list(product_bikes)
    
    return render_template('bikes.html', bikes=all_bikes)

@app.route('/bike/<bike_name>')
def bike_detail(bike_name):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    bike = Bike.query.filter_by(name=bike_name).first()
    if not bike:
        return redirect(url_for('bikes'))
    interest_score = ml_engine.predict_user_interest(session['user_id'], bike_name)
    return render_template('bike_detail.html', bike=bike, interest_score=interest_score)

@app.route('/scooters')
def scooters():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    scooters = Scooter.query.all()
    
    from app import Product
    product_scooters = Product.query.filter_by(category='scooter').all()
    
    all_scooters = list(scooters) + list(product_scooters)
    
    return render_template('scooters.html', scooters=all_scooters)

@app.route('/book_test_ride', methods=['GET', 'POST'])
def book_test_ride():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        test_ride = TestRide(
            user_id=session['user_id'],
            bike_name=request.form['bike_name'],
            test_date=request.form['test_date'],
            test_time=request.form['test_time']
        )
        db.session.add(test_ride)
        db.session.commit()
        return jsonify({'success': True})
    return render_template('book_test_ride.html', bikes=Bike.query.all())

@app.route('/book_bike', methods=['GET', 'POST'])
def book_bike():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        booking = BikeBooking(
            user_id=session['user_id'],
            bike_name=request.form['bike_name'],
            booking_date=request.form['booking_date'],
            down_payment=int(request.form['down_payment'])
        )
        db.session.add(booking)
        db.session.commit()
        return jsonify({'success': True})
    return render_template('book_bike.html', bikes=Bike.query.all())

@app.route('/my_bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    test_rides = TestRide.query.filter_by(user_id=session['user_id']).all()
    bike_bookings = BikeBooking.query.filter_by(user_id=session['user_id']).all()
    part_orders = PartOrder.query.filter_by(user_id=session['user_id']).all()
    clothing_orders = ClothingOrder.query.filter_by(user_id=session['user_id']).all()
    
    return render_template('my_bookings.html', 
                         test_rides=test_rides,
                         bike_bookings=bike_bookings,
                         part_orders=part_orders,
                         clothing_orders=clothing_orders)

@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    data = request.get_json()
    user_message = data.get('message', '').lower().strip()
    
    if any(word in user_message for word in ['hi', 'hello', 'hey']):
        response = "👋 Hello! Welcome to Kawasaki AI Assistant! How can I help you?"
    elif 'price' in user_message:
        response = "💰 Ninja 400: ₹5.50 Lakh | Ninja 650: ₹7.20 Lakh | Z900: ₹9.30 Lakh"
    elif 'test ride' in user_message:
        response = "🏍️ Book a test ride from the 'Book Test Ride' section!"
    else:
        response = "🤖 I'm your Kawasaki assistant! Ask me about bike prices, test rides, or anything!"
    
    return jsonify({'response': response})

@app.route('/api/ai_recommendations')
def api_ai_recommendations():
    if 'user_id' not in session:
        return jsonify({'recommendations': []})
    recommendations = ml_engine.get_ai_recommendations(session['user_id'], None)
    return jsonify({'recommendations': recommendations})

@app.route('/predict_price', methods=['GET', 'POST'])
def predict_price():
    predicted_price = None
    bike_details = None
    
    if request.method == 'POST':
        try:
            bike_name = request.form['bike_name']
            bike_age = float(request.form['bike_age'])
            km_driven = float(request.form['km_driven'])
            owners = int(request.form['owners'])
            original_price = float(request.form['original_price'])
            
            predictor = KawasakiPricePredictor()
            predictor.load_model()
            predicted_price = predictor.predict_price(bike_age, km_driven, owners, original_price)
            confidence = 95 - (bike_age * 2) - (owners * 3)
            confidence = max(70, min(98, confidence))
            
            bike_details = {
                'name': bike_name, 'age': bike_age, 'km_driven': km_driven,
                'owners': owners, 'original_price': original_price,
                'predicted_price': predicted_price, 'confidence': confidence,
                'depreciation': ((original_price - predicted_price) / original_price) * 100
            }
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('predict_price.html', prediction=bike_details)

@app.route('/check_session')
def check_session():
    return jsonify({'logged_in': 'user_id' in session})

@app.route('/parts')
def parts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('parts.html')

@app.route('/shop')
def shop():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('shop.html')

@app.route('/order_confirmation')
def order_confirmation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('order_confirmation.html')

@app.route('/order_confirmation_clothing')
def order_confirmation_clothing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('order_confirmation_clothing.html')

@app.route('/clothing')
def clothing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('clothing.html')

@app.route('/purchase_tools')
def purchase_tools():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('purchase_tools.html')

@app.route('/service')
def service_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('service.html')

@app.route('/racing')
def racing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('racing.html')

@app.route('/news')
def news():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('news.html')

@app.route('/green_academy')
def green_academy():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('green_academy.html')

@app.route('/heritage')
def heritage():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('heritage.html')

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    
    user = User.query.filter_by(username=username, email=email).first()
    if user:
        return jsonify({'success': True, 'message': 'Reset link sent'})
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    username = data.get('username')
    new_password = data.get('new_password')
    
    user = User.query.filter_by(username=username).first()
    if user:
        user.password = generate_password_hash(new_password)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/compare')
def compare():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('compare.html', bikes=Bike.query.all())

@app.route('/financing')
def financing():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('financing.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/compare_bikes', methods=['POST'])
def api_compare_bikes():
    data = request.get_json()
    bike_ids = [int(bike_id) for bike_id in data.get('bike_ids', []) if str(bike_id).isdigit()]
    bikes = Bike.query.filter(Bike.id.in_(bike_ids)).all()
    return jsonify([{
        'id': bike.id, 'name': bike.name, 'cc': bike.cc, 'price': bike.price,
        'power': bike.power, 'top_speed': bike.top_speed, 'mileage': bike.mileage,
        'fuel_type': bike.fuel_type, 'category': bike.category
    } for bike in bikes])

@app.route('/api/calculate_emi', methods=['POST'])
def calculate_emi():
    data = request.get_json()
    principal = float(data.get('principal', 0))
    rate = float(data.get('rate', 0)) / 100 / 12
    time = int(data.get('time', 0)) * 12
    
    if rate == 0:
        emi = principal / time if time > 0 else principal
    else:
        emi = principal * rate * (1 + rate) ** time / ((1 + rate) ** time - 1)
    
    total_amount = emi * time
    total_interest = total_amount - principal
    
    return jsonify({
        'emi': round(emi, 2),
        'total_amount': round(total_amount, 2),
        'total_interest': round(total_interest, 2)
    })

@app.route('/api/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    data = request.get_json()
    bike_name = data.get('bike_name')
    return jsonify({'success': True, 'message': f'{bike_name} added to wishlist'})

@app.route('/api/book_service', methods=['POST'])
def book_service():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    return jsonify({'success': True, 'message': 'Service booked successfully'})

@app.route('/api/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.get_json()
    product_name = data.get('product_name')
    quantity = data.get('quantity', 1)
    price = data.get('price', 0)
    payment_method = data.get('payment_method', 'unknown')
    
    try:
        order = PartOrder(
            user_id=session['user_id'],
            product_name=product_name,
            quantity=quantity,
            price=price,
            status='pending',
            admin_remarks=f'Payment: {payment_method}'
        )
        db.session.add(order)
        db.session.commit()
        return jsonify({'success': True, 'order_id': order.id})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/place_clothing_order', methods=['POST'])
def place_clothing_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    data = request.get_json()
    product_name = data.get('product_name')
    size = data.get('size', 'M')
    quantity = data.get('quantity', 1)
    price = data.get('price', 0)
    payment_method = data.get('payment_method', 'unknown')
    
    try:
        order = ClothingOrder(
            user_id=session['user_id'],
            product_name=product_name,
            size=size,
            quantity=quantity,
            price=price,
            status='pending',
            admin_remarks=f'Size: {size}, Payment: {payment_method}'
        )
        db.session.add(order)
        db.session.commit()
        return jsonify({'success': True, 'order_id': order.id})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/user_stats')
def user_stats():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    user_id = session['user_id']
    
    test_rides = TestRide.query.filter_by(user_id=user_id).count()
    bike_bookings = BikeBooking.query.filter_by(user_id=user_id).count()
    part_orders = PartOrder.query.filter_by(user_id=user_id).count()
    clothing_orders = ClothingOrder.query.filter_by(user_id=user_id).count()
    
    return jsonify({
        'success': True,
        'test_rides': test_rides,
        'bike_bookings': bike_bookings,
        'part_orders': part_orders,
        'clothing_orders': clothing_orders
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# ============================================
# IMAGE UPLOAD API
# ============================================

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    if file and allowed_file(file.filename):
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        name_parts = filename.rsplit('.', 1)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name_parts[0]}.{name_parts[1]}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'image_url': f'/static/uploads/{unique_filename}'
        })
    
    return jsonify({'success': False, 'message': 'Invalid file type. Use PNG, JPG, or JPEG'})

# ============================================
# SECURITY QUESTIONS FOR PASSWORD RESET
# ============================================

@app.route('/verify_security_question', methods=['POST'])
def verify_security_question():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    
    user = User.query.filter_by(username=username, email=email).first()
    if user and user.security_question:
        return jsonify({
            'success': True,
            'question': user.security_question
        })
    return jsonify({'success': False, 'message': 'User not found'})


@app.route('/reset_password_with_security', methods=['POST'])
def reset_password_with_security():
    data = request.get_json()
    username = data.get('username')
    answer = data.get('answer')
    new_password = data.get('new_password')
    
    user = User.query.filter_by(username=username).first()
    if user and user.security_answer and user.security_answer.lower() == answer.lower():
        user.password = generate_password_hash(new_password)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid answer'})


# ============================================
# FORGOT PASSWORD - EMAIL RESET LINK
# ============================================

import secrets
from flask import render_template_string

@app.route('/verify_user_for_reset', methods=['POST'])
def verify_user_for_reset():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    
    user = User.query.filter_by(username=username, email=email).first()
    if user:
        return jsonify({
            'success': True,
            'username': user.username,
            'email': user.email,
            'has_security_question': bool(user.security_question)
        })
    return jsonify({'success': False, 'message': 'User not found with this username and email'})


@app.route('/get_security_question', methods=['POST'])
def get_security_question():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    
    user = User.query.filter_by(username=username, email=email).first()
    if user and user.security_question:
        return jsonify({
            'success': True,
            'question': user.security_question
        })
    return jsonify({'success': False, 'message': 'Security question not found'})


@app.route('/send_reset_link', methods=['POST'])
def send_reset_link():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    
    user = User.query.filter_by(username=username, email=email).first()
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=1)
    
    user.reset_token = token
    user.token_expiry = expiry
    db.session.commit()
    
    reset_link = f"http://127.0.0.1:5000/reset_with_token?token={token}"
    
    subject = "Reset Your Kawasaki Password"
    body = f"""
Dear {user.full_name},

You requested to reset your password for your Kawasaki account.

Click the link below to reset your password (valid for 1 hour):

{reset_link}

If you did not request this, please ignore this email.

Best regards,
Kawasaki Team
"""
    
    try:
        msg = Message(subject, recipients=[email], body=body)
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Reset link sent to your email'})
    except Exception as e:
        print(f"Email error: {e}")
        return jsonify({'success': False, 'message': 'Failed to send email'})


@app.route('/reset_with_token')
def reset_with_token():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(reset_token=token).first()
    if user and user.token_expiry and user.token_expiry > datetime.utcnow():
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Reset Password - Kawasaki</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .reset-card { background: white; border-radius: 20px; padding: 40px; max-width: 450px; width: 100%; }
    </style>
</head>
<body>
    <div class="reset-card">
        <div class="text-center mb-4">
            <i class="fas fa-motorcycle fa-3x text-success"></i>
            <h3 class="mt-2">Reset Password</h3>
            <p class="text-muted">Enter your new password</p>
        </div>
        <form action="/reset_password_with_token" method="POST">
            <input type="hidden" name="token" value="{{ token }}">
            <div class="mb-3">
                <label>New Password</label>
                <input type="password" name="new_password" class="form-control" required>
            </div>
            <div class="mb-3">
                <label>Confirm Password</label>
                <input type="password" name="confirm_password" class="form-control" required>
            </div>
            <button type="submit" class="btn btn-success w-100">Reset Password</button>
        </form>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
''', token=token)
    
    return '<div class="alert alert-danger text-center m-5">Invalid or expired reset link. Please request a new one.</div>'


@app.route('/reset_password_with_token', methods=['POST'])
def reset_password_with_token():
    token = request.form.get('token')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password != confirm_password:
        return '<div class="alert alert-danger text-center m-5">Passwords do not match. <a href="/login">Go back</a></div>'
    
    user = User.query.filter_by(reset_token=token).first()
    if user and user.token_expiry and user.token_expiry > datetime.utcnow():
        user.password = generate_password_hash(new_password)
        user.reset_token = None
        user.token_expiry = None
        db.session.commit()
        return '<div class="alert alert-success text-center m-5">Password reset successfully! <a href="/login">Click here to login</a></div>'
    
    return '<div class="alert alert-danger text-center m-5">Invalid or expired reset link. <a href="/login">Go back</a></div>'


# ============================================
# IMPORT ADMIN ROUTES
# ============================================

from admin.admin_routes import *

# ============================================
# RUN THE APP
# ============================================

if __name__ == '__main__':
    app.run(debug=True)