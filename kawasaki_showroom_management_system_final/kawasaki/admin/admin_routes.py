from flask import render_template, redirect, url_for, session, jsonify, request, Response
from app import app, db, User, Bike, Scooter, BikeBooking, TestRide, PartOrder, ClothingOrder, send_order_status_email, AdminOTP, send_otp_email
from datetime import datetime, timedelta
import random
import csv
from io import StringIO

# ============================================
# ADMIN VERIFICATION WITH OTP
# ============================================

@app.route('/verify_admin', methods=['POST'])
def verify_admin():
    data = request.get_json()
    password = data.get('password')
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    if password == 'admin123':
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        admin_email = 'lokeshm00070@gmail.com'
        
        try:
            otp_record = AdminOTP(email=admin_email, otp=otp_code, expires_at=expires_at, is_used=False)
            db.session.add(otp_record)
            db.session.commit()
        except Exception as e:
            print(f"Database error: {e}")
        
        try:
            send_otp_email(admin_email, 'Kawasaki Admin', otp_code)
        except Exception as e:
            print(f"Email error: {e}")
        
        session['admin_password_verified'] = True
        session['admin_email'] = admin_email
        
        return jsonify({'success': True, 'requires_otp': True})
    else:
        return jsonify({'success': False, 'message': 'Invalid password'})


@app.route('/admin/verify_otp', methods=['POST'])
def verify_admin_otp():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    if not session.get('admin_password_verified', False):
        return jsonify({'success': False, 'message': 'Please verify password first'})
    
    data = request.get_json()
    entered_otp = data.get('otp')
    admin_email = session.get('admin_email', 'lokeshm00070@gmail.com')
    
    try:
        otp_record = AdminOTP.query.filter_by(email=admin_email, otp=entered_otp, is_used=False).first()
        
        if otp_record and otp_record.expires_at > datetime.utcnow():
            otp_record.is_used = True
            db.session.commit()
            session['admin_verified'] = True
            session.pop('admin_password_verified', None)
            session.pop('admin_email', None)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Invalid or expired OTP'})
    except Exception as e:
        print(f"OTP error: {e}")
        return jsonify({'success': False, 'message': 'Error verifying OTP'})


@app.route('/admin/resend_otp', methods=['POST'])
def resend_admin_otp():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    if not session.get('admin_password_verified', False):
        return jsonify({'success': False, 'message': 'Please verify password first'})
    
    admin_email = 'lokeshm00070@gmail.com'
    
    try:
        old_otps = AdminOTP.query.filter_by(email=admin_email, is_used=False).all()
        for old in old_otps:
            old.is_used = True
        db.session.commit()
        
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        otp_record = AdminOTP(email=admin_email, otp=otp_code, expires_at=expires_at, is_used=False)
        db.session.add(otp_record)
        db.session.commit()
        send_otp_email(admin_email, 'Kawasaki Admin', otp_code)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Resend error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/admin/otp_page')
def admin_otp_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not session.get('admin_password_verified', False):
        return redirect(url_for('select_role'))
    return render_template('otp_verify.html')


# ============================================
# ADMIN DASHBOARD
# ============================================

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if not session.get('admin_verified', False):
        return redirect(url_for('select_role'))
    user = User.query.get(session['user_id'])
    return render_template('admin_dashboard.html', user=user)


# ============================================
# ADMIN STATISTICS API
# ============================================

@app.route('/admin/stats')
def admin_stats():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    return jsonify({
        'pending_testrides': TestRide.query.filter_by(status='pending').count(),
        'pending_bookings': BikeBooking.query.filter_by(status='pending').count(),
        'pending_orders': PartOrder.query.filter_by(status='pending').count(),
        'total_users': User.query.count(),
        'approved_testrides': TestRide.query.filter_by(status='approved').count(),
        'rejected_testrides': TestRide.query.filter_by(status='rejected').count(),
        'approved_bookings': BikeBooking.query.filter_by(status='approved').count(),
        'rejected_bookings': BikeBooking.query.filter_by(status='rejected').count(),
        'total_parts_orders': PartOrder.query.count(),
        'total_clothing_orders': ClothingOrder.query.count()
    })


# ============================================
# ADMIN USERS MANAGEMENT
# ============================================

