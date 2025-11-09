from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models import db
from routes.auth import auth_bp
from routes.frameworks import frameworks_bp
from routes.plans import plans_bp
from routes.prompts import prompts_bp
from routes.responses import responses_bp
from routes.feedback import feedback_bp
from routes.reasoning import reasoning_bp
from routes.agent import agent_bp
from routes.documents import documents_bp
from services.seed_data import seed_frameworks_and_prompts

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    CORS(
        app,
        origins=app.config['CORS_ORIGINS'],
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization'],
        methods=['GET','POST','PUT','DELETE','OPTIONS']
    )
    jwt = JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(frameworks_bp, url_prefix='/api/frameworks')
    app.register_blueprint(plans_bp, url_prefix='/api/plans')
    app.register_blueprint(prompts_bp, url_prefix='/api/prompts')
    app.register_blueprint(responses_bp, url_prefix='/api/responses')
    app.register_blueprint(feedback_bp, url_prefix='/api/feedback')
    app.register_blueprint(reasoning_bp, url_prefix='/api/reasoning')
    app.register_blueprint(agent_bp, url_prefix='/api/agent')
    app.register_blueprint(documents_bp, url_prefix='/api/documents')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Seed initial frameworks and prompts
        seed_frameworks_and_prompts()
    
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'service': 'CyPlanAI API'}, 200
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8088)

