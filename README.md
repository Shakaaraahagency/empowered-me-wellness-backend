# Empowered Me Wellness - Backend

This is the backend API for the Empowered Me Wellness application. It is built with Python and Flask and serves as the core engine for user authentication, class bookings, e-commerce, blogging, and more.

## Tech Stack
- **Framework:** Flask (Python 3)
- **Database:** PostgreSQL (with SQLAlchemy ORM)
- **Migrations:** Flask-Migrate (Alembic)
- **Authentication:** JWT (Flask-JWT-Extended)
- **Payments:** Stripe
- **Emails:** Resend
- **Media Storage:** Cloudinary
- **Error Tracking:** Sentry

## Features
- **Authentication & Authorization:** Secure user registration, login, JWT refresh logic, and admin roles.
- **Classes & Bookings:** APIs to manage and book wellness sessions and classes.
- **E-Commerce:** Products, shopping cart checkout integration via Stripe, digital downloads, and product reviews.
- **Blog Management:** APIs to manage blog posts and related media.
- **Testimonials & Newsletters:** Capture feedback and manage newsletter subscriptions.
- **Admin Dashboard:** Comprehensive endpoints for admins to track stats, manage users, bookings, orders, and content.

## Setup Instructions

1. **Clone the repository and enter the backend directory.**

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root backend directory (you can use `.env.example` as a template) and configure your credentials for:
   - `FLASK_ENV` (development/production)
   - Database connection URL
   - JWT and Secret Keys
   - Stripe API Keys
   - Cloudinary & Resend API credentials
   - Sentry DSN

5. **Run Database Migrations:**
   ```bash
   flask db upgrade
   ```
   *Note: If running `python app.py` directly, database tables and migrations are automatically ensured on startup.*

6. **Create an Admin Account:**
   Make sure you have registered a regular user first, then grant them admin privileges via the CLI:
   ```bash
   flask create-admin your.email@example.com
   ```

7. **Start the Development Server:**
   ```bash
   flask run
   ```
   Or run directly:
   ```bash
   python app.py
   ```

## Deployment
For production, ensure all environment variables are correctly set (especially `DATABASE_URL`, `SECRET_KEY`, and `JWT_SECRET_KEY`). The application can be served using Gunicorn:
```bash
gunicorn app:app
```
