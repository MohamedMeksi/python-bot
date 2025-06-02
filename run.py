import logging

from app import create_app

app = create_app()

if __name__ == "__main__":
    logging.info("Flask app started")
    print("---------------------------------------------------------")
    print("Flask application is running and accessible at 0.0.0.0:8000")
    print("---------------------------------------------------------")
    app.run(host="0.0.0.0", port=8000)