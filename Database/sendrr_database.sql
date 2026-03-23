-- ============================================================
--  Sendrr Webmail App -- Database Setup
--  Drop this file in your /database folder and run it once.
--  It creates all tables and loads dummy data to test with.
-- ============================================================

-- Create the database itself and select it
CREATE DATABASE IF NOT EXISTS sendrr;
USE sendrr;


-- ============================================================
--  TABLE: users
--  Stores every registered account on the platform.
--  NOTE: passwords are stored as plain text here -- a real
--  production app would hash these, but we're keeping it simple.
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id     INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,         -- the part before @sendrr.com
    email       VARCHAR(100) NOT NULL UNIQUE,         -- full address, e.g. john@sendrr.com
    password    VARCHAR(100) NOT NULL,                -- plain text (no hashing)
    region      VARCHAR(10)  NOT NULL DEFAULT 'NA',   -- matches the dropdown in signup
    is_admin    TINYINT(1)   NOT NULL DEFAULT 0,      -- 0 = regular user, 1 = admin
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
--  TABLE: emails
--  Every message sent between sendrr accounts lives here.
--  sender_id and recipient_id both point back to users.user_id.
-- ============================================================
CREATE TABLE IF NOT EXISTS emails (
    email_id    INT AUTO_INCREMENT PRIMARY KEY,
    sender_id   INT          NOT NULL,
    recipient_id INT         NOT NULL,
    subject     VARCHAR(255) NOT NULL DEFAULT '(no subject)',
    body        TEXT         NOT NULL,
    sent_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_read     TINYINT(1)   NOT NULL DEFAULT 0,      -- 0 = unread, 1 = read

    FOREIGN KEY (sender_id)    REFERENCES users(user_id),
    FOREIGN KEY (recipient_id) REFERENCES users(user_id)
);


-- ============================================================
--  TABLE: sessions
--  Created when a user logs in, deleted (or marked inactive)
--  when they log out. The admin panel reads this table to show
--  login activity across all accounts.
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT          NOT NULL,
    session_token VARCHAR(255) NOT NULL,              -- random string generated at login
    ip_address   VARCHAR(45),                         -- IPv4 or IPv6
    login_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    logout_at    DATETIME,                            -- NULL means session is still active
    is_active    TINYINT(1)   NOT NULL DEFAULT 1,     -- 1 = logged in, 0 = logged out

    FOREIGN KEY (user_id) REFERENCES users(user_id)
);


-- ============================================================
--  No seed data -- all tables start completely empty.
--  Create accounts through the signup page as normal.
--  There is no limit on how many accounts can be made.
-- ============================================================


-- ============================================================
--  Quick sanity check queries -- run these to confirm setup
-- ============================================================

-- See all users (admin panel would use something like this)
-- SELECT user_id, username, email, region, is_admin, created_at FROM users;

-- See all emails with sender/recipient names instead of IDs
-- SELECT e.email_id, s.username AS sender, r.username AS recipient,
--        e.subject, e.sent_at, e.is_read
-- FROM emails e
-- JOIN users s ON e.sender_id   = s.user_id
-- JOIN users r ON e.recipient_id = r.user_id;

-- See active sessions (admin panel login activity view)
-- SELECT s.session_id, u.username, s.ip_address, s.login_at, s.is_active
-- FROM sessions s
-- JOIN users u ON s.user_id = u.user_id
-- ORDER BY s.login_at DESC;
