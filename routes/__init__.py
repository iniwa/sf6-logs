from routes import dashboard, overlay, settings, api, report


def register_blueprints(app):
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(overlay.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(report.bp)
