import os
import requests
import logging
from flask import Flask, render_template, request, jsonify, session
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

# Flask 앱 초기화
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

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

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    # 세션에 대화 기록이 없으면 초기화
    if 'conversation_history' not in session:
        session['conversation_history'] = []
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
        
        # 세션에서 대화 기록 가져오기
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        conversation_history = session['conversation_history']
        timestamp = datetime.now().isoformat()
        
        # 사용자 메시지를 대화 기록에 추가
        conversation_history.append({
            'type': 'user',
            'content': user_message,
            'timestamp': timestamp,
            'user_name': user_name,
            'question_type': question_type  # 질문 유형도 저장
        })
        
        # 인사말의 경우 검색 없이 직접 응답
        if not response_config.get("use_search", True):
            ai_content = response_config["response"]
            citations = []
            
            # AI 응답을 대화 기록에 추가
            conversation_history.append({
                'type': 'assistant',
                'content': ai_content,
                'citations': citations,
                'timestamp': timestamp,
                'question_type': question_type
            })
            
            # 세션 업데이트 (최근 20개 메시지만 유지)
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            session['conversation_history'] = conversation_history
            session.modified = True
            
            return jsonify({
                'success': True,
                'response': ai_content,
                'citations': citations,
                'timestamp': timestamp,
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
        
        # 이전 대화 기록 추가 (최근 대화만, 인사말 제외)
        recent_history = [msg for msg in conversation_history[-10:] if msg.get('question_type') != 'greeting']
        for msg in recent_history:
            if msg['type'] in ['user', 'assistant']:
                messages.append({
                    "role": "user" if msg['type'] == 'user' else "assistant",
                    "content": msg['content']
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
        
        # AI 응답을 대화 기록에 추가
        conversation_history.append({
            'type': 'assistant',
            'content': ai_content,
            'citations': citations,
            'timestamp': timestamp,
            'question_type': question_type
        })
        
        # 세션 업데이트 (최근 20개 메시지만 유지)
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        session['conversation_history'] = conversation_history
        session.modified = True
        
        return jsonify({
            'success': True,
            'response': ai_content,
            'citations': citations,
            'timestamp': timestamp,
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
    """현재 세션의 대화 기록 반환"""
    conversation_history = session.get('conversation_history', [])
    return jsonify({'conversation': conversation_history})

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """대화 기록 초기화"""
    session['conversation_history'] = []
    session.modified = True
    return jsonify({'success': True, 'message': '대화 기록이 초기화되었습니다.'})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """사용자 설정 저장 (세션에 저장)"""
    try:
        data = request.get_json()
        user_name = data.get('user_name', '사용자')
        search_scope = data.get('search_scope', 'general')
        
        session['user_settings'] = {
            'user_name': user_name,
            'search_scope': search_scope
        }
        session.modified = True
        
        return jsonify({'success': True, 'message': '설정이 저장되었습니다.'})
    except Exception as e:
        logging.error(f"설정 저장 오류: {str(e)}")
        return jsonify({'error': '설정 저장 중 오류가 발생했습니다.'}), 500

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """사용자 설정 조회"""
    settings = session.get('user_settings', {
        'user_name': '사용자',
        'search_scope': 'general'
    })
    return jsonify(settings)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
