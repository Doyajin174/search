"""
소스 필터링 및 관련성 검증 시스템
질문과 관련성이 높고 신뢰할 수 있는 소스만 필터링하여 표시
"""

import re
import logging
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple

# 도메인별 신뢰도 점수
DOMAIN_TRUST_SCORES = {
    # 높은 신뢰도 (90-100점)
    "wikipedia.org": 95,
    "ko.wikipedia.org": 95,
    "naver.com": 90,
    "daum.net": 90,
    "gov.kr": 100,
    "go.kr": 100,
    "edu": 95,
    "ac.kr": 95,
    "or.kr": 85,
    
    # 중간 신뢰도 (70-89점)
    "news.naver.com": 85,
    "news.daum.net": 85,
    "ytn.co.kr": 80,
    "kbs.co.kr": 85,
    "sbs.co.kr": 85,
    "mbc.co.kr": 85,
    "chosun.com": 80,
    "joongang.co.kr": 80,
    "hankyung.com": 75,
    "khan.co.kr": 75,
    "hani.co.kr": 75,
    "github.com": 85,
    "stackoverflow.com": 80,
    "docs.microsoft.com": 85,
    "docs.python.org": 90,
    
    # 낮은 신뢰도 (30-69점)
    "blog.naver.com": 50,
    "tistory.com": 45,
    "youtube.com": 30,
    "instagram.com": 20,
    "facebook.com": 25,
    "twitter.com": 35,
    "tiktok.com": 15,
    "spotify.com": 20,
    "pinterest.com": 25,
    "reddit.com": 40
}

# 소스 타입 분류
SOURCE_TYPES = {
    "official": ["gov.kr", "go.kr", "company.com", "organization.org", "docs.", "microsoft.com", "google.com", "apple.com"],
    "news": ["news.", "press.", "media.", "ytn.co.kr", "kbs.co.kr", "sbs.co.kr", "mbc.co.kr", "chosun.com", "joongang.co.kr"],
    "academic": ["edu", "ac.kr", "scholar.", "research.", "ieee.org", "acm.org", "arxiv.org"],
    "social": ["instagram.com", "facebook.com", "twitter.com", "tiktok.com", "pinterest.com"],
    "entertainment": ["youtube.com", "spotify.com", "netflix.com", "twitch.tv"],
    "blog": ["blog.", "tistory.com", "wordpress.com", "medium.com"],
    "wiki": ["wikipedia.org", "namuwiki.com"],
    "tech": ["github.com", "stackoverflow.com", "dev.to", "docs."]
}

def extract_keywords(text: str) -> List[str]:
    """텍스트에서 주요 키워드 추출 (한국어 최적화)"""
    if not text:
        return []
    
    # 한국어와 영어 키워드 추출
    text = text.lower()
    
    # 불용어 제거
    stop_words = {
        '그', '이', '저', '것', '수', '있', '없', '하', '되', '된', '될', '로', '를', '의', '가', '은', '는', 
        'the', 'is', 'at', 'which', 'on', 'and', 'or', 'but', 'in', 'with', 'to', 'for', 'of', 'as', 'by'
    }
    
    # 단어 분리 (한글, 영문, 숫자만 유지)
    words = re.findall(r'[가-힣a-z0-9]+', text)
    
    # 의미 있는 키워드만 추출 (2글자 이상)
    keywords = [word for word in words if len(word) >= 2 and word not in stop_words]
    
    return list(set(keywords))

def calculate_keyword_match(question_keywords: List[str], source_keywords: List[str]) -> float:
    """키워드 매칭 점수 계산"""
    if not question_keywords or not source_keywords:
        return 0.0
    
    # 정확한 매칭
    exact_matches = len(set(question_keywords) & set(source_keywords))
    
    # 부분 매칭 (포함 관계)
    partial_matches = 0
    for q_keyword in question_keywords:
        for s_keyword in source_keywords:
            if q_keyword in s_keyword or s_keyword in q_keyword:
                partial_matches += 0.5
                break
    
    # 점수 계산 (0-100)
    total_score = (exact_matches * 2 + partial_matches) / len(question_keywords)
    return min(100, total_score * 50)  # 최대 100점으로 정규화

