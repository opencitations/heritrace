from flask import Flask


def register_blueprints(app: Flask):
    """Register all blueprints for the application."""
    from heritrace.routes.main import main_bp
    from heritrace.routes.entity import entity_bp
    from heritrace.routes.auth import auth_bp
    from heritrace.routes.api import api_bp
    from heritrace.errors.handlers import errors_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(entity_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(errors_bp, url_prefix='/errors')