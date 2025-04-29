from flask import Flask
from app.config import load_configurations, configure_logging
from app.routes.webhook_routes import webhook_blueprint
from app.routes.auth_routes import auth_blueprint
from app.routes.profile_routes import profile_blueprint
from app.routes.app_routes import app_blueprint
from app.routes.assistant_routes import assistant_blueprint
from app.routes.admin_subscription_routes import admin_subscription_bp
from app.routes.user_subscription_routes import user_subscription_bp
from app.routes.message_routes import message_blueprint
from app.routes.message_template_routes import template_routes
from app.routes.scheduler_routes import scheduler_routes
from app.routes.batch_routes import batch_routes
from app.routes.contact_routes import contact_routes
from app.routes.dashboard_routes import admin_dashboard
from app.routes.admin_user_routes import admin_user_blueprint
from app.routes.super_admin_routes import super_admin_blueprint
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))


def create_app():
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(profile_blueprint)
    app.register_blueprint(app_blueprint)
    app.register_blueprint(assistant_blueprint)
    
    #subscriptions blueprints
    app.register_blueprint(user_subscription_bp)
    app.register_blueprint(admin_subscription_bp)
    
    #message blueprints
    app.register_blueprint(message_blueprint)
    app.register_blueprint(template_routes)
    app.register_blueprint(scheduler_routes)
    app.register_blueprint(batch_routes)
    app.register_blueprint(contact_routes)
    
    #admin dashboard
    app.register_blueprint(admin_dashboard)
    app.register_blueprint(admin_user_blueprint)
    app.register_blueprint(super_admin_blueprint)
    return app
