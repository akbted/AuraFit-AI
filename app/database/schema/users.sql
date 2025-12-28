CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    mobile VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Personal Info
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20) CHECK (gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
    
    -- Physical Stats
    weight_kg DECIMAL(5,2),  -- in kilograms
    height_cm DECIMAL(5,2),  -- in centimeters
    blood_group VARCHAR(10) CHECK (blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', NULL)),
    
    -- Location
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    
    -- Account Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Index for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_mobile ON users(mobile);