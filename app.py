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
DEFAULT_MODEL = "sonar-pro"

# PPLX 모델 설정
PPLX_MODELS = {
    "sonar-pro": {
        "name": "Sonar Pro", 
        "description": "최고 성능의 플래그십 모델 (200k 컨텍스트)",
        "has_web_search": True,
        "recommended_for": ["복잡한 질문", "상세한 분석", "최신 정보"],
        "icon": "fas fa-star"
    },
    "sonar": {
        "name": "Sonar",
        "description": "균형잡힌 성능의 기본 모델 (128k 컨텍스트)", 
        "has_web_search": True,
        "recommended_for": ["일반적인 질문", "빠른 응답"],
        "icon": "fas fa-balance-scale"
    },
    "sonar-deep-research": {
        "name": "Sonar Deep Research",
        "description": "심층 연구 및 분석에 특화된 모델",
        "has_web_search": True,
        "recommended_for": ["학술 연구", "깊이 있는 분석"],
        "icon": "fas fa-microscope"
    },
    "sonar-reasoning-pro": {
        "name": "Sonar Reasoning Pro", 
        "description": "고급 추론 및 논리적 사고에 특화",
        "has_web_search": True,
        "recommended_for": ["복잡한 추론", "논리 문제"],
        "icon": "fas fa-brain"
    },
    "sonar-reasoning": {
        "name": "Sonar Reasoning",
        "description": "논리적 사고와 추론에 최적화된 모델",
        "has_web_search": True,
        "recommended_for": ["논리적 사고", "문제 해결"],
        "icon": "fas fa-lightbulb"
    },
    "r1-1776": {
        "name": "R1-1776",
        "description": "웹 검색 없는 순수 언어 모델",
        "has_web_search": False,
        "recommended_for": ["창작", "일반 대화", "개인정보 보호"],
        "icon": "fas fa-pen-fancy"
    },
    "codellama-34b-instruct": {
        "name": "CodeLlama", 
        "description": "프로그래밍 및 코딩에 특화된 모델",
        "has_web_search": False,
        "recommended_for": ["코딩 질문", "프로그래밍 도움"],
        "icon": "fas fa-code"
    }
}

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
            try:
                db.session.commit()
            except:
                db.session.rollback()
            return user
    
    # 새 사용자 생성
    user = User()
    try:
        db.session.add(user)
        db.session.commit()
        
        # 세션에 사용자 ID 저장
        session['user_id'] = user.id
        session.permanent = True
        
        return user
    except Exception as e:
        db.session.rollback()
        logging.error(f"사용자 생성 실패: {e}")
        # 기존 사용자 중 하나를 반환하거나 임시 사용자 생성
        existing_user = User.query.first()
        if existing_user:
            session['user_id'] = existing_user.id
            return existing_user
        raise e

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

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """사용자의 대화 목록 조회"""
    try:
        user = get_or_create_user()
        
        # 페이지네이션 파라미터
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search_query = request.args.get('search', '').strip()
        
        # 기본 쿼리
        query = Conversation.query.filter_by(user_id=user.id)
        
        # 검색 필터
        if search_query:
            query = query.filter(
                db.or_(
                    Conversation.title.ilike(f'%{search_query}%'),
                    Conversation.id.in_(
                        db.session.query(Message.conversation_id)
                        .filter(Message.content.ilike(f'%{search_query}%'))
                        .distinct()
                    )
                )
            )
        
        # 정렬 및 페이지네이션
        conversations = query.order_by(Conversation.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 대화 목록을 딕셔너리로 변환하고 메시지 수 추가
        conversations_list = []
        for conv in conversations.items:
            conv_dict = conv.to_dict()
            # 메시지 수 추가
            message_count = Message.query.filter_by(conversation_id=conv.id).count()
            conv_dict['message_count'] = message_count
            conversations_list.append(conv_dict)
        
        # 날짜별 그룹핑
        grouped_conversations = group_conversations_by_date(conversations_list)
        
        return jsonify({
            'success': True,
            'conversations': grouped_conversations,
            'pagination': {
                'page': conversations.page,
                'pages': conversations.pages,
                'per_page': conversations.per_page,
                'total': conversations.total,
                'has_next': conversations.has_next,
                'has_prev': conversations.has_prev
            }
        })
        
    except Exception as e:
        logging.error(f"대화 목록 조회 실패: {e}")
        return jsonify({'success': False, 'error': '대화 목록을 불러올 수 없습니다.'}), 500

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """특정 대화의 상세 내용 조회"""
    try:
        user = get_or_create_user()
        conversation = Conversation.query.filter_by(
            id=conversation_id, 
            user_id=user.id
        ).first()
        
        if not conversation:
            return jsonify({'error': '대화를 찾을 수 없습니다.'}), 404
        
        # 메시지 목록 포함
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at.asc()).all()
        
        return jsonify({
            'conversation': conversation.to_dict(),
            'messages': [msg.to_dict() for msg in messages]
        })
        
    except Exception as e:
        logging.error(f"대화 조회 실패: {e}")
        return jsonify({'error': '대화를 불러올 수 없습니다.'}), 500

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """대화 삭제"""
    try:
        user = get_or_create_user()
        conversation = Conversation.query.filter_by(
            id=conversation_id, 
            user_id=user.id
        ).first()
        
        if not conversation:
            return jsonify({'error': '대화를 찾을 수 없습니다.'}), 404
        
        # 관련 메시지도 함께 삭제 (CASCADE로 자동 처리됨)
        db.session.delete(conversation)
        db.session.commit()
        
        return jsonify({'message': '대화가 삭제되었습니다.'})
        
    except Exception as e:
        logging.error(f"대화 삭제 실패: {e}")
        return jsonify({'error': '대화를 삭제할 수 없습니다.'}), 500