def get_domain_trust_score(url: str) -> float:
    """도메인 신뢰도 점수 반환"""
    if not url:
        return 50.0
    
    try:
        domain = urlparse(url).netloc.lower()
        
        # 정확한 도메인 매칭
        if domain in DOMAIN_TRUST_SCORES:
            return DOMAIN_TRUST_SCORES[domain]
        
        # 부분 매칭
        for trusted_domain, score in DOMAIN_TRUST_SCORES.items():
            if trusted_domain in domain:
                return score
        
        # 기본 점수 (알려지지 않은 도메인)
        return 50.0
        
    except Exception:
        return 30.0

def get_source_type(url: str) -> str:
    """소스 타입 분류"""
    if not url:
        return "unknown"
    
    try:
        domain = urlparse(url).netloc.lower()
        path = urlparse(url).path.lower()
        
        for source_type, patterns in SOURCE_TYPES.items():
            for pattern in patterns:
                if pattern in domain or pattern in path:
                    return source_type
        
        return "general"
        
    except Exception:
        return "unknown"

def get_source_type_score(url: str, question: str) -> float:
    """질문 유형에 따른 소스 타입 적합성 점수"""
    source_type = get_source_type(url)
    question_lower = question.lower()
    
    # 질문 내용 기반 소스 타입 점수
    type_scores = {
        "official": 90,
        "academic": 85,
        "news": 80,
        "wiki": 85,
        "tech": 75,
        "general": 60,
        "blog": 40,
        "social": 20,
        "entertainment": 15
    }
    
    base_score = type_scores.get(source_type, 50)
    
    # 질문 내용에 따른 보정
    if any(keyword in question_lower for keyword in ['뉴스', '최신', '현재', '오늘']):
        if source_type == "news":
            base_score += 15
    
    if any(keyword in question_lower for keyword in ['학습', '공부', '연구', '논문', '이론']):
        if source_type in ["academic", "wiki"]:
            base_score += 15
    
    if any(keyword in question_lower for keyword in ['코딩', '프로그래밍', 'python', 'javascript', '개발']):
        if source_type == "tech":
            base_score += 20
    
    return min(100, base_score)

def analyze_source_relevance(question: str, source_title: str, source_url: str, source_content: str = "") -> Dict[str, Any]:
    """소스 관련성 분석"""
    try:
        question_keywords = extract_keywords(question)
        source_text = f"{source_title} {source_content}"
        source_keywords = extract_keywords(source_text)
        
        # 키워드 매칭 점수 (50% 가중치)
        keyword_score = calculate_keyword_match(question_keywords, source_keywords)
        
        # 도메인 신뢰도 점수 (30% 가중치)
        domain_score = get_domain_trust_score(source_url)
        
        # 소스 타입 관련성 점수 (20% 가중치)
        type_score = get_source_type_score(source_url, question)
        
        # 최종 관련성 점수 (가중평균)
        relevance_score = (keyword_score * 0.5) + (domain_score * 0.3) + (type_score * 0.2)
        
        return {
            "score": relevance_score,
            "keyword_score": keyword_score,
            "domain_score": domain_score,
            "type_score": type_score,
            "keywords": question_keywords,
            "domain": urlparse(source_url).netloc if source_url else "",
            "source_type": get_source_type(source_url)
        }
        
    except Exception as e:
        logging.error(f"소스 관련성 분석 오류: {str(e)}")
        return {
            "score": 30.0,
            "keyword_score": 0,
            "domain_score": 30,
            "type_score": 30,
            "keywords": [],
            "domain": "",
            "source_type": "unknown"
        }

