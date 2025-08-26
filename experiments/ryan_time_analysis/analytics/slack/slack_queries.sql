-- =====================================================
-- Slack Analytics SQL Queries Reference
-- Generated for Ryan Marien Time Analysis Experiment
-- =====================================================

-- DATABASE SETUP AND INITIALIZATION QUERIES
-- SETUP QUERIES
-- ==================================================

-- CREATE SLACK MESSAGES TABLE
-- ------------------------------
CREATE OR REPLACE TABLE slack_messages AS 
                SELECT * FROM read_csv_auto('slack_messages.csv');

-- CREATE SLACK CHANNELS TABLE
-- ------------------------------
CREATE OR REPLACE TABLE slack_channels AS 
                SELECT * FROM read_csv_auto('slack_channels.csv');

-- CREATE SLACK USERS TABLE
-- ------------------------------
CREATE OR REPLACE TABLE slack_users AS 
                SELECT * FROM read_csv_auto('slack_users.csv');

-- ADD COMPUTED COLUMNS
-- ------------------------------
ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_ryan_message BOOLEAN;
                ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_dm BOOLEAN;
                ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_business_hours BOOLEAN;
                ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_after_hours BOOLEAN;
                ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_thread_reply BOOLEAN;
                ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS message_length INTEGER;
                
                UPDATE slack_messages SET 
                    is_ryan_message = (user_id = 'UBL74SKU0'),
                    is_dm = (channel_name = 'Direct Message'),
                    is_business_hours = (hour >= 9 AND hour <= 17 AND day_of_week NOT IN ('Saturday', 'Sunday')),
                    is_after_hours = NOT (hour >= 9 AND hour <= 17 AND day_of_week NOT IN ('Saturday', 'Sunday')),
                    is_thread_reply = (thread_ts IS NOT NULL AND thread_ts != ''),
                    message_length = LENGTH(text);


-- CORE ANALYTICAL VIEWS FOR SLACK COMMUNICATION ANALYSIS
-- ANALYTICAL VIEWS
-- ==================================================

-- V MESSAGE VOLUME
-- ------------------------------
CREATE OR REPLACE VIEW v_message_volume AS
                SELECT 
                    date,
                    hour,
                    day_of_week,
                    week,
                    month,
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                    COUNT(CASE WHEN is_dm THEN 1 END) as dm_messages,
                    COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_messages,
                    COUNT(CASE WHEN is_thread_reply THEN 1 END) as thread_messages,
                    AVG(message_length) as avg_message_length
                FROM slack_messages
                GROUP BY date, hour, day_of_week, week, month
                ORDER BY date, hour;

-- V CHANNEL ACTIVITY
-- ------------------------------
CREATE OR REPLACE VIEW v_channel_activity AS
                SELECT 
                    m.channel_name,
                    COUNT(m.message_id) as actual_total_messages,
                    COUNT(CASE WHEN m.is_ryan_message THEN 1 END) as actual_ryan_messages,
                    COUNT(CASE WHEN NOT m.is_ryan_message THEN 1 END) as others_messages,
                    ROUND(COUNT(CASE WHEN m.is_ryan_message THEN 1 END) * 100.0 / COUNT(m.message_id), 1) as ryan_participation_pct,
                    COUNT(DISTINCT m.user_id) as unique_participants,
                    COUNT(CASE WHEN m.is_thread_reply THEN 1 END) as thread_messages,
                    COUNT(CASE WHEN m.is_business_hours THEN 1 END) as business_hours_messages,
                    COUNT(CASE WHEN m.is_after_hours THEN 1 END) as after_hours_messages,
                    AVG(m.message_length) as avg_message_length,
                    MIN(m.datetime) as first_message_time,
                    MAX(m.datetime) as last_message_time
                FROM slack_messages m
                GROUP BY m.channel_name
                ORDER BY actual_total_messages DESC;

-- V COMMUNICATION INTENSITY
-- ------------------------------
CREATE OR REPLACE VIEW v_communication_intensity AS
                SELECT 
                    date,
                    day_of_week,
                    COUNT(*) as total_daily_messages,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_daily_messages,
                    COUNT(DISTINCT channel_id) as active_channels,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(CASE WHEN is_dm THEN 1 END) as dm_count,
                    COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_count,
                    COUNT(CASE WHEN is_thread_reply THEN 1 END) as thread_replies,
                    COUNT(CASE WHEN is_business_hours THEN 1 END) as business_hours_msgs,
                    COUNT(CASE WHEN is_after_hours THEN 1 END) as after_hours_msgs,
                    ROUND(COUNT(CASE WHEN is_after_hours THEN 1 END) * 100.0 / COUNT(*), 1) as after_hours_pct,
                    COUNT(DISTINCT CASE WHEN is_ryan_message THEN channel_id END) as ryan_channels_active
                FROM slack_messages
                GROUP BY date, day_of_week
                ORDER BY date;