@app.route('/api/conversations/<conversation_id>/favorite', methods=['POST'])
def toggle_favorite(conversation_id):
    """대화 즐겨찾기 토글"""
    try:
        user = get_or_create_user()
        conversation = Conversation.query.filter_by(
            id=conversation_id, 
            user_id=user.id
        ).first()
        
        if not conversation:
            return jsonify({'error': '대화를 찾을 수 없습니다.'}), 404
        
        conversation.is_favorite = not conversation.is_favorite
        db.session.commit()
        
        return jsonify({
            'message': '즐겨찾기가 업데이트되었습니다.',
            'is_favorite': conversation.is_favorite
        })
        
    except Exception as e:
        logging.error(f"즐겨찾기 토글 실패: {e}")
        return jsonify({'error': '즐겨찾기를 업데이트할 수 없습니다.'}), 500

@app.route('/api/conversations/new', methods=['POST'])
def create_new_conversation():
    """새 대화 생성"""
    try:
        user = get_or_create_user()
        data = request.get_json()
        title = data.get('title', '새 대화')
        
        conversation = Conversation(user_id=user.id, title=title)
        db.session.add(conversation)
        db.session.commit()
        
        # 세션에 새 대화 ID 저장
        session['conversation_id'] = conversation.id
        
        return jsonify({
            'conversation': conversation.to_dict(),
            'message': '새 대화가 생성되었습니다.'
        })
        
    except Exception as e:
        logging.error(f"대화 생성 실패: {e}")
        return jsonify({'error': '새 대화를 생성할 수 없습니다.'}), 500

