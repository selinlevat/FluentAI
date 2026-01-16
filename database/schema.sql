-- FluentAI Database Schema
-- MySQL 8.0 compatible

CREATE DATABASE IF NOT EXISTS fluentai 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE fluentai;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    cefr_level ENUM('A1', 'A2', 'B1', 'B2', 'C1', 'C2') DEFAULT NULL,
    xp_total INT DEFAULT 0,
    current_streak INT DEFAULT 0,
    longest_streak INT DEFAULT 0,
    role ENUM('student', 'admin') DEFAULT 'student',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL,
    INDEX idx_email (email),
    INDEX idx_cefr_level (cefr_level)
) ENGINE=InnoDB;

-- User settings table (API keys, preferences)
CREATE TABLE IF NOT EXISTS user_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    openai_api_key TEXT DEFAULT NULL,
    gemini_api_key TEXT DEFAULT NULL,
    preferred_ai ENUM('openai', 'gemini') DEFAULT 'openai',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    daily_goal_minutes INT DEFAULT 15,
    study_days JSON DEFAULT NULL,
    reminder_time TIME DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Lesson packs (grouped lessons)
CREATE TABLE IF NOT EXISTS lesson_packs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    cefr_level ENUM('A1', 'A2', 'B1', 'B2', 'C1', 'C2') NOT NULL,
    order_index INT DEFAULT 0,
    icon VARCHAR(10) DEFAULT '📚',
    is_locked BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_cefr_level (cefr_level),
    INDEX idx_order (order_index)
) ENGINE=InnoDB;

-- Lessons table
CREATE TABLE IF NOT EXISTS lessons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pack_id INT DEFAULT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    type ENUM('daily', 'grammar_sprint', 'word_sprint', 'placement', 'transition', 'review') DEFAULT 'daily',
    cefr_level ENUM('A1', 'A2', 'B1', 'B2', 'C1', 'C2') NOT NULL,
    xp_reward INT DEFAULT 50,
    questions_count INT DEFAULT 10,
    order_index INT DEFAULT 0,
    is_locked BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pack_id) REFERENCES lesson_packs(id) ON DELETE SET NULL,
    INDEX idx_type (type),
    INDEX idx_cefr_level (cefr_level),
    INDEX idx_pack (pack_id)
) ENGINE=InnoDB;

-- Questions table
CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lesson_id INT DEFAULT NULL,
    type ENUM('mcq', 'gap_fill', 'matching', 'picture_word', 'word_picture', 'translation', 'listening', 'reorder', 'true_false') DEFAULT 'mcq',
    content JSON NOT NULL,
    correct_answer JSON NOT NULL,
    skill_tag ENUM('grammar', 'vocabulary', 'pronunciation', 'speaking', 'listening', 'reading') DEFAULT 'grammar',
    difficulty INT DEFAULT 1,
    xp_value INT DEFAULT 10,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE,
    INDEX idx_lesson (lesson_id),
    INDEX idx_skill (skill_tag),
    INDEX idx_difficulty (difficulty)
) ENGINE=InnoDB;

-- User progress tracking
CREATE TABLE IF NOT EXISTS user_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    lesson_id INT DEFAULT 0,
    score INT DEFAULT 0,
    xp_earned INT DEFAULT 0,
    answers JSON,
    completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    time_spent_seconds INT DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_lesson (lesson_id),
    INDEX idx_completed (completed_at)
) ENGINE=InnoDB;

-- Vocabulary lists (for review)
CREATE TABLE IF NOT EXISTS vocabulary_lists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    word VARCHAR(100) NOT NULL,
    translation TEXT,
    mistake_count INT DEFAULT 0,
    mastered BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_word (user_id, word),
    INDEX idx_user (user_id),
    INDEX idx_mastered (mastered)
) ENGINE=InnoDB;

-- Achievements/Badges
CREATE TABLE IF NOT EXISTS achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    badge_type VARCHAR(50) NOT NULL,
    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_badge (user_id, badge_type),
    INDEX idx_user (user_id)
) ENGINE=InnoDB;