@app.route('/admin/users')
def admin_users():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    users = User.query.all()
    return jsonify([{
        'id': u.id, 'username': u.username, 'full_name': u.full_name,
        'email': u.email, 'phone': u.phone, 'role': getattr(u, 'role', 'customer'),
        'created_at': u.created_at.strftime('%Y-%m-%d') if hasattr(u, 'created_at') and u.created_at else '-'
    } for u in users])


@app.route('/admin/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    user = User.query.get(user_id)
    if user and user.username != 'admin':
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Cannot delete admin user'})


# ============================================
# ADMIN BOOKINGS MANAGEMENT
# ============================================

@app.route('/admin/bookings')
def admin_bookings():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    bookings = db.session.query(BikeBooking, User).join(User, BikeBooking.user_id == User.id).order_by(BikeBooking.created_at.desc()).all()
    return jsonify([{
        'id': b.BikeBooking.id, 'username': b.User.username, 'bike_name': b.BikeBooking.bike_name,
        'booking_date': b.BikeBooking.booking_date if b.BikeBooking.booking_date else b.BikeBooking.created_at.strftime('%Y-%m-%d'),
        'down_payment': b.BikeBooking.down_payment, 'status': b.BikeBooking.status if hasattr(b.BikeBooking, 'status') else 'pending',
        'admin_remarks': getattr(b.BikeBooking, 'admin_remarks', '') or ''
    } for b in bookings])


# ============================================
# ADMIN TEST RIDES MANAGEMENT
# ============================================

@app.route('/admin/testrides')
def admin_testrides():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    rides = db.session.query(TestRide, User).join(User, TestRide.user_id == User.id).order_by(TestRide.booking_date.desc()).all()
    return jsonify([{
        'id': r.TestRide.id, 'username': r.User.username, 'bike_name': r.TestRide.bike_name,
        'test_date': r.TestRide.test_date, 'test_time': r.TestRide.test_time,
        'status': r.TestRide.status if hasattr(r.TestRide, 'status') else 'pending',
        'admin_remarks': getattr(r.TestRide, 'admin_remarks', '') or ''
    } for r in rides])


# ============================================
# ADMIN ORDERS MANAGEMENT
# ============================================

@app.route('/admin/orders')
def admin_orders():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    orders = db.session.query(PartOrder, User).join(User, PartOrder.user_id == User.id).order_by(PartOrder.order_date.desc()).all()
    return jsonify([{
        'id': o.PartOrder.id, 'username': o.User.username, 'product_name': o.PartOrder.product_name,
        'quantity': o.PartOrder.quantity, 'size': 'N/A', 'color': 'N/A',
        'price': o.PartOrder.quantity * o.PartOrder.price, 'status': o.PartOrder.status,
        'admin_remarks': o.PartOrder.admin_remarks or ''
    } for o in orders])


# ============================================
# ADMIN CLOTHING ORDERS MANAGEMENT (FIXED)
# ============================================

@app.route('/admin/clothing_orders')
def admin_clothing_orders():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    orders = db.session.query(ClothingOrder, User).join(User, ClothingOrder.user_id == User.id).order_by(ClothingOrder.order_date.desc()).all()
    
    result = []
    for order, user in orders:
        result.append({
            'id': order.id,
            'username': user.username,
            'product_name': order.product_name,
            'size': order.size,
            'quantity': order.quantity,
            'price': order.price,
            'total': order.quantity * order.price,
            'status': order.status,
            'admin_remarks': order.admin_remarks or ''
        })
    
    return jsonify(result)


# ============================================
# UPDATE STATUS WITH EMAIL
# ============================================

@app.route('/admin/update_status', methods=['POST'])
def update_status():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    data = request.get_json()
    item_type = data.get('type')
    item_id = data.get('id')
    new_status = data.get('status')
    remarks = data.get('remarks', '')
    
    type_map = {
        'testride': (TestRide, "Test Ride"),
        'booking': (BikeBooking, "Bike Booking"),
        'order': (PartOrder, "Parts Order"),
        'clothing': (ClothingOrder, "Clothing Order")
    }
    
    if item_type not in type_map:
        return jsonify({'success': False, 'message': 'Invalid type'})
    
    Model, order_type = type_map[item_type]
    item = Model.query.get(item_id)
    
    if item:
        user = User.query.get(item.user_id)
        item.status = new_status
        if remarks:
            item.admin_remarks = remarks
        db.session.commit()
        
        if user and user.email:
            send_order_status_email(user.email, user.full_name, order_type, item.id, new_status)
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Item not found'})


# ============================================
# PRODUCT MANAGEMENT
# ============================================

def get_product_model():
    from app import Product
    return Product

@app.route('/admin/products')
def admin_products():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    Product = get_product_model()
    products = Product.query.order_by(Product.created_at.desc()).all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'category': p.category, 'price': p.price,
        'old_price': p.old_price, 'stock': p.stock, 'featured': p.featured,
        'image': p.image, 'description': p.description
    } for p in products])


