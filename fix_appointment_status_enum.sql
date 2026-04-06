-- Fix appointment status enum to use lowercase values
-- This script fixes the PostgreSQL enum type to match the SQLAlchemy model

-- First, let's see what the current enum values are
-- SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'appointmentstatus');

-- Step 0: Drop the default to avoid casting issues
ALTER TABLE scheduled_appointments ALTER COLUMN status DROP DEFAULT;

-- Step 1: Update all data to lowercase values
UPDATE scheduled_appointments SET status = 'scheduled' WHERE status = 'SCHEDULED';
UPDATE scheduled_appointments SET status = 'confirmed' WHERE status = 'CONFIRMED';
UPDATE scheduled_appointments SET status = 'checked_in' WHERE status = 'CHECKED_IN';
UPDATE scheduled_appointments SET status = 'in_progress' WHERE status = 'IN_PROGRESS';
UPDATE scheduled_appointments SET status = 'cancelled' WHERE status = 'CANCELLED';
UPDATE scheduled_appointments SET status = 'completed' WHERE status = 'COMPLETED';
UPDATE scheduled_appointments SET status = 'no_show' WHERE status = 'NO_SHOW';
UPDATE scheduled_appointments SET status = 'rescheduled' WHERE status = 'RESCHEDULED';

-- Step 2: Create new enum type with lowercase values
CREATE TYPE appointmentstatus_new AS ENUM (
    'scheduled', 
    'confirmed', 
    'checked_in', 
    'in_progress', 
    'cancelled', 
    'completed', 
    'no_show', 
    'rescheduled'
);

-- Step 3: Alter the column to use the new type
ALTER TABLE scheduled_appointments 
ALTER COLUMN status TYPE appointmentstatus_new 
USING status::text::appointmentstatus_new;

-- Step 4: Drop the old enum type
DROP TYPE IF EXISTS appointmentstatus;

-- Step 5: Rename the new type to the original name
ALTER TYPE appointmentstatus_new RENAME TO appointmentstatus;

-- Step 6: Restore the default value
ALTER TABLE scheduled_appointments 
ALTER COLUMN status SET DEFAULT 'scheduled'::appointmentstatus;

-- Verify the fix
-- SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'appointmentstatus');
