from flask import Flask
from settings import Config
from extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from cad.views import cad_bp
    from admin.views import admin_bp
    app.register_blueprint(cad_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    with app.app_context():
        from cad.models import Lead, User
        db.create_all()
        # Create default admin if none exists
        if not User.query.first():
            user = User(email="admin@example.com")
            user.set_password("admin123")  # change in prod
            db.session.add(user)
            db.session.commit()

    return app

app = create_app()
