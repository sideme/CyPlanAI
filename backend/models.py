from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()

class User(db.Model):
    """User model representing individuals using CyPlanAI"""
    __tablename__ = 'users'
    
    userId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student, instructor, admin
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    plans = db.relationship('Plan', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'userId': self.userId,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Framework(db.Model):
    """Framework model representing cybersecurity frameworks"""
    __tablename__ = 'frameworks'
    
    frameworkId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, unique=True)
    type = db.Column(db.String(50), nullable=False)  # NIST_CSF, ISO_27001, NIST_AI_RMF, MITRE_ATLAS
    description = db.Column(db.Text)
    version = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    prompts = db.relationship('Prompt', backref='framework', lazy=True)
    
    def to_dict(self):
        return {
            'frameworkId': self.frameworkId,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'version': self.version
        }

class Prompt(db.Model):
    """Prompt model representing questions presented to users"""
    __tablename__ = 'prompts'
    
    promptId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # e.g., 'Risk Assessment', 'Control Selection'
    frameworkId = db.Column(db.String(36), db.ForeignKey('frameworks.frameworkId'), nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    responses = db.relationship('Response', backref='prompt', lazy=True)
    
    def to_dict(self):
        return {
            'promptId': self.promptId,
            'text': self.text,
            'category': self.category,
            'frameworkId': self.frameworkId,
            'order': self.order,
            'framework': self.framework.to_dict() if self.framework else None
        }

class Plan(db.Model):
    """Plan model aggregating user responses into cybersecurity planning output"""
    __tablename__ = 'plans'
    
    planId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    summary = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='in_progress')  # in_progress, completed, draft
    userId = db.Column(db.String(36), db.ForeignKey('users.userId'), nullable=False)
    frameworkId = db.Column(db.String(36), db.ForeignKey('frameworks.frameworkId'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    framework = db.relationship('Framework')
    responses = db.relationship('Response', backref='plan', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'planId': self.planId,
            'summary': self.summary,
            'status': self.status,
            'userId': self.userId,
            'frameworkId': self.frameworkId,
            'framework': self.framework.to_dict() if self.framework else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'response_count': len(self.responses)
        }

class Response(db.Model):
    """Response model capturing individual answers submitted by users"""
    __tablename__ = 'responses'
    
    responseId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    value = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    planId = db.Column(db.String(36), db.ForeignKey('plans.planId'), nullable=False)
    promptId = db.Column(db.String(36), db.ForeignKey('prompts.promptId'), nullable=False)
    
    def to_dict(self):
        return {
            'responseId': self.responseId,
            'value': self.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'planId': self.planId,
            'promptId': self.promptId,
            'prompt': self.prompt.to_dict() if self.prompt else None
        }

class Feedback(db.Model):
    """Feedback model for user feedback submissions"""
    __tablename__ = 'feedback'
    
    feedbackId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId = db.Column(db.String(36), db.ForeignKey('users.userId'), nullable=False)
    planId = db.Column(db.String(36), db.ForeignKey('plans.planId'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    user = db.relationship('User', backref='feedback_submissions')
    plan = db.relationship('Plan', backref='feedback')
    
    def to_dict(self):
        return {
            'feedbackId': self.feedbackId,
            'userId': self.userId,
            'planId': self.planId,
            'message': self.message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

# --- Knowledge Base and Auditability ---

class Control(db.Model):
    """Catalog of controls across frameworks (normalized with citations)."""
    __tablename__ = 'controls'

    controlId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    frameworkId = db.Column(db.String(36), db.ForeignKey('frameworks.frameworkId'), nullable=False)
    reference = db.Column(db.String(100), nullable=False)  # e.g., ISO A.8.1.1, NIST CSF PR.AC-3
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # Access Control, Asset Management, etc.
    maturity_cost = db.Column(db.Integer, default=2)  # rough heuristic 1..5
    severity_mitigated = db.Column(db.Integer, default=3)  # rough heuristic 1..5

    framework = db.relationship('Framework')

    def to_dict(self):
        return {
            'controlId': self.controlId,
            'frameworkId': self.frameworkId,
            'reference': self.reference,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'maturity_cost': self.maturity_cost,
            'severity_mitigated': self.severity_mitigated,
        }

class Threat(db.Model):
    """Threat library entries, including adversarial ML items."""
    __tablename__ = 'threats'

    threatId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., 'Adversarial ML', 'Data Poisoning'
    likelihood = db.Column(db.Integer, default=2)  # 1..5
    impact = db.Column(db.Integer, default=3)  # 1..5

    def to_dict(self):
        return {
            'threatId': self.threatId,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'likelihood': self.likelihood,
            'impact': self.impact,
        }

class ControlMapping(db.Model):
    """Ontology: map risks/threats to controls and evidence."""
    __tablename__ = 'control_mappings'

    mappingId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    threatId = db.Column(db.String(36), db.ForeignKey('threats.threatId'), nullable=False)
    controlId = db.Column(db.String(36), db.ForeignKey('controls.controlId'), nullable=False)
    evidence_hint = db.Column(db.Text)  # suggested evidence to collect

    threat = db.relationship('Threat')
    control = db.relationship('Control')

    def to_dict(self):
        return {
            'mappingId': self.mappingId,
            'threat': self.threat.to_dict() if self.threat else None,
            'control': self.control.to_dict() if self.control else None,
            'evidence_hint': self.evidence_hint,
        }

class AuditLog(db.Model):
    """Capture auditable actions and AI prompts/outputs for traceability."""
    __tablename__ = 'audit_logs'

    auditId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId = db.Column(db.String(36), db.ForeignKey('users.userId'))
    planId = db.Column(db.String(36), db.ForeignKey('plans.planId'))
    action = db.Column(db.String(100), nullable=False)  # e.g., CREATE_PLAN, GENERATE_SUMMARY
    details = db.Column(db.Text)  # JSON/text payload
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'auditId': self.auditId,
            'userId': self.userId,
            'planId': self.planId,
            'action': self.action,
            'details': self.details,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }

class AgentSession(db.Model):
    """Agent conversation session for stateful planning."""
    __tablename__ = 'agent_sessions'

    sessionId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    userId = db.Column(db.String(36), db.ForeignKey('users.userId'), nullable=False)
    planId = db.Column(db.String(36), db.ForeignKey('plans.planId'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'sessionId': self.sessionId,
            'userId': self.userId,
            'planId': self.planId,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

class AgentMessage(db.Model):
    """Messages within an agent session (user/assistant/tools)."""
    __tablename__ = 'agent_messages'

    messageId = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sessionId = db.Column(db.String(36), db.ForeignKey('agent_sessions.sessionId'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user, assistant, tool
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'messageId': self.messageId,
            'sessionId': self.sessionId,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class ChatThread(db.Model):
    """Persistent thread metadata for LangGraph conversations."""
    __tablename__ = 'chat_threads'

    id = db.Column(db.Integer, primary_key=True)
    threadId = db.Column(db.String(64), unique=True, nullable=False, index=True)
    userId = db.Column(db.String(36), db.ForeignKey('users.userId'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('chat_threads', lazy=True))
    messages = db.relationship('ChatMessage', backref='thread', lazy=True, cascade='all, delete-orphan', order_by='ChatMessage.created_at')

    def to_dict(self, include_messages: bool = False):
        data = {
            'threadId': self.threadId,
            'userId': self.userId,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            data['messages'] = [message.to_dict() for message in self.messages]
        return data


class ChatMessage(db.Model):
    """Individual messages within a chat thread."""
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    threadId = db.Column(db.String(64), db.ForeignKey('chat_threads.threadId'), nullable=False, index=True)
    messageId = db.Column(db.String(64), nullable=True)
    role = db.Column(db.String(20), nullable=False)  # human, ai, tool
    content = db.Column(db.Text, nullable=False)
    tokenUsage = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'threadId': self.threadId,
            'messageId': self.messageId,
            'role': self.role,
            'content': self.content,
            'tokenUsage': self.tokenUsage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

