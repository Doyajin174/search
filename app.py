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

@app.route('/')
def index():
    """메인 페이지 렌더링"""
    # 세션에 대화 기록이 없으면 초기화
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """채팅 API 엔드포인트 - Perplexity AI와 통신"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        search_scope = data.get('search_scope', 'general')
        user_name = data.get('user_name', '사용자')
        
        if not user_message:
            return jsonify({'error': '메시지를 입력해주세요.'}), 400
        
        # 세션에서 대화 기록 가져오기
        if 'conversation_history' not in session:
            session['conversation_history'] = []
        
        conversation_history = session['conversation_history']
        
        # Perplexity API 요청을 위한 메시지 배열 구성
        messages = []
        
        # 시스템 메시지 추가 (개인화 설정 반영)
        system_content = f"당신은 {user_name}님을 위한 AI 검색 어시스턴트입니다. "
        if search_scope == 'news':
            system_content += "최신 뉴스와 시사 정보에 중점을 두어 답변해주세요."
        elif search_scope == 'academic':
            system_content += "학술적이고 전문적인 정보에 중점을 두어 답변해주세요."
        else:
            system_content += "정확하고 유용한 정보를 제공해주세요."
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # 이전 대화 기록 추가 (최근 5개 대화만)
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        for msg in recent_history:
            messages.append({
                "role": "user" if msg['type'] == 'user' else "assistant",
                "content": msg['content']
            })
        
        # 현재 사용자 메시지 추가
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # 검색 범위에 따른 필터 설정
        search_recency_filter = "month"
        if search_scope == 'news':
            search_recency_filter = "day"
        elif search_scope == 'academic':
            search_recency_filter = "year"
        
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
            "return_related_questions": True,
            "search_recency_filter": search_recency_filter,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }
        
        logging.debug(f"Perplexity API 요청: {payload}")
        
        response = requests.post(PERPLEXITY_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        api_response = response.json()
        logging.debug(f"Perplexity API 응답: {api_response}")
        
        # AI 응답 추출
        ai_content = api_response['choices'][0]['message']['content']
        citations = api_response.get('citations', [])
        
        # 대화 기록에 추가
        timestamp = datetime.now().isoformat()
        
        # 사용자 메시지 추가
        conversation_history.append({
            'type': 'user',
            'content': user_message,
            'timestamp': timestamp,
            'user_name': user_name
        })
        
        # AI 응답 추가
        conversation_history.append({
            'type': 'assistant',
            'content': ai_content,
            'citations': citations,
            'timestamp': timestamp
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
            'timestamp': timestamp
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
