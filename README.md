# Jorden Backend API

This is the robust backend service for the **Jorden** platform, built using modern Python frameworks and libraries. It uses **FastAPI** for high-performance API routing, **Prisma** as the ORM, and **PostgreSQL** as the primary database.

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database ORM**: Prisma Client Python
- **Database Engine**: PostgreSQL
- **Dependency Management**: Poetry
- **Authentication**: JWT (JSON Web Tokens) with Argon2 hashing
- **File Uploads/Storage**: Cloudinary
- **Notifications & Firebase**: Firebase Admin SDK
- **Email Services**: FastAPI-Mail
- **Containerization**: Docker

## 📁 Project Structure

```
jorden/
│
├── app/                      # Main application source code
│   ├── core/                 # Core configurations, database setup, and lifecycle events
│   ├── common/               # Shared utilities and helpers
│   ├── modules/              # Feature-based modular architecture
│   │   ├── admin/            # Administrative endpoints
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── articles/         # Article and blog management
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── auth/             # Authentication (Login, Signup)
│   │   │   ├── router.py     # API endpoints and route definitions
│   │   │   ├── schemas.py    # Pydantic models for validation
│   │   │   └── service.py    # Business logic and database interactions
│   │   ├── bugs/             # Bug reporting system
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── faq/              # Frequently Asked Questions
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── message_reports/  # Reporting abusive messages
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── messages/         # Messaging system endpoints
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── notifications/    # Firebase push & in-app notifications
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── orders/           # Order processing & tracking
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── products/         # Product catalog management
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── reports/          # General reports management
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── reviews/          # Product review endpoints
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── service_applications/ # Endpoints for applying to services
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── service_review/   # Reviews specific to services
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── services/         # Service offerings management
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   ├── settings/         # App-wide settings management
│   │   │   ├── router.py     
│   │   │   ├── schemas.py    
│   │   │   └── service.py    
│   │   └── users/            # User profile and account management
│   │       ├── router.py     
│   │       ├── schemas.py    
│   │       └── service.py    
│   └── main.py               # Application entry point & router registration
│
├── prisma/                   # Prisma database schemas and migrations
├── scripts/                  # Utility and operational scripts
├── .env                      # Environment variable configuration (Ignored in Git)
├── Dockerfile                # Docker configuration
├── pyproject.toml            # Poetry configuration & dependencies
└── firebase_credentials.json # Firebase Admin credentials (Ignored in Git)
```

## 🌐 API Modules & Endpoints Overview

The API is fully modular. The following feature routers are included in the main API instance:

- **Auth** (`app/modules/auth/router.py`): JWT generation, user registration, and authentication logic.
- **Users** (`app/modules/users/router.py`): CRUD operations for user profiles.
- **Admin** (`app/modules/admin/router.py`): Operations restricted to administrators.
- **Products** (`app/modules/products/router.py`): Endpoints for fetching, creating, and managing products.
- **Orders** (`app/modules/orders/router.py`): Order lifecycle management.
- **Reviews** (`app/modules/reviews/router.py`): Management of product ratings and comments.
- **Messages** (`app/modules/messages/router.py`): P2P or system-to-user messaging APIs.
- **Services & Applications** (`app/modules/services/router.py`, `app/modules/service_applications/router.py`): Platform services and the application process for them.
- **Notifications** (`app/modules/notifications/router.py`): Endpoints tied to FCM (Firebase Cloud Messaging).
- **Settings, FAQ, Bugs, Articles**: Content management and configuration endpoints.

*(Detailed interactive API documentation is available at `/docs` or `/redoc` when the application is running).*

## Setup & Installation

### Prerequisites
- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- PostgreSQL database
- Firebase credentials JSON file
- Cloudinary credentials

### Step-by-Step Guide

1. **Activate Poetry Environment**
   ```bash
   poetry env activate
   # OR simply use poetry shell
   ```

2. **Configure Environment Variables**
   Update the `.env` file at the root of the project with your database URL, JWT secrets, Cloudinary credentials, and Firebase config.

3. **Install Dependencies**
   ```bash
   poetry install
   ```

4. **Prisma Database Setup**
   Generate the Prisma client:
   ```bash
   poetry run prisma generate
   ```
   Push the schema to your PostgreSQL database:
   ```bash
   poetry run prisma db push
   ```

5. **Run the Development Server**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

The application will be accessible at `http://127.0.0.1:8000`. 
Visit `http://127.0.0.1:8000/docs` to view the interactive Swagger UI.

## 🗄️ Prisma Commands Cheatsheet

- `poetry run prisma generate` - Generate Prisma client
- `poetry run prisma db push` - Push schema to database
- `poetry run prisma db push --force` - Force push schema to database (Use with caution)
- `poetry run prisma db push --preview-feature` - Enable preview features
- `poetry run prisma studio` - Open Prisma Studio to view and edit data visually