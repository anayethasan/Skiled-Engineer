<div align="center">

# ⚔️ Skiled-Engineer

### E-Learning Platform API

[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-ff1709?style=for-the-badge&logo=django&logoColor=white)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

*A production-ready REST API for an E-Learning platform featuring real-time Battle Mode, AI-powered Mistake Tracking, and a full Quiz engine.*

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Unique Features](#-unique-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Database Design](#-database-design)
- [API Endpoints](#-api-endpoints)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [User Roles & Permissions](#-user-roles--permissions)
- [Development Phases](#-development-phases)
- [License](#-license)

---

## 🎯 Overview

**Skiled-Engineer** is a fully-featured E-Learning Platform API built with Django REST Framework. It supports a complete course lifecycle — from creation by teachers, enrollment by students, quiz attempts with auto-evaluation, all the way to admin analytics and revenue tracking.

What makes it stand out is two flagship features: a **real-time Battle Mode** where two students compete head-to-head on the same quiz, and a **Mistake Tracker** that intelligently detects patterns in wrong answers and gives personalized study suggestions.

---

## 🔥 Unique Features

### ⚔️ Battle Mode
Two students compete in real-time on the same set of questions. The first student to submit a correct answer wins that round. The system handles matchmaking, question distribution, submission tracking, and winner declaration automatically.

```
Student A ──┐
            ├──▶ BattleRoom ──▶ Same Questions ──▶ First Correct = Winner 🏆
Student B ──┘
```

### 🧠 Mistake Tracker
Every wrong answer is logged and aggregated by topic. The system detects patterns and generates personalized suggestions using threshold-based rules.

```
Wrong Answer
    │
    ▼
MistakeLog (raw record)
    │
    ▼
MistakeAnalysis (aggregated per topic)
    │
    ▼
Suggestion: "You often fail in Edge Cases. Focus on boundary conditions."
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0 + Django REST Framework |
| Database | PostgreSQL 16 |
| Authentication | JWT via `djangorestframework-simplejwt` + Djoser |
| Email Verification | Djoser activation flow |
| Filtering | `django-filter` |
| Nested Routing | `drf-nested-routers` |
| Pagination | Custom `PageNumberPagination` (15/page) |
| Future | Payment Gateway (SSLCommerz / Stripe stub ready) |

---

## 🏗 Project Structure

```
Skiled-Engineer/
├── accounts/               # Custom User model, JWT auth, email verification
│   ├── models.py           # User, EmailVerificationToken
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── courses/                # Course & Department management
│   ├── models.py           # Course, Department
│   ├── serializers.py
│   ├── views.py
│   ├── filters.py
│   └── services.py
│
├── enrollments/            # Student enrollment & progress tracking
│   ├── models.py           # Enrollment
│   ├── serializers.py
│   └── views.py
│
├── quizzes/                # Quiz engine with auto-evaluation
│   ├── models.py           # Quiz, Question, QuizAttempt, QuizAnswer
│   ├── serializers.py
│   ├── views.py
│   └── services.py         # QuizService: start, submit, finish
│
├── battle/                 # Real-time battle mode
│   ├── models.py           # BattleRoom, BattleQuestion, BattleSubmission
│   ├── serializers.py
│   └── views.py
│
├── analytics/              # Mistake tracker + Admin dashboard
│   ├── models.py           # MistakeLog, MistakeAnalysis, CoursesAnalytics, Purchase
│   ├── serializers.py
│   ├── views.py
│   ├── services.py         # MistakeService, AnalyticsService, PurchaseService
│   ├── filters.py
│   ├── signals.py          # Auto-fires on wrong QuizAnswer / BattleSubmission
│   └── apps.py             # Registers signals on startup
│
├── api/                    # Shared utilities
│   ├── pagination.py       # DefaultPagination (page_size=15)
│   ├── permissions.py      # IsTeacherOrAdmin, IsOwnerOrAdmin
│   └── urls.py             # Master URL config
│
├── fixtures/
│   └── LMS_data.json       # Seed data for development
│
├── config/
│   └── settings.py
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🧱 Database Design

```
User ──────────────────────────────────────────────────────────────┐
 │ (instructor)                                                     │ (student)
 ▼                                                                  ▼
Course ──── Department                                         Enrollment
 │                                                                  │
 ▼                                                              progress (0-100)
Quiz
 │
 ├──▶ Question (options: JSON, topic, difficulty)
 │         │
 │         ├──▶ QuizAttempt ──▶ QuizAnswer
 │         │         │               │
 │         │         └───────────────┴──▶ MistakeLog ──▶ MistakeAnalysis
 │         │
 │         └──▶ BattleQuestion ──▶ BattleSubmission
 │
 └──▶ BattleRoom (player1, player2, winner)


analytics/
  CoursesAnalytics  (daily snapshots per course)
  Purchase          (payment stub — gateway-ready)
```

---

## 🔗 API Endpoints

### 🔐 Authentication — `/auth/`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/users/` | Register new user |
| `POST` | `/auth/users/activation/` | Activate account via email |
| `POST` | `/auth/jwt/create/` | Login — returns access + refresh token |
| `POST` | `/auth/jwt/refresh/` | Refresh access token |
| `POST` | `/auth/jwt/verify/` | Verify token validity |
| `POST` | `/auth/logout/` | Logout (blacklist token) |
| `GET` | `/auth/users/me/` | Get current user profile |
| `PATCH` | `/auth/users/me/` | Update profile |
| `PATCH` | `/auth/me/avatar/` | Upload / replace profile image |
| `DELETE` | `/auth/me/avatar/` | Remove profile image |
| `DELETE` | `/auth/me/deactivate/` | Deactivate own account |
| `POST` | `/auth/users/reset_password/` | Request password reset |
| `POST` | `/auth/users/reset_password_confirm/` | Confirm password reset |
| `POST` | `/auth/users/set_password/` | Change password |

---

### 📚 Courses — `/courses/`

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/courses/` | List all published courses | All |
| `POST` | `/courses/` | Create course | Teacher / Admin |
| `GET` | `/courses/{id}/` | Course detail | All |
| `PUT/PATCH` | `/courses/{id}/` | Update course | Owner / Admin |
| `DELETE` | `/courses/{id}/` | Delete course | Owner / Admin |
| `GET` | `/courses/my-courses/` | Teacher's own courses | Teacher |
| `POST` | `/courses/{id}/publish/` | Publish draft course | Owner / Admin |
| `POST` | `/courses/{id}/archive/` | Archive course | Owner / Admin |

**Filters:** `?department=`, `?status=`, `?is_free=`, `?search=`

---

### 🧪 Quizzes — `/courses/{course_pk}/quizzes/`

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/courses/{course_pk}/quizzes/` | List quizzes | Enrolled student / Teacher / Admin |
| `POST` | `/courses/{course_pk}/quizzes/` | Create quiz | Teacher (own course) / Admin |
| `GET/PUT/PATCH/DELETE` | `/courses/{course_pk}/quizzes/{id}/` | CRUD | Owner / Admin |

### ❓ Questions — `/courses/{course_pk}/quizzes/{quiz_pk}/questions/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `.../questions/` | Student: no correct_answer. Teacher/Admin: full |
| `POST` | `.../questions/` | Teacher (own quiz) / Admin |
| `GET/PUT/PATCH/DELETE` | `.../questions/{id}/` | CRUD |

### 🎯 Attempts — `/courses/{course_pk}/quizzes/{quiz_pk}/attempts/`

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `POST` | `.../attempts/start/` | Start a new attempt | Enrolled student |
| `GET` | `.../attempts/` | List attempts | Student (own) / Teacher+Admin (all) |
| `GET` | `.../attempts/{id}/` | Attempt detail with all answers | Own / Teacher / Admin |
| `POST` | `.../attempts/{id}/submit/` | Submit one answer | Attempt owner |
| `POST` | `.../attempts/{id}/finish/` | Finish attempt early | Attempt owner / Admin |

---

### 🎓 Enrollments — `/enrollments/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/enrollments/` | Student's enrolled courses |
| `POST` | `/enrollments/` | Enroll in a course |
| `GET` | `/enrollments/{id}/` | Enrollment detail |
| `PATCH` | `/enrollments/{id}/progress/` | Update progress (0-100) |
| `DELETE` | `/enrollments/{id}/` | Unenroll |

---

### ⚔️ Battle Mode — `/rooms/`

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `POST` | `/rooms/` | Create battle room (becomes player1) | Student |
| `GET` | `/rooms/` | List rooms | All |
| `GET` | `/rooms/{id}/` | Room detail | All |
| `POST` | `/rooms/{id}/join/` | Join as player2 | Student |
| `POST` | `/rooms/{id}/start/` | Start battle | player1 |
| `POST` | `/rooms/{id}/submit/` | Submit answer during battle | player1 / player2 |
| `GET` | `/rooms/{id}/questions/` | Get battle questions | player1 / player2 |
| `GET` | `/rooms/{id}/result/` | Final result + winner | All |
| `POST` | `/rooms/{id}/cancel/` | Cancel waiting room | player1 |

---

### 🧠 Mistake Tracker — `/mistakes/`

| Method | Endpoint | Description | Permission |
|---|---|---|---|
| `GET` | `/mistakes/` | Student: own logs. Admin: all | Auth |
| `GET` | `/mistakes/{id}/` | Single mistake detail | Own / Admin |
| `GET` | `/mistakes/analysis/` | Per-topic analysis + suggestions | Student |
| `GET` | `/mistakes/weak-topics/?limit=5` | Top N weakest topics | Student |

**Filters:** `?source=quiz|battle`, `?topic=`, `?from_date=`, `?to_date=`

---

### 📊 Analytics (Admin) — `/course-stats/` `/dashboard/` `/purchases/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/course-stats/` | Daily course snapshots |
| `GET` | `/course-stats/summary/?days=7` | Revenue + enrollment summary |
| `GET` | `/dashboard/` | Full admin dashboard (revenue, top students, popular courses) |
| `GET` | `/purchases/` | All purchase records |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL 16+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/skiled-engineer.git
cd skiled-engineer

# 2. Create virtual environment
python -m venv env
source env/bin/activate        # Linux/Mac
env\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your values

# 5. Run migrations
python manage.py migrate

# 6. Load seed data (optional)
python manage.py loaddata fixtures/LMS_data.json

# 7. Start development server
python manage.py runserver
```

### API Documentation
Once the server is running, visit:
- **Swagger UI:** `http://127.0.0.1:8000/swagger/`
- **ReDoc:** `http://127.0.0.1:8000/redoc/`

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database
DB_NAME=skiled_engineer
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Skiled Engineer <noreply@skiled.engineer>

# JWT
JWT_ACCESS_TOKEN_LIFETIME_DAYS=7
JWT_REFRESH_TOKEN_LIFETIME_DAYS=30

# Media
MEDIA_URL=/media/
MEDIA_ROOT=media/
```

---

## 👥 User Roles & Permissions

| Action | Student | Teacher | Admin |
|---|---|---|---|
| View published courses | ✅ | ✅ | ✅ |
| Create / edit courses | ❌ | ✅ (own only) | ✅ |
| Enroll in courses | ✅ | ❌ | ✅ |
| Attempt quizzes | ✅ (enrolled) | ❌ | ✅ |
| Create questions | ❌ | ✅ (own quiz) | ✅ |
| Battle Mode | ✅ | ❌ | ✅ |
| View mistake analysis | ✅ (own) | ❌ | ✅ (all) |
| Admin dashboard | ❌ | ❌ | ✅ |
| Manage departments | ❌ | ❌ | ✅ |
| View all purchases | ❌ | ❌ | ✅ |

---

## 📅 Development Phases

- [x] **Phase 1** — Authentication (JWT + Email Verification)
- [x] **Phase 2** — Course CRUD + Department management
- [x] **Phase 3** — Enrollment system + Progress tracking
- [x] **Phase 4** — Quiz engine (attempt, submit, auto-evaluate)
- [x] **Phase 5** — Admin dashboard + Analytics
- [x] **Phase 6** — Mistake Tracker (signals, analysis, suggestions)
- [x] **Phase 7** — Battle Mode (matchmaking, real-time submit, winner)
- [ ] **Phase 8** — Payment Gateway (SSLCommerz / Stripe)
- [ ] **Phase 9** — WebSocket (real-time battle updates)
- [ ] **Phase 10** — Testing + Optimization + Deployment

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ using Django REST Framework

</div>