@app.route('/admin/product/add', methods=['POST'])
def admin_add_product():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    Product = get_product_model()
    data = request.get_json()
    
    product = Product(
        name=data.get('name'),
        category=data.get('category'),
        price=data.get('price'),
        old_price=data.get('old_price'),
        description=data.get('description'),
        image=data.get('image'),
        stock=data.get('stock', 0),
        featured=data.get('featured', False),
        cc=data.get('cc', 0),
        top_speed=data.get('top_speed', 0),
        mileage=data.get('mileage', 0.0),
        power=data.get('power', ''),
        features=data.get('features', '')
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({'success': True, 'id': product.id})


@app.route('/admin/product/edit/<int:product_id>', methods=['PUT'])
def admin_edit_product(product_id):
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    Product = get_product_model()
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'})
    
    data = request.get_json()
    product.name = data.get('name', product.name)
    product.price = data.get('price', product.price)
    product.old_price = data.get('old_price', product.old_price)
    product.stock = data.get('stock', product.stock)
    product.description = data.get('description', product.description)
    product.featured = data.get('featured', product.featured)
    product.image = data.get('image', product.image)
    
    product.cc = data.get('cc', product.cc)
    product.top_speed = data.get('top_speed', product.top_speed)
    product.mileage = data.get('mileage', product.mileage)
    product.power = data.get('power', product.power)
    product.features = data.get('features', product.features)
    
    db.session.commit()
    return jsonify({'success': True})


@app.route('/admin/product/delete/<int:product_id>', methods=['DELETE'])
def admin_delete_product(product_id):
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    Product = get_product_model()
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})


# ============================================
# RECENT ORDERS API
# ============================================

@app.route('/admin/recent_orders')
def admin_recent_orders():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    orders = []
    parts = PartOrder.query.order_by(PartOrder.order_date.desc()).limit(10).all()
    for o in parts:
        user = User.query.get(o.user_id)
        orders.append({
            'id': o.id, 'customer': user.full_name if user else 'Unknown', 'type': 'Parts',
            'product': o.product_name, 'amount': o.quantity * o.price,
            'date': o.order_date.strftime('%Y-%m-%d'), 'status': o.status
        })
    return jsonify(orders[:10])


# ============================================
# RECENT USERS API
# ============================================

@app.route('/admin/recent_users')
def admin_recent_users():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    users = User.query.order_by(User.id.desc()).limit(10).all()
    return jsonify([{
        'id': u.id, 'name': u.full_name, 'email': u.email, 'phone': u.phone,
        'date': u.created_at.strftime('%Y-%m-%d') if hasattr(u, 'created_at') and u.created_at else '-'
    } for u in users])


# ============================================
# CHART DATA API
# ============================================

@app.route('/admin/chart_data')
def admin_chart_data():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    return jsonify({
        'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'revenue': [125000, 145000, 168000, 192000, 215000, 245000],
        'pending': PartOrder.query.filter_by(status='pending').count() + BikeBooking.query.filter_by(status='pending').count(),
        'approved': PartOrder.query.filter_by(status='approved').count() + BikeBooking.query.filter_by(status='approved').count(),
        'rejected': PartOrder.query.filter_by(status='rejected').count() + BikeBooking.query.filter_by(status='rejected').count()
    })


# ============================================
# EXPORT ORDERS API
# ============================================

@app.route('/admin/export_orders')
def admin_export_orders():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    orders = PartOrder.query.order_by(PartOrder.order_date.desc()).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order ID', 'Customer', 'Product', 'Quantity', 'Price', 'Total', 'Date', 'Status'])
    
    for o in orders:
        user = User.query.get(o.user_id)
        writer.writerow([o.id, user.full_name if user else 'Unknown', o.product_name, o.quantity, o.price, o.quantity * o.price, o.order_date.strftime('%Y-%m-%d'), o.status])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=orders_export.csv'
    return response


