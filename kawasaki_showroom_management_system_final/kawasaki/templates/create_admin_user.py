from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Check if user exists
    user = User.query.filter_by(username='lokesh').first()
    
    if user:
        print(f"User found: {user.username}")
        print(f"Current role: {user.role}")
        print(f"Password hash: {user.password}")
        
        # Update to admin and reset password
        user.role = 'admin'
        user.password = generate_password_hash('admin123')
        db.session.commit()
        print("User updated to admin with password 'admin123'")
    else:
        # Create new admin user
        new_admin = User(
            username='lokesh',
            password=generate_password_hash('admin123'),
            full_name='Admin Lokesh',
            email='lokesh@kawasaki.com',
            phone='9999999999',
            role='admin'
        )
        db.session.add(new_admin)
        db.session.commit()
        print("Admin user created with username 'lokesh' and password 'admin123'")
    
    # Verify
    verify = User.query.filter_by(username='lokesh').first()
    print(f"\nVerification:")
    print(f"Username: {verify.username}")
    print(f"Role: {verify.role}")