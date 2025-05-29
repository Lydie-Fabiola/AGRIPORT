from extensions import db  # <-- absolute import
from datetime import datetime
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from geoalchemy2 import Geography

class UserRole(Enum):
    FARMER = 'farmer'
    BUYER = 'buyer'
    ADMIN = 'admin'

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # <-- match your SQL schema
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    role = db.Column(db.Enum('farmer', 'buyer', 'admin', name='user_role'), nullable=False)
    language_preference = db.Column(db.String(10), default='en')
    profile_picture_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True))
    last_login = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)  # <-- add this line

    farmer = db.relationship('Farmer', back_populates='user', uselist=False)
    buyer = db.relationship('Buyer', backref='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Farmer(db.Model):
    __tablename__ = 'farmers'
    farmer_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    profile_photo_url = db.Column(db.String(255))
    village = db.Column(db.String(100))
    phone_number = db.Column(db.String(20), nullable=True)
    trust_rating = db.Column(db.Float, default=0.0)
    national_id_number = db.Column(db.String(50))
    national_id_image_url = db.Column(db.String(255))
    verification_status = db.Column(db.Enum('unverified', 'pending', 'verified', name='verification_status'), default='unverified')
    verification_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='farmer')

class Buyer(db.Model):
    __tablename__ = 'buyers'

    buyer_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    preferred_locations = db.Column(db.ARRAY(db.String))
    preferred_products = db.Column(db.ARRAY(db.String))

class Product(db.Model):
    __tablename__ = 'products'
    
    product_id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.farmer_id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Enum('available', 'reserved', 'sold', name='product_status'), default='available')
    is_organic = db.Column(db.Boolean, default=False)
    is_fresh_today = db.Column(db.Boolean, default=False)
    harvest_date = db.Column(db.Date)
    image_urls = db.Column(db.ARRAY(db.String(255)))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    location = db.Column(Geography(geometry_type='POINT', srid=4326))
    
    # Relationships
    farmer = db.relationship('Farmer', back_populates='products')
    category = db.relationship('Category', back_populates='products')
    tags = db.relationship('Tag', secondary='product_tags', back_populates='products')
    
    def to_dict(self):
        return {
            'product_id': self.product_id,
            'farmer_id': self.farmer_id,
            'category_id': self.category_id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'quantity': float(self.quantity),
            'unit': self.unit,
            'status': self.status,
            'is_organic': self.is_organic,
            'is_fresh_today': self.is_fresh_today,
            'harvest_date': self.harvest_date.isoformat() if self.harvest_date else None,
            'image_urls': self.image_urls,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'location': {
                'lat': self.location.x if self.location else None,
                'lng': self.location.y if self.location else None
            } if self.location else None,
            'tags': [tag.name for tag in self.tags]
        }

class ProductTag(db.Model):
    __tablename__ = 'product_tags'
    
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.tag_id'), primary_key=True)

class Conversation(db.Model):
    __tablename__ = 'conversations'
    conversation_id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.farmer_id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('buyers.buyer_id'), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = db.relationship('Message', backref='conversation', lazy=True)

class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.conversation_id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class Tag(db.Model):
    __tablename__ = 'tags'
    tag_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', secondary='product_tags', back_populates='tags')


class Reservation(db.Model):
    __tablename__ = 'reservations'
    reservation_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('buyers.buyer_id'), nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'rejected', 'completed', name='reservation_status'), default='pending')
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add relationships if needed

class Notification(db.Model):
    __tablename__ = 'notifications'
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g. 'message', 'reservation', 'order', 'weather'
    title = db.Column(db.String(100))
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    data = db.Column(db.JSON, nullable=True)  # For extra info (e.g., reservation_id)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    feedback_id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.farmer_id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('buyers.buyer_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    transaction_id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.reservation_id'), unique=True, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.farmer_id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('buyers.buyer_id'), nullable=False)
    momo_amount = db.Column(db.Numeric(10,2), nullable=False)
    momo_date = db.Column(db.DateTime, nullable=False)
    momo_receipt_url = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum('pending', 'confirmed', 'rejected', name='transaction_status'), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reservation = db.relationship('Reservation', backref='transaction')
    farmer = db.relationship('Farmer', backref='transactions')
    buyer = db.relationship('Buyer', backref='transactions')

class DeviceToken(db.Model):
    __tablename__ = 'device_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True)
    platform = db.Column(db.String(20))  # 'android', 'ios', 'web'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alert(db.Model):
    __tablename__ = 'alerts'
    alert_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'weather', 'pest', 'practice'
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    region = db.Column(db.String(100), nullable=True)  # e.g., 'Bamenda'
    crop = db.Column(db.String(50), nullable=True)     # e.g., 'maize'
    severity = db.Column(db.String(20), nullable=True) # e.g., 'info', 'warning', 'critical'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class FarmerSubscription(db.Model):
    __tablename__ = 'farmer_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.farmer_id'), nullable=False)
    region = db.Column(db.String(100), nullable=True)
    crop = db.Column(db.String(50), nullable=True)