# ============================================
# ADMIN DASHBOARD WIDGET DATA
# ============================================

@app.route('/admin/widget_data')
def admin_widget_data():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    return jsonify({
        'total_bikes': Bike.query.count(),
        'total_scooters': Scooter.query.count(),
        'total_parts_orders': PartOrder.query.count(),
        'total_clothing_orders': ClothingOrder.query.count()
    })


# ============================================
# BULK UPDATE CLOTHING
# ============================================

@app.route('/admin/bulk_update_clothing', methods=['POST'])
def bulk_update_clothing():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    data = request.get_json()
    ids = data.get('ids', [])
    new_status = data.get('status')
    
    count = 0
    for item_id in ids:
        item = ClothingOrder.query.get(item_id)
        if item:
            item.status = new_status
            count += 1
            
            user = User.query.get(item.user_id)
            if user and user.email:
                send_order_status_email(
                    user_email=user.email,
                    user_name=user.full_name,
                    order_type="Clothing Order",
                    order_id=item.id,
                    new_status=new_status
                )
    
    db.session.commit()
    return jsonify({'success': True, 'count': count})


# ============================================
# BULK UPDATE PARTS ORDERS
# ============================================

@app.route('/admin/bulk_update_status', methods=['POST'])
def bulk_update_status():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    data = request.get_json()
    ids = data.get('ids', [])
    new_status = data.get('status')
    
    count = 0
    for item_id in ids:
        item = PartOrder.query.get(item_id)
        if item:
            item.status = new_status
            count += 1
    
    db.session.commit()
    return jsonify({'success': True, 'count': count})


# ============================================
# DOWNLOAD REPORTS
# ============================================

@app.route('/admin/download_testrides')
def download_testrides():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User', 'Bike Name', 'Test Date', 'Test Time', 'Status', 'Booking Date'])
    
    rides = db.session.query(TestRide, User).join(User, TestRide.user_id == User.id).all()
    for ride, user in rides:
        writer.writerow([ride.id, user.username, ride.bike_name, ride.test_date, ride.test_time, ride.status, ride.booking_date.strftime('%Y-%m-%d %H:%M')])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=test_rides_report.csv'
    return response


@app.route('/admin/download_bookings')
def download_bookings():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User', 'Bike Name', 'Booking Date', 'Down Payment', 'Status'])
    
    bookings = db.session.query(BikeBooking, User).join(User, BikeBooking.user_id == User.id).all()
    for booking, user in bookings:
        writer.writerow([booking.id, user.username, booking.bike_name, booking.booking_date, booking.down_payment, booking.status])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=bike_bookings_report.csv'
    return response


@app.route('/admin/download_parts_orders')
def download_parts_orders():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User', 'Product', 'Quantity', 'Price', 'Total', 'Order Date', 'Status'])
    
    orders = db.session.query(PartOrder, User).join(User, PartOrder.user_id == User.id).all()
    for order, user in orders:
        writer.writerow([order.id, user.username, order.product_name, order.quantity, order.price, order.quantity * order.price, order.order_date.strftime('%Y-%m-%d %H:%M'), order.status])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=parts_orders_report.csv'
    return response


@app.route('/admin/download_clothing_orders')
def download_clothing_orders():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User', 'Product', 'Size', 'Quantity', 'Price', 'Total', 'Order Date', 'Status'])
    
    orders = db.session.query(ClothingOrder, User).join(User, ClothingOrder.user_id == User.id).all()
    for order, user in orders:
        writer.writerow([order.id, user.username, order.product_name, order.size, order.quantity, order.price, order.quantity * order.price, order.order_date.strftime('%Y-%m-%d %H:%M'), order.status])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=clothing_orders_report.csv'
    return response


@app.route('/admin/download_users')
def download_users():
    if not session.get('admin_verified', False):
        return jsonify({'error': 'Unauthorized'})
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Username', 'Full Name', 'Email', 'Phone', 'Role', 'Registered Date'])
    
    users = User.query.all()
    for user in users:
        writer.writerow([user.id, user.username, user.full_name, user.email, user.phone, user.role, user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else '-'])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=users_report.csv'
    return response