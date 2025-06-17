-- Create the database
CREATE DATABASE farm2market;

-- Connect to the database
\c farm2market

-- Required extensions
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enum types
CREATE TYPE user_role AS ENUM ('farmer', 'buyer', 'admin');
CREATE TYPE product_status AS ENUM ('available', 'reserved', 'sold');
CREATE TYPE reservation_status AS ENUM ('pending', 'approved', 'rejected', 'completed');
CREATE TYPE verification_status AS ENUM ('unverified', 'pending', 'verified');

-- Users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    role user_role NOT NULL,
    language_preference VARCHAR(10) DEFAULT 'en',
    profile_picture_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Farmers
CREATE TABLE farmers (
    farmer_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    full_name VARCHAR(100) NOT NULL,
    national_id VARCHAR(50),
    national_id_image_url VARCHAR(255),
    village VARCHAR(100) NOT NULL,
    farm_location GEOGRAPHY(POINT, 4326),
    address TEXT,
    verification_status verification_status DEFAULT 'unverified',
    verification_method VARCHAR(50),
    verification_date TIMESTAMP WITH TIME ZONE,
    trust_rating NUMERIC(3,2) DEFAULT 0,
    profile_completion_percentage INTEGER DEFAULT 0,
    qr_code_url VARCHAR(255),
    bio TEXT,
    farming_methods TEXT
);

-- Buyers
CREATE TABLE buyers (
    buyer_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    full_name VARCHAR(100) NOT NULL,
    preferred_locations TEXT[]
);

-- Categories
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    icon_url VARCHAR(255)
);

-- Products
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    category_id INTEGER REFERENCES categories(category_id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL,
    quantity NUMERIC(10,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    status product_status DEFAULT 'available',
    is_organic BOOLEAN DEFAULT FALSE,
    is_fresh_today BOOLEAN DEFAULT FALSE,
    harvest_date DATE,
    image_urls VARCHAR(255)[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    location GEOGRAPHY(POINT, 4326)
);

-- Tags
CREATE TABLE tags (
    tag_id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- Product Tags
CREATE TABLE product_tags (
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
    PRIMARY KEY (product_id, tag_id)
);

-- Reservations
CREATE TABLE reservations (
    reservation_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    buyer_id INTEGER NOT NULL REFERENCES buyers(buyer_id) ON DELETE CASCADE,
    quantity NUMERIC(10,2) NOT NULL,
    status reservation_status DEFAULT 'pending',
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    pickup_time TIMESTAMP WITH TIME ZONE,
    delivery_option VARCHAR(50),
    notes TEXT
);

-- Conversations
CREATE TABLE conversations (
    conversation_id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    buyer_id INTEGER NOT NULL REFERENCES buyers(buyer_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (farmer_id, buyer_id)
);

-- Messages
CREATE TABLE messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    sender_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE
);

-- Reviews
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    reservation_id INTEGER UNIQUE REFERENCES reservations(reservation_id) ON DELETE CASCADE,
    reviewer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    farmer_id INTEGER NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Mobile Money Transactions
CREATE TABLE momo_transactions (
    transaction_id SERIAL PRIMARY KEY,
    reservation_id INTEGER REFERENCES reservations(reservation_id) ON DELETE SET NULL,
    farmer_id INTEGER NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    buyer_id INTEGER NOT NULL REFERENCES buyers(buyer_id) ON DELETE CASCADE,
    amount NUMERIC(10,2) NOT NULL,
    momo_reference VARCHAR(100) NOT NULL,
    receipt_image_url VARCHAR(255),
    transaction_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_confirmed BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMP WITH TIME ZONE
);

-- Favorites
CREATE TABLE favorites (
    favorite_id SERIAL PRIMARY KEY,
    buyer_id INTEGER NOT NULL REFERENCES buyers(buyer_id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
    farmer_id INTEGER REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (product_id IS NOT NULL AND farmer_id IS NULL) OR
        (product_id IS NULL AND farmer_id IS NOT NULL)
    )
);

-- Notifications
CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notification_type VARCHAR(50) NOT NULL,
    related_entity_type VARCHAR(50),
    related_entity_id INTEGER
);

-- Alerts
CREATE TABLE alerts (
    alert_id SERIAL PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE
);

-- Eco-farming Tips
CREATE TABLE farming_tips (
    tip_id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    language VARCHAR(10) NOT NULL,
    video_url VARCHAR(255),
    image_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    -- RECOMMEND: Add trigger to auto-update `updated_at`
);

-- Offline Operations
CREATE TABLE offline_operations (
    operation_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_synced BOOLEAN DEFAULT FALSE,
    sync_date TIMESTAMP WITH TIME ZONE
);

-- Admin Actions
CREATE TABLE admin_actions (
    action_id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id INTEGER NOT NULL,
    details TEXT,
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- App Analytics
CREATE TABLE analytics (
    metric_id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    active_users INTEGER NOT NULL DEFAULT 0,
    new_users INTEGER NOT NULL DEFAULT 0,
    new_farmers INTEGER NOT NULL DEFAULT 0,
    new_buyers INTEGER NOT NULL DEFAULT 0,
    products_listed INTEGER NOT NULL DEFAULT 0,
    reservations_made INTEGER NOT NULL DEFAULT 0,
    transactions_completed INTEGER NOT NULL DEFAULT 0,
    revenue_generated NUMERIC(15,2) NOT NULL DEFAULT 0
);

-- Indexes
CREATE INDEX idx_products_farmer ON products(farmer_id);
CREATE INDEX idx_products_location ON products USING GIST(location);
CREATE INDEX idx_farmers_location ON farmers USING GIST(farm_location);
CREATE INDEX idx_reservations_product ON reservations(product_id);
CREATE INDEX idx_reservations_buyer ON reservations(buyer_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_alerts_farmer ON alerts(farmer_id);
