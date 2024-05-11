from flask import Blueprint
from .endpoints import framing_bp

def register_framing_blueprints(app):
    app.register_blueprint(framing_bp)