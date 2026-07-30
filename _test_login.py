from app import create_app, db
app = create_app()
with app.app_context():
    from app.models import User
    users = User.query.all()
    print(f'Database path: {app.config["SQLALCHEMY_DATABASE_URI"]}')
    print(f'Users found: {len(users)}')
    for u in users:
        print(f'  - {u.username} ({u.email}) role={u.role} approved={u.is_approved} active={u.is_active}')
    print("All columns:", [c.name for c in User.__table__.columns])