def get_filtering_rules(question_type: str, question: str) -> Dict[str, Any]:
    """질문 유형별 소스 필터링 규칙"""
    rules = {
        "greeting": {
            "min_relevance_score": 0,
            "exclude_types": ["all"],
            "max_sources": 0,
            "description": "인사말 - 검색 비활성화"
        },
        "info_search": {
            "min_relevance_score": 60,
            "exclude_types": ["social", "entertainment"],
            "preferred_types": ["official", "news", "academic", "wiki"],
            "max_sources": 5,
            "description": "정보 검색 - 신뢰할 수 있는 소스 우선"
        },
        "learning": {
            "min_relevance_score": 70,
            "exclude_types": ["social", "entertainment"],
            "preferred_types": ["academic", "wiki", "official"],
            "max_sources": 4,
            "description": "학습 질문 - 교육적 소스 우선"
        },
        "realtime": {
            "min_relevance_score": 65,
            "exclude_types": ["social", "entertainment", "blog"],
            "preferred_types": ["news", "official"],
            "max_sources": 5,
            "time_filter": "recent",
            "description": "실시간 정보 - 뉴스 및 공식 소스 우선"
        },
        "general": {
            "min_relevance_score": 55,
            "exclude_types": ["social", "entertainment"],
            "preferred_types": ["wiki", "official", "news"],
            "max_sources": 5,
            "description": "일반 질문 - 균형잡힌 필터링"
        }
    }
    
    # 코딩 관련 질문 특별 처리
    if any(keyword in question.lower() for keyword in ['코딩', '프로그래밍', 'python', 'javascript', '개발', 'code']):
        rules["coding"] = {
            "min_relevance_score": 75,
            "exclude_types": ["social", "entertainment"],
            "preferred_types": ["tech", "official", "academic"],
            "allowed_domains": ["github.com", "stackoverflow.com", "docs."],
            "max_sources": 4,
            "description": "코딩 질문 - 기술 문서 우선"
        }
        return rules["coding"]
    
    return rules.get(question_type, rules["general"])

def filter_sources(sources: List[Dict[str, Any]], question: str, question_type: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """소스 필터링 메인 함수"""
    if not sources:
        return [], {"filtered_count": 0, "total_count": 0}
    
    rules = get_filtering_rules(question_type, question)
    
    # 인사말 등으로 검색이 비활성화된 경우
    if rules["max_sources"] == 0:
        return [], {
            "filtered_count": len(sources),
            "total_count": len(sources),
            "filter_reason": rules["description"]
        }
    
    # 각 소스 분석
    analyzed_sources = []
    for source in sources:
        analysis = analyze_source_relevance(
            question,
            source.get("title", ""),
            source.get("url", ""),
            source.get("excerpt", "")
        )
        
        analyzed_source = {
            **source,
            "relevance_score": analysis["score"],
            "domain": analysis["domain"],
            "source_type": analysis["source_type"],
            "analysis": analysis
        }
        analyzed_sources.append(analyzed_source)
    
    # 필터링 적용
    filtered_sources = []
    for source in analyzed_sources:
        # 최소 관련성 점수 확인
        if source["relevance_score"] < rules["min_relevance_score"]:
            continue
        
        # 제외 타입 확인
        if "all" in rules.get("exclude_types", []):
            continue
            
        if source["source_type"] in rules.get("exclude_types", []):
            continue
        
        # 허용 도메인 확인 (있는 경우)
        allowed_domains = rules.get("allowed_domains", [])
        if allowed_domains:
            if not any(domain in source.get("url", "") for domain in allowed_domains):
                continue
        
        filtered_sources.append(source)
    
    # 선호 타입 우선 정렬
    preferred_types = rules.get("preferred_types", [])
    filtered_sources.sort(key=lambda x: (
        -(preferred_types.index(x["source_type"]) if x["source_type"] in preferred_types else len(preferred_types)),
        -x["relevance_score"]
    ))
    
    # 최대 소스 개수 제한
    final_sources = filtered_sources[:rules["max_sources"]]
    
    filter_stats = {
        "filtered_count": len(sources) - len(final_sources),
        "total_count": len(sources),
        "filter_rules": rules["description"],
        "min_score_used": rules["min_relevance_score"],
        "excluded_types": rules.get("exclude_types", [])
    }
    
    return final_sources, filter_stats