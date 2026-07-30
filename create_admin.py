import sys
from app import create_app
from extensions import db
from models.user import User

def create_or_promote_admin(email, password=None, first_name="Admin", last_name="User"):
    app = create_app()
    with app.app_context():
        email_clean = email.strip().lower()
        user = User.query.filter_by(email=email_clean).first()
        
        if user:
            user.role = "admin"
            if password:
                user.set_password(password)
            db.session.commit()
            print(f"Success: Existing account '{email_clean}' promoted to admin.")
        else:
            if not password:
                print(f"Error: User '{email_clean}' does not exist. Please provide a password to create the account.")
                print("Usage: python create_admin.py <email> <password> [first_name] [last_name]")
                sys.exit(1)
            
            new_user = User(
                email=email_clean,
                first_name=first_name,
                last_name=last_name,
                role="admin"
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            print(f"Success: New admin account created for '{email_clean}'.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python create_admin.py <email> [password] [first_name] [last_name]")
        sys.exit(1)
    
    email_arg = sys.argv[1]
    pass_arg = sys.argv[2] if len(sys.argv) > 2 else None
    fname_arg = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    lname_arg = sys.argv[4] if len(sys.argv) > 4 else "User"
    
    create_or_promote_admin(email_arg, pass_arg, fname_arg, lname_arg)