-- V SLACK LOAD HEATMAP
-- ------------------------------
CREATE OR REPLACE VIEW v_slack_load_heatmap AS
                SELECT 
                    day_of_week,
                    hour,
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                    COUNT(CASE WHEN is_dm THEN 1 END) as dm_messages,
                    COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_messages,
                    COUNT(CASE WHEN is_business_hours THEN 1 END) as business_hours_messages,
                    ROUND(COUNT(CASE WHEN is_ryan_message THEN 1 END) * 100.0 / COUNT(*), 1) as ryan_participation_pct,
                    COUNT(*) / COUNT(DISTINCT date) as avg_messages_per_day_hour,
                    CASE 
                        WHEN hour >= 9 AND hour <= 17 AND day_of_week NOT IN ('Saturday', 'Sunday') THEN 'Business Hours'
                        WHEN hour >= 18 AND hour <= 22 THEN 'Evening'
                        WHEN hour >= 6 AND hour <= 8 THEN 'Early Morning'
                        ELSE 'Off Hours'
                    END as time_period
                FROM slack_messages
                GROUP BY day_of_week, hour
                ORDER BY 
                    CASE day_of_week 
                        WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 
                        WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 
                        WHEN 'Sunday' THEN 7 
                    END, hour;

-- V STRATEGIC VS OPERATIONAL
-- ------------------------------
CREATE OR REPLACE VIEW v_strategic_vs_operational AS
                SELECT 
                    channel_name,
                    date,
                    day_of_week,
                    hour,
                    CASE 
                        WHEN channel_name IN ('executive-team', 'leadership') THEN 'Strategic'
                        WHEN channel_name IN ('product-strategy') THEN 'Strategic-Product'
                        WHEN channel_name IN ('engineering', 'marketing') THEN 'Operational'
                        WHEN channel_name = 'Direct Message' THEN 'Mixed'
                        ELSE 'Other'
                    END as communication_category,
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                    COUNT(CASE WHEN is_thread_reply THEN 1 END) as threaded_messages,
                    AVG(message_length) as avg_message_length,
                    COUNT(CASE WHEN is_business_hours THEN 1 END) as business_hours_msgs,
                    COUNT(CASE WHEN is_after_hours THEN 1 END) as after_hours_msgs,
                    CASE 
                        WHEN COUNT(CASE WHEN is_ryan_message THEN 1 END) > 0 
                        THEN AVG(CASE WHEN is_ryan_message THEN message_length END)
                        ELSE 0 
                    END as ryan_avg_message_length
                FROM slack_messages
                GROUP BY channel_name, date, day_of_week, hour
                ORDER BY date, hour, channel_name;


-- KEY METRIC EXTRACTION QUERIES FOR EXECUTIVE REPORTING
-- KEY METRICS QUERIES
-- ==================================================

-- BASIC STATISTICS
-- ------------------------------
SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                    COUNT(DISTINCT channel_id) as total_channels,
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(DISTINCT date) as total_days,
                    ROUND(COUNT(CASE WHEN is_ryan_message THEN 1 END) * 100.0 / COUNT(*), 1) as ryan_percentage
                FROM slack_messages;

-- TEMPORAL PATTERNS
-- ------------------------------
SELECT 
                    SUM(CASE WHEN is_business_hours AND is_ryan_message THEN 1 END) as business_hours_messages,
                    SUM(CASE WHEN is_after_hours AND is_ryan_message THEN 1 END) as after_hours_messages,
                    ROUND(SUM(CASE WHEN is_after_hours AND is_ryan_message THEN 1 END) * 100.0 / 
                          SUM(CASE WHEN is_ryan_message THEN 1 END), 1) as after_hours_percentage
                FROM slack_messages;

-- COMMUNICATION PREFERENCES
-- ------------------------------
SELECT 
                    SUM(CASE WHEN is_dm AND is_ryan_message THEN 1 END) as dm_messages,
                    SUM(CASE WHEN NOT is_dm AND is_ryan_message THEN 1 END) as channel_messages,
                    ROUND(SUM(CASE WHEN is_dm AND is_ryan_message THEN 1 END) * 100.0 / 
                          SUM(CASE WHEN is_ryan_message THEN 1 END), 1) as dm_percentage
                FROM slack_messages;

