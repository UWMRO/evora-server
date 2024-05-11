from flask import Blueprint
from .endpoints import blueprint

def register_blueprint(app):
    app.register_blueprint(blueprint)