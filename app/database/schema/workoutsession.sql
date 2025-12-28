CREATE TABLE IF NOT EXISTS workout_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Session Info
    session_name VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,  -- Calculated on session end
    
    -- Session Stats (aggregated)
    total_exercises INTEGER DEFAULT 0,
    total_sets INTEGER DEFAULT 0,
    total_reps INTEGER DEFAULT 0,
    calories_burned DECIMAL(6,2),  -- Estimated
    
    -- Status
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'cancelled')),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_workout_sessions_user ON workout_sessions(user_id);
CREATE INDEX idx_workout_sessions_date ON workout_sessions(started_at);