-- PEAK ACTIVITY HOURS
-- ------------------------------
SELECT 
                    hour,
                    day_of_week,
                    SUM(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages
                FROM slack_messages
                GROUP BY hour, day_of_week
                ORDER BY ryan_messages DESC
                LIMIT 10;

-- TOP COLLABORATION PARTNERS
-- ------------------------------
SELECT 
                    u.real_name as collaborator,
                    COUNT(*) as total_interactions,
                    COUNT(CASE WHEN m.is_dm THEN 1 END) as dm_interactions,
                    COUNT(CASE WHEN NOT m.is_dm THEN 1 END) as channel_interactions
                FROM slack_messages m
                JOIN slack_users u ON m.user_id = u.user_id
                WHERE u.real_name != 'Ryan Marien' AND u.real_name IS NOT NULL
                GROUP BY u.real_name
                ORDER BY total_interactions DESC
                LIMIT 10;

-- STRATEGIC COMMUNICATION BREAKDOWN
-- ------------------------------
SELECT 
                    CASE 
                        WHEN channel_name IN ('executive-team', 'leadership') THEN 'Strategic'
                        WHEN channel_name IN ('product-strategy') THEN 'Strategic-Product'
                        WHEN channel_name IN ('engineering', 'marketing') THEN 'Operational'
                        WHEN channel_name = 'Direct Message' THEN 'Mixed'
                        ELSE 'Other'
                    END as communication_category,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                    ROUND(COUNT(CASE WHEN is_ryan_message THEN 1 END) * 100.0 / 
                          (SELECT COUNT(*) FROM slack_messages WHERE is_ryan_message = true), 1) as percentage
                FROM slack_messages
                GROUP BY communication_category
                ORDER BY ryan_messages DESC;


-- PERFORMANCE AND EFFICIENCY ANALYSIS QUERIES
-- PERFORMANCE QUERIES
-- ==================================================

-- DAILY MESSAGE INTENSITY
-- ------------------------------
SELECT 
                    date,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as daily_messages,
                    COUNT(DISTINCT CASE WHEN is_ryan_message THEN channel_id END) as channels_used,
                    ROUND(COUNT(CASE WHEN is_after_hours AND is_ryan_message THEN 1 END) * 100.0 / 
                          COUNT(CASE WHEN is_ryan_message THEN 1 END), 1) as after_hours_pct
                FROM slack_messages
                GROUP BY date
                ORDER BY date;

-- CONTEXT SWITCHING ANALYSIS
-- ------------------------------
SELECT 
                    date,
                    COUNT(DISTINCT CASE WHEN is_ryan_message THEN channel_id END) as channels_active,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as total_messages,
                    CASE 
                        WHEN COUNT(DISTINCT CASE WHEN is_ryan_message THEN channel_id END) >= 4 THEN 'High Switching'
                        WHEN COUNT(DISTINCT CASE WHEN is_ryan_message THEN channel_id END) >= 2 THEN 'Moderate Switching'
                        ELSE 'Focused'
                    END as switching_level
                FROM slack_messages
                GROUP BY date
                ORDER BY channels_active DESC;

-- COMMUNICATION EFFICIENCY SCORE
-- ------------------------------
WITH daily_metrics AS (
                    SELECT 
                        date,
                        COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                        COUNT(CASE WHEN is_dm AND is_ryan_message THEN 1 END) as dm_messages,
                        COUNT(CASE WHEN is_after_hours AND is_ryan_message THEN 1 END) as after_hours_messages,
                        COUNT(DISTINCT CASE WHEN is_ryan_message THEN channel_id END) as channels_used
                    FROM slack_messages
                    GROUP BY date
                )
                SELECT 
                    date,
                    ryan_messages,
                    ROUND(dm_messages * 100.0 / ryan_messages, 1) as dm_percentage,
                    ROUND(after_hours_messages * 100.0 / ryan_messages, 1) as after_hours_percentage,
                    channels_used,
                    -- Efficiency score calculation
                    ROUND((
                        LEAST(100, (dm_messages * 100.0 / ryan_messages) * 2) +  -- DM preference
                        GREATEST(0, 100 - (after_hours_messages * 100.0 / ryan_messages) * 2) +  -- Time management
                        GREATEST(0, 100 - (channels_used - 1) * 20)  -- Focus score
                    ) / 3, 1) as efficiency_score
                FROM daily_metrics
                WHERE ryan_messages > 0
                ORDER BY efficiency_score DESC;


