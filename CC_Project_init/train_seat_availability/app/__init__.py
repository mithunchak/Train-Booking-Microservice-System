from flask import Flask
from .routes import app

def create_app():
    return app
