from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    """사용자 정보 및 설정 모델"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False, default='사용자')
    search_scope = db.Column(db.String(20), nullable=False, default='general')
    theme = db.Column(db.String(10), nullable=False, default='light')
    preferred_model = db.Column(db.String(50), nullable=False, default='sonar-pro')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 관계 설정
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'search_scope': self.search_scope,
            'theme': self.theme,
            'preferred_model': self.preferred_model,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_active': self.last_active.isoformat()
        }

class Conversation(db.Model):
    """대화 세션 모델"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=True)  # 대화 제목 (첫 번째 메시지 기반)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # 관계 설정
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan', order_by='Message.created_at')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'message_count': len(self.messages)
        }

class Message(db.Model):
    """메시지 모델"""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    
    # 메시지 내용
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # 'user' 또는 'assistant'
    question_type = db.Column(db.String(20), nullable=True)  # 질문 유형 분류
    
    # AI 응답 관련 정보
    citations = db.Column(db.JSON, nullable=True)  # 참고 자료 링크들
    search_scope = db.Column(db.String(20), nullable=True)  # 검색 범위
    
    # 메타데이터
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processing_time = db.Column(db.Float, nullable=True)  # API 응답 시간 (초)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'content': self.content,
            'message_type': self.message_type,
            'question_type': self.question_type,
            'citations': self.citations,
            'search_scope': self.search_scope,
            'created_at': self.created_at.isoformat(),
            'processing_time': self.processing_time
        }

class UserSession(db.Model):
    """사용자 세션 관리"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(100), nullable=False, unique=True)
    current_conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # 관계 설정
    user = db.relationship('User', backref='sessions')
    current_conversation = db.relationship('Conversation', backref='active_sessions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'current_conversation_id': self.current_conversation_id,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_active': self.is_active
        }