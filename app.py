from flask import Flask, request, jsonify
from flask_cors import CORS
from extensions import mail
from extensions import db, jwt, migrate
from flask_socketio import SocketIO
from datetime import timedelta
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from routes.products import products_bp
from routes.farmers import farmers_bp
from routes.chat import chat_bp
from routes.reservations import reservations_bp
from services.socket_service import socketio
import eventlet

# Ensure eventlet is used for async operations
eventlet.monkey_patch()
socketio = SocketIO(cors_allowed_origins="*")  # Expose this for import

def create_app():
    # Load environment variables
    load_dotenv()

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/farm2market')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

    db.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    socketio.init_app(app)

    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

    # Email Configuration
    # app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    # app.config['MAIL_PORT'] = 587
    # app.config['MAIL_USE_TLS'] = True
    # app.config['MAIL_USERNAME'] = 'durandmassodagmail.com'
    # app.config['MAIL_PASSWORD'] = 'fsri aqou jxix iijy'
    # mail.init_app(app)

    # Import models and blueprints here, after db.init_app(app)
    from models import User, Farmer, Buyer, Product, ProductTag, Tag
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.notification_routes import notifications_bp
    from routes.analytics import analytics_bp
    from routes.transactions import transactions_bp
    from routes.alert_routes import alerts_bp
    from routes.subscription_routes import subscriptions_bp

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(farmers_bp, url_prefix='/api/farmers')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(reservations_bp, url_prefix='/api/reservations')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(transactions_bp, url_prefix='/api/transactions')
    app.register_blueprint(alerts_bp, url_prefix='/api/alerts')
    app.register_blueprint(subscriptions_bp, url_prefix='/api/subscriptions')

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "healthy"}), 200

    if __name__ == '__main__':
        with app.app_context():
            db.create_all()
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    
    return app
# This function initializes the Flask application, sets up CORS, JWT, and database configurations.