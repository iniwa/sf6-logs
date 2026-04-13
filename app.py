from flask import Flask
from waitress import serve
from routes import register_blueprints
from routes.filters import register_filters
from services.scheduler import start_scheduler

app = Flask(__name__)
register_filters(app)
register_blueprints(app)

start_scheduler()

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8510, threads=8, ident='sf6-logs')
