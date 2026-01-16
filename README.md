# FluentAI - AI-Powered Language Learning Platform


## Features

- **Placement Test**: Determine your CEFR level (A1-C2)
- **Daily Lessons**: 10-question lessons with varied question types
- **Grammar Sprint**: Time-constrained grammar practice (20 sec/question)
- **Word Sprint+**: 30-second vocabulary challenge
- **AI Speaking Practice**:
  - **Prepare Me**: 5-turn roleplay conversations with AI
  - **Talk Loop**: Open-ended free talk with real-time feedback
- **Adaptive Learning**: AI-powered content selection based on performance
- **Progress Tracking**: XP system, streaks, achievements
- **Review Mode**: Personalized quizzes based on past mistakes
- **Admin Panel**: Content management and statistics

## Tech Stack

- **Frontend**: HTML5, CSS3, Vanilla JavaScript (ES6 modules)
- **Backend**: Python 3.11+ with FastAPI
- **Database**: MySQL 8.0 (XAMPP)
- **AI Integration**: OpenAI (GPT-4, Whisper) + Google Gemini

## Installation

### Prerequisites

1. XAMPP with MySQL running
2. Python 3.11 or higher
3. pip (Python package manager)

### Setup Steps

1. **Create Database**:
   - Open phpMyAdmin (http://localhost/phpmyadmin)
   - Import the database schema:
   ```
   C:\xampp\htdocs\fluentai\database\schema.sql
   ```
   - Or run from MySQL command line:
   ```bash
   mysql -u root < C:\xampp\htdocs\fluentai\database\schema.sql
   ```

2. **Install Python Dependencies**:
   ```bash
   cd C:\xampp\htdocs\fluentai\backend
   pip install -r requirements.txt
   ```

3. **Start the Backend Server**:
   ```bash
   cd C:\xampp\htdocs\fluentai\backend
   python main.py
   ```
   The API will be available at http://localhost:8000

4. **Access the Application**:
   - Open your browser and go to: http://localhost/fluentai/frontend/
   - Or directly: http://localhost/fluentai/frontend/index.html

## Configuration

### Database Configuration

Edit `backend/config.py` if your MySQL settings differ:

```python
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = ""  # Set your MySQL password
DB_NAME = "fluentai"
```

### AI API Keys

Users can add their own API keys in the Settings page:
- **OpenAI API Key**: For GPT-4 conversation and Whisper speech-to-text
- **Google Gemini API Key**: Alternative AI provider

Get your API keys from:
- OpenAI: https://platform.openai.com/api-keys
- Google AI: https://makersuite.google.com/app/apikey


## Project Structure

```
fluentai/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # MySQL connection
│   ├── requirements.txt     # Python dependencies
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic
│   ├── models/              # Pydantic models
│   └── utils/               # Utilities
├── frontend/
│   ├── index.html           # Landing page
│   ├── css/                 # Stylesheets
│   ├── js/                  # JavaScript modules
│   └── pages/               # Application pages
├── database/
│   └── schema.sql           # MySQL schema
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Lessons
- `GET /api/lessons/daily` - Get daily lesson
- `GET /api/lessons/grammar-sprint` - Get grammar sprint
- `GET /api/lessons/word-sprint` - Get word sprint
- `POST /api/lessons/{id}/submit` - Submit answers

### Speaking
- `GET /api/speaking/scenarios` - Get roleplay scenarios
- `POST /api/speaking/roleplay/start` - Start roleplay
- `POST /api/speaking/roleplay/respond` - Send response
- `POST /api/speaking/freetalk/start` - Start free talk
- `POST /api/speaking/freetalk/respond` - Send message

### Progress
- `GET /api/progress/dashboard` - Get dashboard data
- `GET /api/progress/achievements` - Get achievements

### Settings
- `GET /api/settings/profile` - Get profile
- `PUT /api/settings/api-keys` - Update API keys

## CEFR Levels

| Level | Description |
|-------|-------------|
| A1 | Beginner |
| A2 | Elementary |
| B1 | Intermediate |
| B2 | Upper Intermediate |
| C1 | Advanced |
| C2 | Proficient |

## License

This project was created for educational purposes.

## Group Members

1. Nisa Atım
2. Selinay Levat


