CREATE TABLE IF NOT EXISTS exercise_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES workout_sessions(id) ON DELETE CASCADE,
    
    -- Exercise Info
    exercise_type VARCHAR(50) NOT NULL CHECK (exercise_type IN (
        'pushups', 'squats', 'crunches', 'leg_raises', 'plank'
    )),
    set_number INTEGER NOT NULL,
    
    -- For Rep-based exercises (pushups, squats, crunches, leg_raises)
    reps INTEGER,
    
    -- For Timed exercises (plank)
    duration_seconds INTEGER,
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_exercise_sets_session ON exercise_sets(session_id);
CREATE INDEX idx_exercise_sets_type ON exercise_sets(exercise_type);