import os
import requests
import logging
import time
import hashlib
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from models import db, User, Conversation, Message, UserSession

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

# Flask 앱 초기화
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 데이터베이스 초기화
db.init_app(app)

# Perplexity API 설정
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "your_api_key_here")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "llama-3.1-sonar-small-128k-online"

def classify_question(user_input):
    """
    사용자 입력을 분류하여 적절한 응답 방식을 결정
    
    Args:
        user_input (str): 사용자 입력 텍스트
    
    Returns:
        str: 질문 유형 ('greeting', 'info_search', 'learning', 'realtime', 'general')
    """
    user_input_lower = user_input.lower().strip()
    
    # 인사말 키워드
    greeting_keywords = ["안녕", "hi", "hello", "고마워", "감사", "bye", "안녕히", "헬로", "하이", "잘가", "수고"]
    
    # 실시간 정보 키워드
    realtime_keywords = ["오늘", "현재", "실시간", "지금", "최신", "날씨", "주가", "뉴스", "속보", "시간", "요즘"]
    
    # 학습/설명 키워드
    learning_keywords = ["설명", "가르쳐", "어떻게", "무엇", "왜", "방법", "예시", "원리", "의미", "뜻", "차이"]
    
    # 정보 검색 키워드
    info_keywords = ["정보", "알려줘", "찾아줘", "검색", "어디", "언제", "누구", "어떤", "무슨", "얼마"]
    
    # 인사말 패턴 (짧고 간단한 인사)
    if len(user_input_lower) <= 10 and any(keyword in user_input_lower for keyword in greeting_keywords):
        return "greeting"
    
    # 실시간 정보 요청
    if any(keyword in user_input_lower for keyword in realtime_keywords):
        return "realtime"
    
    # 학습/설명 요청
    if any(keyword in user_input_lower for keyword in learning_keywords):
        return "learning"
    
    # 정보 검색 요청
    if any(keyword in user_input_lower for keyword in info_keywords):
        return "info_search"
    
    # 기본값: 일반 질문
    return "general"

def get_response_config(question_type, search_scope):
    """
    질문 유형에 따른 응답 설정을 반환
    
    Args:
        question_type (str): 질문 유형
        search_scope (str): 사용자 설정 검색 범위
    
    Returns:
        dict: 응답 설정 딕셔너리
    """
    configs = {
        "greeting": {
            "use_search": False,
            "response": "안녕하세요! 무엇을 도와드릴까요? 궁금한 것이 있으시면 언제든 말씀해 주세요.",
            "max_length": 100
        },
        "info_search": {
            "use_search": True,
            "prompt_prefix": "다음 질문에 대해 정확하고 상세한 정보를 제공해주세요",
            "search_recency_filter": "month",
            "max_sources": 5
        },
        "learning": {
            "use_search": True,
            "prompt_prefix": "다음 주제에 대해 단계별로 쉽게 설명해주세요. 초보자도 이해할 수 있도록 차근차근 설명해주세요",
            "search_recency_filter": "year",
            "max_sources": 3
        },
        "realtime": {
            "use_search": True,
            "prompt_prefix": "최신 정보를 기반으로 정확하고 신뢰할 수 있는 답변을 제공해주세요",
            "search_recency_filter": "day",
            "max_sources": 4
        },
        "general": {
            "use_search": True,
            "prompt_prefix": "다음 질문에 대해 도움이 되는 답변을 제공해주세요",
            "search_recency_filter": "month",
            "max_sources": 4
        }
    }
    
    # 사용자 검색 범위 설정에 따라 조정
    config = configs.get(question_type, configs["general"])
    
    if search_scope == 'news' and config.get("use_search"):
        config["search_recency_filter"] = "day"
    elif search_scope == 'academic' and config.get("use_search"):
        config["search_recency_filter"] = "year"
        config["prompt_prefix"] += ". 학술적이고 전문적인 정보를 우선으로 해주세요"
    
    return config

