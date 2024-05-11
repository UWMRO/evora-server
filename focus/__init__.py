from flask import Blueprint
from .endpoints import blueprint

def register_focus_assist_blueprints(app):
    app.register_blueprint(blueprint)