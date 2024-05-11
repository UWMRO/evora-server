from flask import Blueprint
from .endpoints import blueprint

def register_framing_blueprints(app):
    app.register_blueprint(blueprint)