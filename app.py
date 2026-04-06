from flask import Flask
from routes import register_blueprints
from routes.filters import register_filters
from services.scheduler import start_scheduler

app = Flask(__name__)
register_filters(app)
register_blueprints(app)

start_scheduler()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8510, debug=False)
