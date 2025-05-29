from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate  # <-- Add this line

mail = Mail()
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()  # <-- Add this line
