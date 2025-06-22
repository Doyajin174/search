/**
 * PPLX AI 검색 서비스 클라이언트 스크립트
 * 채팅 인터페이스, 테마 관리, 사용자 설정 등을 담당
 */

class PPLXChatApp {
    constructor() {
        this.isLoading = false;
        this.userSettings = {
            user_name: '사용자',
            search_scope: 'general'
        };
        
        this.init();
    }
    
    /**
     * 앱 초기화
     */
    async init() {
        this.bindEvents();
        this.initTheme();
        await this.loadSettings();
        await this.loadConversation();
        this.updateUserGreeting();
        
        // 메시지 입력창에 포커스
        document.getElementById('messageInput').focus();
    }
    
    /**
     * 이벤트 바인딩
     */
    bindEvents() {
        // 채팅 폼 제출
        document.getElementById('chatForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // 설정 저장
        document.getElementById('saveSettings').addEventListener('click', () => {
            this.saveSettings();
        });
        
        // 테마 토글
        document.getElementById('themeToggle').addEventListener('change', (e) => {
            this.toggleTheme(e.target.checked);
        });
        
        // 대화 기록 초기화
        document.getElementById('clearChat').addEventListener('click', () => {
            this.clearConversation();
        });
        
        // 새 대화 시작
        document.getElementById('newChat').addEventListener('click', () => {
            this.startNewConversation();
        });
        
        // 대화 기록 보기 토글
        document.getElementById('showConversations').addEventListener('click', () => {
            this.toggleConversationList();
        });
        
        // 사이드바 토글 (모바일)
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');
        
        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }
        
        // 사이드바 오버레이 클릭 시 닫기
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const sidebarToggle = document.getElementById('sidebarToggle');
            
            if (window.innerWidth < 768 && 
                sidebar.classList.contains('show') && 
                !sidebar.contains(e.target) && 
                !sidebarToggle.contains(e.target)) {
                this.closeSidebar();
            }
        });
        
        // Enter 키로 메시지 전송 (Shift+Enter는 줄바꿈)
        document.getElementById('messageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }
    
    /**
     * 테마 초기화
     */
    initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        const isDark = savedTheme === 'dark';
        
        document.getElementById('themeToggle').checked = isDark;
        document.documentElement.setAttribute('data-theme', savedTheme);
    }
    
    /**
     * 테마 토글
     */
    toggleTheme(isDark) {
        const theme = isDark ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }
    
    /**
     * 사이드바 토글
     */
    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('show');
        
        // 오버레이 추가/제거
        this.toggleSidebarOverlay();
    }
    
    /**
     * 사이드바 닫기
     */
    closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.remove('show');
        this.removeSidebarOverlay();
    }
    
    /**
     * 사이드바 오버레이 토글
     */
    toggleSidebarOverlay() {
        let overlay = document.querySelector('.sidebar-overlay');
        const sidebar = document.getElementById('sidebar');
        
        if (sidebar.classList.contains('show')) {
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'sidebar-overlay';
                overlay.addEventListener('click', () => this.closeSidebar());
                document.body.appendChild(overlay);
            }
            overlay.classList.add('show');
        } else {
            this.removeSidebarOverlay();
        }
    }
    
    /**
     * 사이드바 오버레이 제거
     */
    removeSidebarOverlay() {
        const overlay = document.querySelector('.sidebar-overlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    }
    
    /**
     * 사용자 설정 로드
     */
    async loadSettings() {
        try {
            // 로컬 스토리지에서 설정 로드
            const localSettings = localStorage.getItem('userSettings');
            if (localSettings) {
                this.userSettings = JSON.parse(localSettings);
            }
            
            // 서버에서 세션 기반 설정 로드
            const response = await fetch('/api/settings');
            if (response.ok) {
                const serverSettings = await response.json();
                this.userSettings = { ...this.userSettings, ...serverSettings };
            }
            
            // UI 업데이트
            document.getElementById('userName').value = this.userSettings.user_name;
            document.getElementById('searchScope').value = this.userSettings.search_scope;
            
            // 로컬 스토리지에 저장
            localStorage.setItem('userSettings', JSON.stringify(this.userSettings));
            
        } catch (error) {
            console.error('설정 로드 실패:', error);
        }
    }
    
    /**
     * 사용자 설정 저장
     */
    async saveSettings() {
        try {
            const userName = document.getElementById('userName').value.trim() || '사용자';
            const searchScope = document.getElementById('searchScope').value;
            const theme = document.documentElement.getAttribute('data-theme') || 'light';
            
            this.userSettings = {
                user_name: userName,
                search_scope: searchScope,
                theme: theme
            };
            
            // 로컬 스토리지에 저장
            localStorage.setItem('userSettings', JSON.stringify(this.userSettings));
            
            // 서버에 저장
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.userSettings)
            });
            
            if (response.ok) {
                this.showToast('설정이 저장되었습니다.', 'success');
                this.updateUserGreeting();
            } else {
                throw new Error('서버 설정 저장 실패');
            }
            
        } catch (error) {
            console.error('설정 저장 실패:', error);
            this.showToast('설정 저장에 실패했습니다.', 'error');
        }
    }
    
    /**
     * 사용자 인사말 업데이트
     */
    updateUserGreeting() {
        const greeting = document.getElementById('userGreeting');
        if (greeting) {
            const timeGreeting = this.getTimeBasedGreeting();
            greeting.textContent = `${timeGreeting}, ${this.userSettings.user_name}님!`;
        }
    }
    
    /**
     * 시간대별 인사말 반환
     */
    getTimeBasedGreeting() {
        const hour = new Date().getHours();
        if (hour < 12) return '좋은 아침입니다';
        if (hour < 18) return '안녕하세요';
        return '좋은 저녁입니다';
    }
    
    /**
     * 대화 기록 로드
     */
    async loadConversation() {
        try {
            const response = await fetch('/api/conversation');
            if (response.ok) {
                const data = await response.json();
                this.displayConversationHistory(data.conversation);
            }
        } catch (error) {
            console.error('대화 기록 로드 실패:', error);
        }
    }
    
    /**
     * 대화 기록 표시
     */
    displayConversationHistory(conversation) {
        const chatMessages = document.getElementById('chatMessages');
        
        // 기존 메시지 제거 (환영 메시지 제외)
        const existingMessages = chatMessages.querySelectorAll('.message-bubble:not(.welcome-message)');
        existingMessages.forEach(msg => msg.remove());
        
        // 대화 기록 표시
        conversation.forEach(message => {
            if (message.type === 'user') {
                this.displayUserMessage(message.content, message.timestamp, false, message.question_type);
            } else if (message.type === 'assistant') {
                this.displayAssistantMessage(message.content, message.citations || [], message.timestamp, false, message.question_type);
            }
        });
    }
    
    /**
     * 메시지 전송
     */
    async sendMessage() {
        if (this.isLoading) return;
        
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;
        
        // UI 상태 업데이트
        this.setLoadingState(true);
        messageInput.value = '';
        
        // 사용자 메시지 표시 (질문 유형은 응답 후 업데이트)
        this.displayUserMessage(message);
        
        // 타이핑 인디케이터 표시
        this.showTypingIndicator();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    search_scope: this.userSettings.search_scope,
                    user_name: this.userSettings.user_name
                })
            });
            
            this.hideTypingIndicator();
            
            if (response.ok) {
                const data = await response.json();
                this.displayAssistantMessage(data.response, data.citations || [], data.timestamp, data.question_type);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'API 요청 실패');
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            console.error('메시지 전송 실패:', error);
            this.displayErrorMessage(error.message);
            this.showToast(error.message, 'error');
        } finally {
            this.setLoadingState(false);
            messageInput.focus();
        }
    }
    
    /**
     * 사용자 메시지 표시
     */
    displayUserMessage(message, timestamp = null, scroll = true, questionType = null) {
        const chatMessages = document.getElementById('chatMessages');
        const messageTime = timestamp ? new Date(timestamp) : new Date();
        
        // 질문 유형 표시용 아이콘 및 색상
        const typeInfo = this.getQuestionTypeInfo(questionType);
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message-bubble user-message';
        messageElement.innerHTML = `
            <div class="message-content">
                <div class="d-flex align-items-start">
                    <i class="fas fa-user me-2"></i>
                    <div class="flex-grow-1">
                        ${this.escapeHtml(message)}
                        ${typeInfo.badge ? `<span class="question-type-badge ${typeInfo.class}">${typeInfo.badge}</span>` : ''}
                    </div>
                </div>
            </div>
            <div class="message-time">
                <small class="text-muted">${this.formatTime(messageTime)}</small>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        
        if (scroll) {
            this.scrollToBottom();
        }
    }
    
    /**
     * AI 응답 메시지 표시
     */
    displayAssistantMessage(message, citations = [], timestamp = null, scroll = true, questionType = null) {
        const chatMessages = document.getElementById('chatMessages');
        const messageTime = timestamp ? new Date(timestamp) : new Date();
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message-bubble assistant-message';
        
        let citationsHtml = '';
        if (citations && citations.length > 0) {
            const citationLinks = citations.map(citation => 
                `<a href="${citation}" target="_blank" class="citation-link" title="${citation}">
                    <i class="fas fa-external-link-alt me-1"></i>
                    ${this.getDomainFromUrl(citation)}
                </a>`
            ).join('');
            
            citationsHtml = `
                <div class="citations">
                    <h6><i class="fas fa-link me-1"></i>참고 자료</h6>
                    ${citationLinks}
                </div>
            `;
        }
        
        // 응답 유형에 따른 아이콘 설정
        const responseIcon = questionType === 'greeting' ? 'fas fa-hand-wave' : 'fas fa-robot';
        
        messageElement.innerHTML = `
            <div class="message-content">
                <i class="${responseIcon} me-2"></i>
                ${this.formatMessage(message)}
                ${citationsHtml}
            </div>
            <div class="message-time">
                <small class="text-muted">${this.formatTime(messageTime)}</small>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        
        if (scroll) {
            this.scrollToBottom();
        }
    }
    
    /**
     * 에러 메시지 표시
     */
    displayErrorMessage(errorMessage) {
        const chatMessages = document.getElementById('chatMessages');
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message-bubble assistant-message';
        messageElement.innerHTML = `
            <div class="message-content">
                <i class="fas fa-exclamation-triangle text-danger me-2"></i>
                <span class="text-danger">죄송합니다. 오류가 발생했습니다: ${this.escapeHtml(errorMessage)}</span>
            </div>
            <div class="message-time">
                <small class="text-muted">${this.formatTime(new Date())}</small>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }
    
    /**
     * 타이핑 인디케이터 표시
     */
    showTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    /**
     * 타이핑 인디케이터 숨기기
     */
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        typingIndicator.style.display = 'none';
    }
    
    /**
     * 로딩 상태 설정
     */
    setLoadingState(loading) {
        this.isLoading = loading;
        const sendButton = document.getElementById('sendButton');
        const messageInput = document.getElementById('messageInput');
        
        if (loading) {
            sendButton.disabled = true;
            sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span class="d-none d-sm-inline ms-1">전송 중...</span>';
            messageInput.disabled = true;
        } else {
            sendButton.disabled = false;
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i><span class="d-none d-sm-inline ms-1">전송</span>';
            messageInput.disabled = false;
        }
    }
    
    /**
     * 현재 대화 삭제
     */
    async clearConversation() {
        if (!confirm('현재 대화를 삭제하시겠습니까?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                // UI에서 메시지 제거 (환영 메시지 제외)
                const chatMessages = document.getElementById('chatMessages');
                const existingMessages = chatMessages.querySelectorAll('.message-bubble:not(.welcome-message)');
                existingMessages.forEach(msg => msg.remove());
                
                this.showToast('대화가 삭제되었습니다.', 'success');
                
                // 대화 목록 새로고침
                if (document.getElementById('conversationList').style.display !== 'none') {
                    this.loadConversationList();
                }
            } else {
                throw new Error('대화 삭제 실패');
            }
            
        } catch (error) {
            console.error('대화 삭제 실패:', error);
            this.showToast('대화 삭제에 실패했습니다.', 'error');
        }
    }
    
    /**
     * 새 대화 시작
     */
    async startNewConversation() {
        try {
            // 현재 대화 종료
            await fetch('/api/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            // UI 초기화
            const chatMessages = document.getElementById('chatMessages');
            const existingMessages = chatMessages.querySelectorAll('.message-bubble:not(.welcome-message)');
            existingMessages.forEach(msg => msg.remove());
            
            this.showToast('새 대화를 시작합니다.', 'success');
            
            // 메시지 입력창에 포커스
            document.getElementById('messageInput').focus();
            
        } catch (error) {
            console.error('새 대화 시작 실패:', error);
            this.showToast('새 대화 시작에 실패했습니다.', 'error');
        }
    }
    
    /**
     * 대화 목록 토글
     */
    async toggleConversationList() {
        const conversationList = document.getElementById('conversationList');
        const showButton = document.getElementById('showConversations');
        
        if (conversationList.style.display === 'none') {
            await this.loadConversationList();
            conversationList.style.display = 'block';
            showButton.innerHTML = '<i class="fas fa-eye-slash me-1"></i>대화 기록 숨기기';
        } else {
            conversationList.style.display = 'none';
            showButton.innerHTML = '<i class="fas fa-history me-1"></i>대화 기록 보기';
        }
    }
    
    /**
     * 대화 목록 로드
     */
    async loadConversationList() {
        try {
            const response = await fetch('/api/conversations');
            if (response.ok) {
                const data = await response.json();
                this.displayConversationList(data.conversations);
            } else {
                throw new Error('대화 목록 조회 실패');
            }
        } catch (error) {
            console.error('대화 목록 로드 실패:', error);
            this.showToast('대화 목록을 불러올 수 없습니다.', 'error');
        }
    }
    
    /**
     * 대화 목록 표시
     */
    displayConversationList(conversations) {
        const conversationItems = document.getElementById('conversationItems');
        conversationItems.innerHTML = '';
        
        if (conversations.length === 0) {
            conversationItems.innerHTML = '<p class="text-muted small">저장된 대화가 없습니다.</p>';
            return;
        }
        
        conversations.forEach(conv => {
            const convElement = document.createElement('div');
            convElement.className = 'conversation-item border rounded p-2 mb-2 cursor-pointer';
            convElement.style.cursor = 'pointer';
            
            const updatedTime = new Date(conv.updated_at);
            const timeStr = this.formatTime(updatedTime);
            
            convElement.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1" onclick="chatApp.loadSpecificConversation('${conv.id}')">
                        <small class="d-block text-truncate fw-semibold">${this.escapeHtml(conv.title)}</small>
                        <small class="text-muted">${timeStr} • ${conv.message_count}개 메시지</small>
                    </div>
                    <button class="btn btn-sm btn-outline-danger ms-2" onclick="chatApp.deleteSpecificConversation('${conv.id}')" title="삭제">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            conversationItems.appendChild(convElement);
        });
    }
    
    /**
     * 특정 대화 로드
     */
    async loadSpecificConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversation/${conversationId}`);
            if (response.ok) {
                const data = await response.json();
                this.displayConversationHistory(data.conversation);
                this.showToast('대화를 불러왔습니다.', 'success');
                
                // 대화 목록 숨기기
                document.getElementById('conversationList').style.display = 'none';
                document.getElementById('showConversations').innerHTML = '<i class="fas fa-history me-1"></i>대화 기록 보기';
            } else {
                throw new Error('대화 로드 실패');
            }
        } catch (error) {
            console.error('특정 대화 로드 실패:', error);
            this.showToast('대화를 불러올 수 없습니다.', 'error');
        }
    }
    
    /**
     * 특정 대화 삭제
     */
    async deleteSpecificConversation(conversationId) {
        if (!confirm('이 대화를 삭제하시겠습니까?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/conversation/${conversationId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.showToast('대화가 삭제되었습니다.', 'success');
                // 대화 목록 새로고침
                this.loadConversationList();
            } else {
                throw new Error('대화 삭제 실패');
            }
        } catch (error) {
            console.error('대화 삭제 실패:', error);
            this.showToast('대화 삭제에 실패했습니다.', 'error');
        }
    }
    
    /**
     * 채팅 영역 하단으로 스크롤
     */
    scrollToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        setTimeout(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 100);
    }
    
    /**
     * 토스트 메시지 표시
     */
    showToast(message, type = 'info') {
        const toastId = type === 'error' ? 'errorToast' : 'successToast';
        const toastBodyId = type === 'error' ? 'errorToastBody' : 'successToastBody';
        
        const toastElement = document.getElementById(toastId);
        const toastBody = document.getElementById(toastBodyId);
        
        if (toastElement && toastBody) {
            toastBody.textContent = message;
            
            const toast = new bootstrap.Toast(toastElement);
            toast.show();
        }
    }
    
    /**
     * HTML 이스케이프
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * 메시지 포맷팅 (마크다운 지원)
     */
    formatMessage(text) {
        // 기본적인 마크다운 변환
        return this.escapeHtml(text)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }
    
    /**
     * URL에서 도메인 추출
     */
    getDomainFromUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname.replace('www.', '');
        } catch {
            return url.substring(0, 30) + '...';
        }
    }
    
    /**
     * 시간 포맷팅
     */
    formatTime(date) {
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return '지금';
        if (diffMins < 60) return `${diffMins}분 전`;
        if (diffHours < 24) return `${diffHours}시간 전`;
        if (diffDays < 7) return `${diffDays}일 전`;
        
        return date.toLocaleDateString('ko-KR', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    /**
     * 질문 유형 정보 반환
     */
    getQuestionTypeInfo(questionType) {
        const typeMap = {
            'greeting': {
                badge: '인사',
                class: 'badge-greeting',
                icon: 'fas fa-hand-wave'
            },
            'realtime': {
                badge: '실시간',
                class: 'badge-realtime',
                icon: 'fas fa-clock'
            },
            'learning': {
                badge: '학습',
                class: 'badge-learning',
                icon: 'fas fa-graduation-cap'
            },
            'info_search': {
                badge: '검색',
                class: 'badge-search',
                icon: 'fas fa-search'
            },
            'general': {
                badge: null,
                class: '',
                icon: 'fas fa-comment'
            }
        };
        
        return typeMap[questionType] || typeMap['general'];
    }
}

// 앱 초기화 및 전역 변수
let chatApp;
document.addEventListener('DOMContentLoaded', () => {
    chatApp = new PPLXChatApp();
});

// 윈도우 리사이즈 시 사이드바 상태 조정
window.addEventListener('resize', () => {
    if (window.innerWidth >= 768) {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.remove('show');
        
        const overlay = document.querySelector('.sidebar-overlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
    }
});