def get_or_create_user():
    """세션에서 사용자 ID를 가져오거나 새 사용자 생성"""
    user_id = session.get('user_id')
    
    if user_id:
        user = User.query.get(user_id)
        if user:
            # 마지막 활동 시간 업데이트
            user.last_active = datetime.utcnow()
            db.session.commit()
            return user
    
    # 새 사용자 생성
    user = User()
    db.session.add(user)
    db.session.commit()
    
    # 세션에 사용자 ID 저장
    session['user_id'] = user.id
    session.permanent = True
    
    return user

def get_or_create_conversation(user_id):
    """현재 활성 대화를 가져오거나 새 대화 생성"""
    conversation_id = session.get('conversation_id')
    
    if conversation_id:
        conversation = Conversation.query.filter_by(
            id=conversation_id, 
            user_id=user_id, 
            is_active=True
        ).first()
        if conversation:
            return conversation
    
    # 새 대화 생성
    conversation = Conversation(user_id=user_id)
    db.session.add(conversation)
    db.session.commit()
    
    # 세션에 대화 ID 저장
    session['conversation_id'] = conversation.id
    
    return conversation

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    # 사용자 생성 또는 가져오기
    user = get_or_create_user()
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """채팅 API 엔드포인트 - 질문 유형별 맞춤 응답 제공"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        search_scope = data.get('search_scope', 'general')
        user_name = data.get('user_name', '사용자')
        
        if not user_message:
            return jsonify({'error': '메시지를 입력해주세요.'}), 400
        
        # 질문 유형 자동 분류
        question_type = classify_question(user_message)
        logging.debug(f"질문 유형 분류: '{user_message}' -> {question_type}")
        
        # 질문 유형에 따른 응답 설정 가져오기
        response_config = get_response_config(question_type, search_scope)
        
        # 사용자 및 대화 가져오기/생성
        user = get_or_create_user()
        conversation = get_or_create_conversation(user.id)
        
        # 처리 시작 시간 기록
        start_time = time.time()
        
        # 사용자 메시지를 데이터베이스에 저장
        user_message_obj = Message(
            conversation_id=conversation.id,
            user_id=user.id,
            content=user_message,
            message_type='user',
            question_type=question_type,
            search_scope=search_scope
        )
        db.session.add(user_message_obj)
        db.session.commit()
        
        # 인사말의 경우 검색 없이 직접 응답
        if not response_config.get("use_search", True):
            ai_content = response_config["response"]
            citations = []
            processing_time = time.time() - start_time
            
            # AI 응답을 데이터베이스에 저장
            ai_message_obj = Message(
                conversation_id=conversation.id,
                user_id=user.id,
                content=ai_content,
                message_type='assistant',
                question_type=question_type,
                citations=citations,
                search_scope=search_scope,
                processing_time=processing_time
            )
            db.session.add(ai_message_obj)
            
            # 대화 업데이트 시간 갱신
            conversation.updated_at = datetime.utcnow()
            if not conversation.title:
                conversation.title = user_message[:50] + ('...' if len(user_message) > 50 else '')
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'response': ai_content,
                'citations': citations,
                'timestamp': user_message_obj.created_at.isoformat(),
                'question_type': question_type
            })
        
        # 검색이 필요한 경우 Perplexity API 호출
        messages = []
        
        # 질문 유형에 맞는 시스템 메시지 구성
        system_content = f"당신은 {user_name}님을 위한 AI 검색 어시스턴트입니다. {response_config['prompt_prefix']}."
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # 이전 대화 기록 추가 (최근 10개 메시지, 인사말 제외)
        recent_messages = Message.query.filter_by(
            conversation_id=conversation.id
        ).filter(
            Message.question_type != 'greeting'
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        # 시간순 정렬로 되돌리기
        recent_messages.reverse()
        
        for msg in recent_messages:
            if msg.id != user_message_obj.id:  # 현재 메시지는 제외
                messages.append({
                    "role": "user" if msg.message_type == 'user' else "assistant",
                    "content": msg.content
                })
        
        # 현재 사용자 메시지 추가
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Perplexity API 요청
        headers = {
            'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": PERPLEXITY_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "top_p": 0.9,
            "return_images": False,
            "return_related_questions": False,  # 관련 질문 비활성화로 응답 간소화
            "search_recency_filter": response_config.get("search_recency_filter", "month"),
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        
        logging.debug(f"Perplexity API 요청 (질문유형: {question_type}): {payload}")
        
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        api_response = response.json()
        logging.debug(f"Perplexity API 응답: {api_response}")
        
        # AI 응답 추출
        ai_content = api_response['choices'][0]['message']['content']
        citations = api_response.get('citations', [])
        
        # 출처 필터링 (관련성 높은 출처만 선별)
        max_sources = response_config.get("max_sources", 4)
        if len(citations) > max_sources:
            citations = citations[:max_sources]
        
        # 처리 시간 계산
        processing_time = time.time() - start_time
        
        # AI 응답을 데이터베이스에 저장
        ai_message_obj = Message(
            conversation_id=conversation.id,
            user_id=user.id,
            content=ai_content,
            message_type='assistant',
            question_type=question_type,
            citations=citations,
            search_scope=search_scope,
            processing_time=processing_time
        )
        db.session.add(ai_message_obj)
        
        # 대화 업데이트 시간 갱신 및 제목 설정
        conversation.updated_at = datetime.utcnow()
        if not conversation.title:
            conversation.title = user_message[:50] + ('...' if len(user_message) > 50 else '')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'response': ai_content,
            'citations': citations,
            'timestamp': user_message_obj.created_at.isoformat(),
            'question_type': question_type
        })
        
    except requests.exceptions.RequestException as e:
        logging.error(f"API 요청 오류: {str(e)}")
        return jsonify({'error': 'API 요청 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'}), 500
    except KeyError as e:
        logging.error(f"API 응답 파싱 오류: {str(e)}")
        return jsonify({'error': 'API 응답을 처리하는 중 오류가 발생했습니다.'}), 500
    except Exception as e:
        logging.error(f"예상치 못한 오류: {str(e)}")
        return jsonify({'error': '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'}), 500

@app.route('/api/conversation', methods=['GET'])
def get_conversation():
    """현재 대화의 메시지 기록 반환"""
    try:
        user = get_or_create_user()
        conversation_id = session.get('conversation_id')
        
        if not conversation_id:
            return jsonify({'conversation': []})
        
        # 현재 대화의 메시지들 가져오기
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at).all()
        
        # 세션 형태로 변환
        conversation_data = []
        for msg in messages:
            message_data = {
                'type': msg.message_type,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
                'question_type': msg.question_type
            }
            
            if msg.message_type == 'assistant' and msg.citations:
                message_data['citations'] = msg.citations
                
            if msg.message_type == 'user':
                # 사용자 이름은 현재 사용자 설정에서 가져오기
                message_data['user_name'] = user.name
                
            conversation_data.append(message_data)
        
        return jsonify({'conversation': conversation_data})
        
    except Exception as e:
        logging.error(f"대화 기록 조회 오류: {str(e)}")
        return jsonify({'conversation': []})

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """현재 대화 종료 및 새 대화 시작"""
    try:
        user = get_or_create_user()
        conversation_id = session.get('conversation_id')
        
        if conversation_id:
            # 현재 대화를 비활성화
            conversation = Conversation.query.get(conversation_id)
            if conversation:
                conversation.is_active = False
                db.session.commit()
        
        # 세션에서 대화 ID 제거 (새 대화가 자동 생성됨)
        session.pop('conversation_id', None)
        
        return jsonify({'success': True, 'message': '대화 기록이 초기화되었습니다.'})
        
    except Exception as e:
        logging.error(f"대화 기록 초기화 오류: {str(e)}")
        return jsonify({'error': '대화 기록 초기화 중 오류가 발생했습니다.'}), 500

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """사용자 설정 저장"""
    try:
        data = request.get_json()
        user_name = data.get('user_name', '사용자')
        search_scope = data.get('search_scope', 'general')
        theme = data.get('theme', 'light')
        
        # 사용자 정보 업데이트
        user = get_or_create_user()
        user.name = user_name
        user.search_scope = search_scope
        user.theme = theme
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': '설정이 저장되었습니다.'})
    except Exception as e:
        logging.error(f"설정 저장 오류: {str(e)}")
        return jsonify({'error': '설정 저장 중 오류가 발생했습니다.'}), 500

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """사용자 설정 조회"""
    try:
        user = get_or_create_user()
        settings = {
            'user_name': user.name,
            'search_scope': user.search_scope,
            'theme': user.theme
        }
        return jsonify(settings)
    except Exception as e:
        logging.error(f"설정 조회 오류: {str(e)}")
        return jsonify({
            'user_name': '사용자',
            'search_scope': 'general',
            'theme': 'light'
        })

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """사용자의 모든 대화 목록 반환"""
    try:
        user = get_or_create_user()
        
        # 사용자의 모든 대화 가져오기 (최신순)
        conversations = Conversation.query.filter_by(
            user_id=user.id
        ).order_by(Conversation.updated_at.desc()).limit(50).all()
        
        conversation_list = []
        for conv in conversations:
            # 각 대화의 첫 번째 메시지와 마지막 메시지 시간 가져오기
            first_message = Message.query.filter_by(
                conversation_id=conv.id
            ).order_by(Message.created_at).first()
            
            conversation_data = {
                'id': conv.id,
                'title': conv.title or (first_message.content[:30] + '...' if first_message and len(first_message.content) > 30 else first_message.content if first_message else '새 대화'),
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'is_active': conv.is_active,
                'message_count': len(conv.messages)
            }
            conversation_list.append(conversation_data)
        
        return jsonify({'conversations': conversation_list})
        
    except Exception as e:
        logging.error(f"대화 목록 조회 오류: {str(e)}")
        return jsonify({'conversations': []})

@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_specific_conversation(conversation_id):
    """특정 대화의 메시지 기록 반환"""
    try:
        user = get_or_create_user()
        
        # 대화 소유권 확인
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=user.id
        ).first()
        
        if not conversation:
            return jsonify({'error': '대화를 찾을 수 없습니다.'}), 404
        
        # 대화의 메시지들 가져오기
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at).all()
        
        # 세션에 현재 대화 ID 설정
        session['conversation_id'] = conversation_id
        
        # 메시지 데이터 변환
        conversation_data = []
        for msg in messages:
            message_data = {
                'type': msg.message_type,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
                'question_type': msg.question_type
            }
            
            if msg.message_type == 'assistant' and msg.citations:
                message_data['citations'] = msg.citations
                
            if msg.message_type == 'user':
                message_data['user_name'] = user.name
                
            conversation_data.append(message_data)
        
        return jsonify({
            'conversation': conversation_data,
            'conversation_info': {
                'id': conversation.id,
                'title': conversation.title,
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        logging.error(f"특정 대화 조회 오류: {str(e)}")
        return jsonify({'error': '대화 조회 중 오류가 발생했습니다.'}), 500

@app.route('/api/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """특정 대화 삭제"""
    try:
        user = get_or_create_user()
        
        # 대화 소유권 확인
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_id=user.id
        ).first()
        
        if not conversation:
            return jsonify({'error': '대화를 찾을 수 없습니다.'}), 404
        
        # 대화와 관련 메시지 모두 삭제 (CASCADE로 자동 삭제됨)
        db.session.delete(conversation)
        db.session.commit()
        
        # 현재 세션의 대화 ID와 같다면 제거
        if session.get('conversation_id') == conversation_id:
            session.pop('conversation_id', None)
        
        return jsonify({'success': True, 'message': '대화가 삭제되었습니다.'})
        
    except Exception as e:
        logging.error(f"대화 삭제 오류: {str(e)}")
        return jsonify({'error': '대화 삭제 중 오류가 발생했습니다.'}), 500

# 데이터베이스 테이블 생성
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