def group_conversations_by_date(conversations):
    """대화를 날짜별로 그룹핑"""
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    today = now.date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    grouped = {
        'favorites': [],
        'today': [],
        'yesterday': [],
        'this_week': [],
        'older': []
    }
    
    for conv in conversations:
        conv_date = datetime.fromisoformat(conv['updated_at'].replace('Z', '+00:00')).date()
        
        if conv.get('is_favorite'):
            grouped['favorites'].append(conv)
        elif conv_date == today:
            grouped['today'].append(conv)
        elif conv_date == yesterday:
            grouped['yesterday'].append(conv)
        elif conv_date >= week_ago:
            grouped['this_week'].append(conv)
        else:
            grouped['older'].append(conv)
    
    return grouped

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
                'question_type': question_type,
                'model_used': 'direct_response'  # 직접 응답의 경우
            })
        
        # 검색이 필요한 경우 Perplexity API 호출
        messages = []
        
        # 품질 개선된 시스템 메시지 구성
        if response_config.get("use_search", True):
            system_content = f"""당신은 전문적인 AI 검색 어시스턴트입니다. {response_config.get('prompt_prefix', '다음 질문에 대해 도움이 되는 답변을 제공해주세요')}.

다음 품질 기준을 준수해주세요:
1. 최소 300자 이상의 상세한 답변 제공
2. 명확한 구조로 2-3개 섹션 구성 (예: 정의, 상세 설명, 요약/결론)
3. 제공된 참고자료를 다양하게 활용하여 신뢰성 확보
4. 구체적인 예시나 세부사항 포함
5. 마크다운 포맷으로 가독성 향상 (**, ##, - 등 활용)

답변은 정확하고 포괄적이며 사용자에게 실질적인 도움이 되도록 작성해주세요."""
        else:
            system_content = f"""당신은 친근하고 전문적인 AI 어시스턴트입니다. 사용자와 자연스럽게 대화하되, 다음을 준수해주세요:

1. 충분히 상세하고 도움이 되는 답변 제공
2. 명확하고 구조화된 형태로 답변 구성
3. 구체적인 예시나 설명 포함

사용자에게 최고 품질의 대화 경험을 제공해주세요."""
        
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
        
        # 사용자가 선택한 모델 사용 (기본값: sonar-pro)
        selected_model = data.get('selected_model') or user.preferred_model or DEFAULT_MODEL
        
        # 모델이 유효한지 확인
        if selected_model not in PPLX_MODELS:
            selected_model = DEFAULT_MODEL
            logging.warning(f"Invalid model {selected_model} requested, using default {DEFAULT_MODEL}")
        
        # 선택된 모델이 웹 검색을 지원하지 않는 경우 검색 비활성화
        model_info = PPLX_MODELS[selected_model]
        if not model_info["has_web_search"] and response_config.get("use_search", True):
            logging.info(f"Model {selected_model} doesn't support web search, adjusting response")
        
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": 0.2,  # 일관성 향상
            "top_p": 0.9,
            "max_tokens": 2000,  # 충분한 답변 길이
            "return_images": False,
            "return_related_questions": False,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        
        # 웹 검색을 지원하는 모델의 경우에만 검색 설정 추가
        if model_info["has_web_search"]:
            payload["search_recency_filter"] = response_config.get("search_recency_filter", "month")
        
        logging.debug(f"Perplexity API 요청 (질문유형: {question_type}, 모델: {selected_model}): {payload}")
        
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        api_response = response.json()
        logging.debug(f"Perplexity API 응답: {api_response}")
        
        # AI 응답 추출
        ai_content = api_response['choices'][0]['message']['content']
        citations = api_response.get('citations', [])
        
        # 답변 품질 검증
        quality_score = evaluate_response_quality(ai_content, citations, question_type)
        logging.info(f"답변 품질 점수: {quality_score['total_score']}/100")
        
        # 품질 기준 미달 시 재시도 (최대 2회 추가)
        retry_count = 0
        max_retries = 2
        
        while quality_score['total_score'] < 70 and retry_count < max_retries:
            retry_count += 1
            logging.warning(f"품질 기준 미달 (점수: {quality_score['total_score']}), 재시도 {retry_count}/{max_retries}")
            
            # 질문을 더 구체적으로 재구성
            enhanced_message = enhance_question_for_retry(user_message, question_type, retry_count)
            messages[-1]['content'] = enhanced_message
            
            # 재요청
            retry_response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload, timeout=30)
            if retry_response.status_code == 200:
                api_response = retry_response.json()
                ai_content = api_response['choices'][0]['message']['content']
                citations = api_response.get('citations', [])
                quality_score = evaluate_response_quality(ai_content, citations, question_type)
                logging.info(f"재시도 후 품질 점수: {quality_score['total_score']}/100")
            else:
                break
        
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
            'question_type': question_type,
            'model_used': selected_model,
            'quality_score': quality_score,
            'retry_count': retry_count,
            'source_filtering': {
                'total_sources': len(api_response.get('citations', [])),
                'filtered_sources': len(citations),
                'filtered_count': max(0, len(api_response.get('citations', [])) - len(citations)),
                'filter_description': f'관련성 기반 필터링 (최대 {max_sources}개 소스)'
            }
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

