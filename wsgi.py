"""WSGI entry point for production servers (Render runs `gunicorn wsgi:app`)."""
from run import app

application = app

if __name__ == "__main__":
    app.run()
