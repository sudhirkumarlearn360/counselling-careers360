-- =====================================================================================
-- CounselQueue database guide: a SELECT for every table, plus handy joins.
-- Database: SQLite  backend/db.sqlite3      Run:  sqlite3 -header -column backend/db.sqlite3 < docs/DATABASE_GUIDE.sql
--   or interactively:  sqlite3 -header -column backend/db.sqlite3   then paste a query.
-- Works on MySQL too (same table/column names). Column details: backend/SCHEMA.md
-- Secrets (password hash, OTP code_hash, access_key) are left out of the SELECTs on purpose.
--
-- Relationships:
--   centres_centre 1-1 centres_centresettings, 1-1 queue_tokensequence
--   centres_centre 1-* counsellors_posting *-1 counsellors_counsellor   (the desk roster)
--   centres_centre 1-* queue_student *-1 counsellors_counsellor          (one row per token)
--   queue_student 1-* queue_sessionrecord / queue_note / queue_auditevent / messaging_message
--   accounts_staffuser *-0..1 centres_centre (reception), 0..1-0..1 counsellors_counsellor
-- Enums: role = ops_lead | reception | counsellor ; centre.status = planned | live | closed ;
--   posting.duty = on_desk | on_break | off_duty ; student.status = waiting | called | in_session | done | ...
-- =====================================================================================


-- ============================ 1. CENTRES ============================================

-- centres_centre: one row per counselling drive (city + venue + date)
SELECT id, slug, city, venue, date, opens_at, closes_at, expected_students, status, front_desk_phone, created_at
FROM centres_centre
ORDER BY date;

-- centres_centresettings: per-centre queue tuning
SELECT s.id, c.slug AS centre, s.target_session_min, s.wait_sla_min, s.recall_limit, s.whatsapp_enabled
FROM centres_centresettings s JOIN centres_centre c ON c.id = s.centre_id;

-- queue_tokensequence: last token number issued per centre (never goes back)
SELECT t.id, c.slug AS centre, t.last_number
FROM queue_tokensequence t JOIN centres_centre c ON c.id = t.centre_id;


-- ============================ 2. COUNSELLORS ========================================

-- counsellors_counsellor: people who counsel (streams is a JSON list e.g. ["PCM","PCMB"])
SELECT id, name, mobile, streams, expected_session_min, created_at
FROM counsellors_counsellor
ORDER BY name;

-- counsellors_posting: which counsellor sits at which desk of which centre, and their duty state
SELECT p.id, c.slug AS centre, p.desk_label, k.name AS counsellor, p.duty
FROM counsellors_posting p
JOIN centres_centre c ON c.id = p.centre_id
JOIN counsellors_counsellor k ON k.id = p.counsellor_id
ORDER BY c.slug, p.desk_label;


-- ============================ 3. STAFF LOGINS =======================================

-- accounts_staffuser: CMS users (password hash not shown)
SELECT u.id, u.email, u.name, u.role, u.title, u.is_active, u.last_login,
       c.slug AS reception_centre, k.name AS counsellor
FROM accounts_staffuser u
LEFT JOIN centres_centre c ON c.id = u.centre_id
LEFT JOIN counsellors_counsellor k ON k.id = u.counsellor_id
ORDER BY u.role, u.email;

-- accounts_loginattempt: failed-login counter per email (lockout)
SELECT id, email, failed_count, last_failed_at FROM accounts_loginattempt;


-- ============================ 4. STUDENTS / QUEUE ===================================

-- queue_student: one row per token (the main table)
SELECT s.id, c.slug AS centre, s.token, s.source, s.status, s.name, s.mobile, s.parent_mobile, s.email,
       s.school, s.klass, s.stream, s.course, s.exams, s.clarity, s.help,
       k.name AS counsellor, s.priority, s.checkin_at, s.queue_at, s.called_at, s.started_at, s.ended_at,
       s.recalls, s.rating, s.outcome, s.follow_up_on, s.consent, s.consent_at
FROM queue_student s
JOIN centres_centre c ON c.id = s.centre_id
LEFT JOIN counsellors_counsellor k ON k.id = s.counsellor_id
ORDER BY c.slug, s.token;

-- queue_sessionrecord: history, one row per completed session (waits/durations come from here)
SELECT r.id, c.slug AS centre, s.token, s.name AS student, k.name AS counsellor, r.outcome,
       r.queue_at, r.called_at, r.started_at, r.ended_at
FROM queue_sessionrecord r
JOIN queue_student s ON s.id = r.student_id
JOIN centres_centre c ON c.id = r.centre_id
JOIN counsellors_counsellor k ON k.id = r.counsellor_id
ORDER BY r.ended_at DESC;

-- queue_note: counsellor notes on a student
SELECT n.id, s.token, s.name AS student, n.author_name, n.text, n.created_at
FROM queue_note n JOIN queue_student s ON s.id = n.student_id
ORDER BY n.created_at DESC;