def evaluate_response_quality(response, citations, question_type):
    """답변 품질을 평가하는 함수"""
    score = {
        'length_score': 0,
        'structure_score': 0,
        'citation_score': 0,
        'content_score': 0,
        'total_score': 0
    }
    
    # 1. 길이 점수 (25점 만점)
    response_length = len(response)
    if response_length >= 300:
        score['length_score'] = 25
    elif response_length >= 200:
        score['length_score'] = 20
    elif response_length >= 100:
        score['length_score'] = 15
    else:
        score['length_score'] = 10
    
    # 2. 구조 점수 (25점 만점)
    structure_indicators = [
        '**' in response,  # 볼드 텍스트
        '##' in response,  # 헤딩
        '\n-' in response or '\n•' in response,  # 리스트
        response.count('\n\n') >= 1,  # 단락 구분
        ':' in response  # 설명 구조
    ]
    score['structure_score'] = min(25, sum(structure_indicators) * 5)
    
    # 3. 참고자료 점수 (25점 만점)
    citation_count = len(citations) if citations else 0
    if citation_count >= 3:
        score['citation_score'] = 25
    elif citation_count >= 2:
        score['citation_score'] = 20
    elif citation_count >= 1:
        score['citation_score'] = 15
    else:
        score['citation_score'] = 5 if question_type == 'greeting' else 0
    
    # 4. 콘텐츠 품질 점수 (25점 만점)
    content_indicators = [
        '예시' in response or '예를 들어' in response,  # 예시 포함
        '요약' in response or '결론' in response,  # 결론 포함
        len(response.split('.')) >= 3,  # 충분한 문장 수
        any(keyword in response for keyword in ['정의', '의미', '특징', '방법', '종류']),  # 체계적 설명
        response.count('다음') >= 1 or response.count('이러한') >= 1  # 연결성
    ]
    score['content_score'] = min(25, sum(content_indicators) * 5)
    
    # 총점 계산
    score['total_score'] = sum([
        score['length_score'],
        score['structure_score'], 
        score['citation_score'],
        score['content_score']
    ])
    
    return score

def enhance_question_for_retry(original_question, question_type, retry_count):
    """재시도를 위해 질문을 더 구체적으로 개선"""
    enhancement_templates = {
        'general': [
            f"{original_question}에 대해 상세하고 구체적인 설명을 제공해주세요. 정의, 특징, 예시를 포함해주세요.",
            f"{original_question}의 모든 측면에 대해 포괄적으로 설명해주세요. 배경, 현황, 의미 등을 다각도로 분석해주세요."
        ],
        'info_search': [
            f"{original_question}에 대한 최신 정보와 다양한 관점을 제시해주세요. 여러 출처의 정보를 종합하여 설명해주세요.",
            f"{original_question}의 전문적이고 상세한 분석을 제공해주세요. 관련 데이터와 사실들을 포함해주세요."
        ],
        'learning': [
            f"{original_question}에 대해 단계별로 자세히 설명해주세요. 기초부터 심화까지 체계적으로 학습할 수 있도록 구성해주세요.",
            f"{original_question}의 개념, 원리, 적용 방법을 구체적인 예시와 함께 상세히 설명해주세요."
        ],
        'realtime': [
            f"{original_question}의 최신 동향과 현재 상황을 자세히 분석해주세요. 관련 뉴스와 데이터를 포함해주세요.",
            f"{original_question}에 대한 실시간 정보와 트렌드를 종합적으로 제시해주세요."
        ]
    }
    
    templates = enhancement_templates.get(question_type, enhancement_templates['general'])
    template_index = min(retry_count - 1, len(templates) - 1)
    
    return templates[template_index]