-- Conversation history (for AI speaking sessions)
CREATE TABLE IF NOT EXISTS conversation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_type ENUM('roleplay', 'freetalk') NOT NULL,
    messages JSON,
    scores JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_type (session_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- Insert default admin user (password: admin123)
INSERT INTO users (email, password_hash, name, role, cefr_level, xp_total) 
VALUES ('admin@lingualearn.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VUy0y3Y9z3XKlO', 'Admin', 'admin', 'C2', 10000)
ON DUPLICATE KEY UPDATE name = 'Admin';

-- Insert admin settings
INSERT INTO user_settings (user_id, notifications_enabled, daily_goal_minutes)
SELECT id, TRUE, 15 FROM users WHERE email = 'admin@lingualearn.com'
ON DUPLICATE KEY UPDATE notifications_enabled = TRUE;

-- Insert sample lesson packs
INSERT INTO lesson_packs (title, description, cefr_level, order_index, icon) VALUES
('Basics 1', 'Start your English journey with fundamental vocabulary', 'A1', 1, '🌱'),
('Greetings', 'Learn to say hello, goodbye, and introduce yourself', 'A1', 2, '👋'),
('Family', 'Family members and relationships vocabulary', 'A1', 3, '👨‍👩‍👧‍👦'),
('Numbers & Time', 'Count, tell time, and discuss dates', 'A1', 4, '🔢'),
('Food & Drinks', 'Order food, discuss meals, and restaurant vocabulary', 'A2', 5, '🍕'),
('Travel', 'Airport, hotel, and transportation vocabulary', 'A2', 6, '✈️'),
('Shopping', 'Buying things and discussing prices', 'A2', 7, '🛒'),
('Past Tense', 'Talk about past events and experiences', 'B1', 8, '⏰'),
('Future Plans', 'Discuss plans, goals, and predictions', 'B1', 9, '🎯'),
('Business English', 'Professional communication and workplace vocabulary', 'B2', 10, '💼'),
('Advanced Grammar', 'Complex grammatical structures', 'C1', 11, '📚')
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- Insert sample lessons
INSERT INTO lessons (pack_id, title, description, type, cefr_level, xp_reward, order_index) VALUES
(1, 'First Words', 'Learn your first English words', 'daily', 'A1', 50, 1),
(1, 'Basic Phrases', 'Essential everyday phrases', 'daily', 'A1', 50, 2),
(1, 'Colors', 'Learn the colors', 'daily', 'A1', 50, 3),
(2, 'Hello & Goodbye', 'Greeting people', 'daily', 'A1', 50, 1),
(2, 'Nice to Meet You', 'Introducing yourself', 'daily', 'A1', 50, 2),
(3, 'Parents & Siblings', 'Immediate family', 'daily', 'A1', 50, 1),
(5, 'At the Restaurant', 'Ordering food', 'daily', 'A2', 60, 1),
(6, 'At the Airport', 'Travel vocabulary', 'daily', 'A2', 60, 1),
(NULL, 'Placement Test', 'Determine your English level', 'placement', 'A1', 0, 0),
(NULL, 'Grammar Sprint Challenge', 'Quick grammar practice', 'grammar_sprint', 'A1', 30, 0),
(NULL, 'Word Sprint Challenge', 'Vocabulary speed round', 'word_sprint', 'A1', 25, 0)
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- Insert sample questions for Basics 1 - First Words
INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value) VALUES
(1, 'mcq', '{"question": "What is the English word for \\"merhaba\\"?", "options": ["Hello", "Goodbye", "Thanks", "Sorry"]}', '"Hello"', 'vocabulary', 1, 10),
(1, 'mcq', '{"question": "Choose the correct greeting:", "options": ["Good morning", "Good night", "Goodbye", "Sorry"]}', '"Good morning"', 'vocabulary', 1, 10),
(1, 'gap_fill', '{"sentence": "Nice to ___ you!", "options": ["meet", "see", "look", "watch"]}', '"meet"', 'grammar', 1, 10),
(1, 'mcq', '{"question": "The opposite of \\"yes\\" is:", "options": ["no", "maybe", "yes", "ok"]}', '"no"', 'vocabulary', 1, 10),
(1, 'mcq', '{"question": "How do you say \\"teşekkürler\\" in English?", "options": ["Thank you", "Please", "Sorry", "Hello"]}', '"Thank you"', 'vocabulary', 1, 10),
(1, 'mcq', '{"question": "\\"Please\\" is used to:", "options": ["Make a polite request", "Say goodbye", "Apologize", "Greet someone"]}', '"Make a polite request"', 'vocabulary', 1, 10),
(1, 'gap_fill', '{"sentence": "My name ___ John.", "options": ["is", "are", "am", "be"]}', '"is"', 'grammar', 1, 10),
(1, 'mcq', '{"question": "Which word means \\"evet\\"?", "options": ["Yes", "No", "Maybe", "Never"]}', '"Yes"', 'vocabulary', 1, 10),
(1, 'translation', '{"question": "Translate: Good night", "options": ["İyi geceler", "Günaydın", "İyi akşamlar", "Merhaba"]}', '"İyi geceler"', 'vocabulary', 1, 10),
(1, 'mcq', '{"question": "Complete: How ___ you?", "options": ["are", "is", "am", "be"]}', '"are"', 'grammar', 1, 10)
ON DUPLICATE KEY UPDATE content = VALUES(content);

-- Insert questions for placement test
INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "She ___ to school every day.", "options": ["go", "goes", "going", "gone"]}', '"goes"', 'grammar', 1, 5
FROM lessons l WHERE l.type = 'placement' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "I ___ watching TV when you called.", "options": ["am", "was", "were", "is"]}', '"was"', 'grammar', 2, 5
FROM lessons l WHERE l.type = 'placement' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "They have lived here ___ 2010.", "options": ["for", "since", "during", "while"]}', '"since"', 'grammar', 3, 5
FROM lessons l WHERE l.type = 'placement' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "If I ___ you, I would study harder.", "options": ["am", "was", "were", "be"]}', '"were"', 'grammar', 4, 5
FROM lessons l WHERE l.type = 'placement' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "The opposite of \\"hot\\" is:", "options": ["warm", "cold", "cool", "heat"]}', '"cold"', 'vocabulary', 1, 5
FROM lessons l WHERE l.type = 'placement' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

-- More grammar sprint questions
INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "She ___ breakfast every morning.", "options": ["eat", "eats", "eating", "eaten"]}', '"eats"', 'grammar', 1, 5
FROM lessons l WHERE l.type = 'grammar_sprint' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "They ___ to Paris last summer.", "options": ["go", "goes", "went", "going"]}', '"went"', 'grammar', 2, 5
FROM lessons l WHERE l.type = 'grammar_sprint' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

-- Word sprint questions
INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "Synonym of \\"fast\\":", "options": ["slow", "quick", "late", "early"]}', '"quick"', 'vocabulary', 1, 5
FROM lessons l WHERE l.type = 'word_sprint' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

INSERT INTO questions (lesson_id, type, content, correct_answer, skill_tag, difficulty, xp_value)
SELECT l.id, 'mcq', '{"question": "A place to buy medicine:", "options": ["bakery", "pharmacy", "library", "bank"]}', '"pharmacy"', 'vocabulary', 2, 5
FROM lessons l WHERE l.type = 'word_sprint' LIMIT 1
ON DUPLICATE KEY UPDATE content = VALUES(content);

SELECT 'Database schema created successfully!' as status;