-- queue_auditevent: who did what (actor NULL = the student acted; student NULL = centre-level event)
SELECT a.id, a.at, a.verb, c.slug AS centre, s.token, u.email AS actor, k.name AS on_behalf_of, a.data
FROM queue_auditevent a
JOIN centres_centre c ON c.id = a.centre_id
LEFT JOIN queue_student s ON s.id = a.student_id
LEFT JOIN accounts_staffuser u ON u.id = a.actor_id
LEFT JOIN counsellors_counsellor k ON k.id = a.on_behalf_of_id
ORDER BY a.at DESC;


-- ============================ 5. MESSAGING / OTP ====================================

-- messaging_message: WhatsApp messages (stub provider: nothing really sent)
SELECT m.id, m.created_at, m."to", m.template, m.status, m.failure_reason, s.token, m.body
FROM messaging_message m LEFT JOIN queue_student s ON s.id = m.student_id
ORDER BY m.created_at DESC;

-- messaging_otpcode: OTP attempts (code hash not shown)
SELECT o.id, c.slug AS centre, o.mobile, o.created_at, o.expires_at, o.attempts,
       o.verified_at, o.invalidated_at, o.verification_used_at
FROM messaging_otpcode o JOIN centres_centre c ON c.id = o.centre_id
ORDER BY o.created_at DESC;


-- ============================ 6. FRAMEWORK TABLES (Django) ==========================

SELECT id, name FROM auth_group;
SELECT id, group_id, permission_id FROM auth_group_permissions;
SELECT id, name, codename, content_type_id FROM auth_permission;
SELECT id, app_label, model FROM django_content_type;
SELECT id, app, name, applied FROM django_migrations ORDER BY id;
SELECT session_key, expire_date FROM django_session;                    -- admin sessions
SELECT id, action_time, user_id, content_type_id, object_repr, action_flag, change_message FROM django_admin_log;
SELECT id, staffuser_id, group_id FROM accounts_staffuser_groups;
SELECT id, staffuser_id, permission_id FROM accounts_staffuser_user_permissions;
SELECT id, user_id, jti, created_at, expires_at FROM token_blacklist_outstandingtoken;   -- issued JWT refresh tokens
SELECT id, blacklisted_at, token_id FROM token_blacklist_blacklistedtoken;                -- signed-out refresh tokens


-- ============================ 7. USEFUL REPORTS =====================================

-- Row count of every app table
SELECT 'centres_centre' t, COUNT(*) n FROM centres_centre UNION ALL
SELECT 'counsellors_counsellor', COUNT(*) FROM counsellors_counsellor UNION ALL
SELECT 'counsellors_posting', COUNT(*) FROM counsellors_posting UNION ALL
SELECT 'accounts_staffuser', COUNT(*) FROM accounts_staffuser UNION ALL
SELECT 'queue_student', COUNT(*) FROM queue_student UNION ALL
SELECT 'queue_sessionrecord', COUNT(*) FROM queue_sessionrecord UNION ALL
SELECT 'queue_note', COUNT(*) FROM queue_note UNION ALL
SELECT 'queue_auditevent', COUNT(*) FROM queue_auditevent UNION ALL
SELECT 'messaging_message', COUNT(*) FROM messaging_message UNION ALL
SELECT 'messaging_otpcode', COUNT(*) FROM messaging_otpcode;

-- Students per centre by status
SELECT c.slug AS centre, s.status, COUNT(*) AS students
FROM queue_student s JOIN centres_centre c ON c.id = s.centre_id
GROUP BY c.slug, s.status ORDER BY c.slug;

-- Who is waiting right now at a centre, in queue order (change the slug)
SELECT s.token, s.name, s.stream, k.name AS counsellor, s.queue_at
FROM queue_student s
JOIN centres_centre c ON c.id = s.centre_id
LEFT JOIN counsellors_counsellor k ON k.id = s.counsellor_id
WHERE c.slug = 'gwalior-demo' AND s.status = 'waiting'
ORDER BY s.priority DESC, s.queue_at;

-- Load per counsellor at a centre
SELECT k.name AS counsellor, p.desk_label, p.duty,
       SUM(s.status = 'waiting') AS waiting, SUM(s.status = 'in_session') AS in_session
FROM counsellors_posting p
JOIN centres_centre c ON c.id = p.centre_id
JOIN counsellors_counsellor k ON k.id = p.counsellor_id
LEFT JOIN queue_student s ON s.centre_id = p.centre_id AND s.counsellor_id = p.counsellor_id
WHERE c.slug = 'gwalior-demo'
GROUP BY k.name, p.desk_label, p.duty;

-- Find a student by mobile (student or parent)
SELECT c.slug AS centre, s.token, s.name, s.status
FROM queue_student s JOIN centres_centre c ON c.id = s.centre_id
WHERE s.mobile = '9000010001' OR s.parent_mobile = '9000010001';

-- Average wait and session length per counsellor (minutes; SQLite julianday, use TIMESTAMPDIFF on MySQL)
SELECT k.name AS counsellor, COUNT(*) AS sessions,
       ROUND(AVG((julianday(r.called_at) - julianday(r.queue_at)) * 1440), 1) AS avg_wait_min,
       ROUND(AVG((julianday(r.ended_at) - julianday(r.started_at)) * 1440), 1) AS avg_session_min
FROM queue_sessionrecord r JOIN counsellors_counsellor k ON k.id = r.counsellor_id
GROUP BY k.name;