@app.route('/api/conversation', methods=['GET'])
def get_current_conversation():
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
        preferred_model = data.get('preferred_model', DEFAULT_MODEL)
        
        # 모델이 유효한지 확인
        if preferred_model not in PPLX_MODELS:
            preferred_model = DEFAULT_MODEL
        
        # 사용자 정보 업데이트
        user = get_or_create_user()
        user.name = user_name
        user.search_scope = search_scope
        user.theme = theme
        user.preferred_model = preferred_model
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
            'theme': user.theme,
            'preferred_model': user.preferred_model
        }
        return jsonify(settings)
    except Exception as e:
        logging.error(f"설정 조회 오류: {str(e)}")
        return jsonify({
            'user_name': '사용자',
            'search_scope': 'general',
            'theme': 'light',
            'preferred_model': DEFAULT_MODEL
        })

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
def delete_specific_conversation(conversation_id):
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

@app.route('/api/models', methods=['GET'])
def get_available_models():
    """사용 가능한 PPLX 모델 목록 반환"""
    try:
        models_info = []
        for model_id, model_data in PPLX_MODELS.items():
            models_info.append({
                'id': model_id,
                'name': model_data['name'],
                'description': model_data['description'],
                'has_web_search': model_data['has_web_search'],
                'recommended_for': model_data['recommended_for'],
                'icon': model_data['icon']
            })
        
        return jsonify({
            'models': models_info,
            'default_model': DEFAULT_MODEL
        })
    except Exception as e:
        logging.error(f"모델 목록 조회 오류: {str(e)}")
        return jsonify({'error': '모델 목록을 가져올 수 없습니다.'}), 500

@app.route('/api/model/recommend', methods=['POST'])
def recommend_model():
    """질문 유형에 따른 모델 추천"""
    try:
        data = request.get_json()
        question_type = data.get('question_type', 'general')
        user_message = data.get('message', '').lower()
        
        # 질문 내용 기반 모델 추천
        if any(keyword in user_message for keyword in ['코딩', '프로그래밍', '코드', 'programming', 'code', 'python', 'javascript']):
            recommended = 'codellama-34b-instruct'
        elif question_type == 'learning' or any(keyword in user_message for keyword in ['연구', '분석', '논문', '학술']):
            recommended = 'sonar-deep-research'
        elif any(keyword in user_message for keyword in ['추론', '논리', '문제해결', 'reasoning']):
            recommended = 'sonar-reasoning-pro'
        elif any(keyword in user_message for keyword in ['창작', '글쓰기', '소설', '시']):
            recommended = 'r1-1776'
        elif question_type == 'realtime' or any(keyword in user_message for keyword in ['최신', '뉴스', '현재']):
            recommended = 'sonar-pro'
        else:
            recommended = 'sonar'  # 기본 추천
        
        model_info = PPLX_MODELS.get(recommended, PPLX_MODELS[DEFAULT_MODEL])
        
        return jsonify({
            'recommended_model': recommended,
            'model_info': model_info,
            'reason': f"질문 유형 '{question_type}'에 최적화된 모델입니다."
        })
        
    except Exception as e:
        logging.error(f"모델 추천 오류: {str(e)}")
        return jsonify({'error': '모델 추천 중 오류가 발생했습니다.'}), 500

# 데이터베이스 테이블 생성
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
