/**
 * PPLX AI 검색 서비스 - 모던 UI 버전
 * Welcome Screen과 Chat Interface 상태를 관리하는 클라이언트 스크립트
 */

class PPLXChatApp {
    constructor() {
        this.userSettings = {
            user_name: '사용자',
            search_scope: 'general',
            preferred_model: 'sonar-pro',
            theme: 'light'
        };
        this.selectedModel = 'sonar-pro';
        this.availableModels = {};
        this.isLoading = false;
        this.currentState = 'welcome'; // 'welcome' | 'chat'
        this.currentConversationId = null;
        this.conversationHistory = [];
        this.searchHistory = {
            conversations: [],
            currentPage: 1,
            totalPages: 1,
            isLoading: false,
            searchQuery: '',
            searchTimeout: null
        };
    }

    /**
     * 앱 초기화
     */
    async init() {
        // 테마 초기화
        this.initTheme();
        
        // 설정 로드
        await this.loadSettings();
        
        // 이벤트 바인딩
        this.bindModernUIEvents();
        
        // 초기 상태 설정
        this.setState('welcome');
        
        // 채팅 모드일 때 대화 이력 로드
        if (this.currentState === 'chat') {
            this.loadConversationHistory();
        }
        
        // 사용자 인사말 업데이트
        this.updateUserGreeting();
        
        // 초기 포커스 설정
        this.setInitialFocus();
    }

    /**
     * 테마 초기화
     */
    initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.userSettings.theme = savedTheme;
        this.toggleTheme(savedTheme === 'dark');
    }

    /**
     * 설정 로드
     */
    async loadSettings() {
        try {
            const savedSettings = localStorage.getItem('userSettings');
            if (savedSettings) {
                this.userSettings = { ...this.userSettings, ...JSON.parse(savedSettings) };
            }
            this.selectedModel = this.userSettings.preferred_model;
        } catch (error) {
            console.error('설정 로드 실패:', error);
        }
    }

    /**
     * 모던 UI 이벤트 바인딩
     */
    bindModernUIEvents() {
        // 로고 버튼 (홈으로 돌아가기)
        const logoBtn = document.getElementById('logoBtn');
        if (logoBtn) {
            logoBtn.addEventListener('click', () => {
                this.setState('welcome');
            });
        }
        
        // 테마 토글 버튼
        const themeToggleBtn = document.getElementById('themeToggleBtn');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
        
        // Welcome Screen 이벤트들
        this.bindWelcomeEvents();
        
        // Chat Interface 이벤트들
        this.bindChatEvents();
        
        // 검색 이력 관련 이벤트들
        this.bindSearchHistoryEvents();
        
        // 모바일 사이드바 관련
        this.bindMobileSidebarEvents();
        
        // 설정 관련
        this.bindSettingsEvents();
    }

    /**
     * Welcome Screen 이벤트 바인딩
     */
    bindWelcomeEvents() {
        // Welcome 검색 제출
        const welcomeInput = document.getElementById('welcomeMessageInput');
        const welcomeSubmitBtn = document.getElementById('welcomeSubmitBtn');
        
        if (welcomeSubmitBtn) {
            welcomeSubmitBtn.addEventListener('click', () => {
                this.handleWelcomeSubmit();
            });
        }
        
        if (welcomeInput) {
            welcomeInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleWelcomeSubmit();
                }
            });
            
            // 입력 상태 감지
            welcomeInput.addEventListener('input', () => {
                const hasText = welcomeInput.value.trim().length > 0;
                if (welcomeSubmitBtn) {
                    welcomeSubmitBtn.disabled = !hasText;
                }
            });
        }
        
        // 제안 카드 클릭
        document.querySelectorAll('.suggestion-card').forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.getAttribute('data-prompt');
                if (welcomeInput && prompt) {
                    welcomeInput.value = prompt;
                    this.handleWelcomeSubmit();
                }
            });
        });
        
        // 모델 선택
        const welcomeModelSelect = document.getElementById('welcomeModelSelect');
        if (welcomeModelSelect) {
            welcomeModelSelect.addEventListener('change', (e) => {
                this.selectedModel = e.target.value;
            });
        }
        
        // 검색 모드 선택
        document.querySelectorAll('input[name="searchMode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.userSettings.search_scope = e.target.value;
            });
        });
        
        // Welcome 입력창 자동 리사이즈
        this.setupWelcomeAutoResize();
    }

    /**
     * Chat Interface 이벤트 바인딩
     */
    bindChatEvents() {
        // 새 대화 버튼
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
                this.startNewConversation();
            });
        }
        
        // Chat 메시지 전송
        const chatInput = document.getElementById('chatMessageInput');
        const chatSendBtn = document.getElementById('chatSendBtn');
        
        if (chatSendBtn) {
            chatSendBtn.addEventListener('click', () => {
                this.handleChatSubmit();
            });
        }
        
        if (chatInput) {
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleChatSubmit();
                }
            });
            
            // Chat 입력 상태 감지
            chatInput.addEventListener('input', () => {
                const hasText = chatInput.value.trim().length > 0;
                if (chatSendBtn) {
                    chatSendBtn.disabled = !hasText;
                }
            });
        }
        
        // Chat 모델 선택
        const chatModelSelect = document.getElementById('chatModelSelect');
        if (chatModelSelect) {
            chatModelSelect.addEventListener('change', (e) => {
                this.selectedModel = e.target.value;
            });
        }
        
        // 설정 버튼
        const chatSettingsBtn = document.getElementById('chatSettingsBtn');
        if (chatSettingsBtn) {
            chatSettingsBtn.addEventListener('click', () => {
                this.openSettingsModal();
            });
        }
        
        // Chat 입력창 자동 리사이즈
        this.setupChatAutoResize();
    }

    /**
     * 모바일 사이드바 이벤트 바인딩
     */
    bindMobileSidebarEvents() {
        // 모바일 메뉴 버튼
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', () => {
                this.toggleChatSidebar();
            });
        }
        
        // 사이드바 오버레이
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', () => {
                this.closeChatSidebar();
            });
        }
    }

    /**
     * 검색 이력 관련 이벤트 바인딩
     */
    bindSearchHistoryEvents() {
        // 검색창 이벤트
        const historySearchInput = document.getElementById('historySearchInput');
        const searchClearBtn = document.getElementById('searchClearBtn');
        
        if (historySearchInput) {
            historySearchInput.addEventListener('input', (e) => {
                const query = e.target.value.trim();
                this.handleHistorySearch(query);
                
                // 검색어가 있으면 클리어 버튼 표시
                if (searchClearBtn) {
                    searchClearBtn.style.display = query ? 'block' : 'none';
                }
            });
        }
        
        if (searchClearBtn) {
            searchClearBtn.addEventListener('click', () => {
                if (historySearchInput) {
                    historySearchInput.value = '';
                    historySearchInput.focus();
                    searchClearBtn.style.display = 'none';
                    this.handleHistorySearch('');
                }
            });
        }
        
        // 새 대화 버튼
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => {
                this.createNewConversation();
            });
        }
        
        // 더 보기 버튼
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.loadMoreConversations();
            });
        }
        
        // 키보드 단축키
        document.addEventListener('keydown', (e) => {
            // Ctrl+H로 이력 패널 토글
            if (e.ctrlKey && e.key === 'h') {
                e.preventDefault();
                this.toggleSidebar();
            }
        });
    }

    /**
     * 검색 이력 처리
     */
    async handleHistorySearch(query) {
        // 이전 검색 타이머 취소
        if (this.searchHistory.searchTimeout) {
            clearTimeout(this.searchHistory.searchTimeout);
        }
        
        this.searchHistory.searchQuery = query;
        
        // 검색어가 없으면 즉시 로드
        if (!query) {
            await this.loadConversationHistory();
            return;
        }
        
        // 300ms 지연 후 검색 실행
        this.searchHistory.searchTimeout = setTimeout(async () => {
            await this.loadConversationHistory(1, query);
        }, 300);
    }

    /**
     * 대화 이력 로드
     */
    async loadConversationHistory(page = 1, searchQuery = '') {
        if (this.searchHistory.isLoading) return;
        
        this.searchHistory.isLoading = true;
        this.showHistoryLoading(true);
        
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                per_page: '50'
            });
            
            if (searchQuery) {
                params.append('search', searchQuery);
            }
            
            const response = await fetch(`/api/conversations/list?${params}`);
            const data = await response.json();
            
            if (response.ok) {
                this.searchHistory.conversations = data.conversations;
                this.searchHistory.currentPage = data.pagination.page;
                this.searchHistory.totalPages = data.pagination.pages;
                
                this.renderConversationHistory();
            } else {
                console.error('대화 이력 로드 실패:', data.error);
                this.showHistoryEmpty();
            }
        } catch (error) {
            console.error('대화 이력 로드 오류:', error);
            this.showHistoryEmpty();
        } finally {
            this.searchHistory.isLoading = false;
            this.showHistoryLoading(false);
        }
    }

    /**
     * 대화 이력 렌더링
     */
    renderConversationHistory() {
        const historyEmpty = document.getElementById('historyEmpty');
        const chatHistory = document.getElementById('chatHistory');
        
        if (!this.searchHistory.conversations || this.searchHistory.conversations.favorites.length === 0 && 
            this.searchHistory.conversations.today.length === 0 && 
            this.searchHistory.conversations.yesterday.length === 0 && 
            this.searchHistory.conversations.this_week.length === 0 && 
            this.searchHistory.conversations.older.length === 0) {
            this.showHistoryEmpty();
            return;
        }
        
        if (historyEmpty) historyEmpty.style.display = 'none';
        if (chatHistory) chatHistory.style.display = 'block';
        
        // 각 섹션 렌더링
        this.renderHistorySection('favorites', this.searchHistory.conversations.favorites, 'favoritesSection', 'favoritesList', 'favoritesCount');
        this.renderHistorySection('today', this.searchHistory.conversations.today, 'todaySection', 'todayList', 'todayCount');
        this.renderHistorySection('yesterday', this.searchHistory.conversations.yesterday, 'yesterdaySection', 'yesterdayList', 'yesterdayCount');
        this.renderHistorySection('this_week', this.searchHistory.conversations.this_week, 'thisWeekSection', 'thisWeekList', 'thisWeekCount');
        this.renderHistorySection('older', this.searchHistory.conversations.older, 'olderSection', 'olderList', 'olderCount');
        
        // 더 보기 버튼 표시/숨김
        const loadMoreSection = document.getElementById('loadMoreSection');
        if (loadMoreSection) {
            loadMoreSection.style.display = this.searchHistory.currentPage < this.searchHistory.totalPages ? 'block' : 'none';
        }
    }

    /**
     * 이력 섹션 렌더링
     */
    renderHistorySection(sectionKey, conversations, sectionId, listId, countId) {
        const section = document.getElementById(sectionId);
        const list = document.getElementById(listId);
        const count = document.getElementById(countId);
        
        if (!section || !list || !count) return;
        
        if (conversations.length === 0) {
            section.style.display = 'none';
            return;
        }
        
        section.style.display = 'block';
        count.textContent = conversations.length;
        
        list.innerHTML = conversations.map(conv => this.createHistoryItemHTML(conv)).join('');
        
        // 이벤트 리스너 추가
        list.querySelectorAll('.history-item').forEach(item => {
            const conversationId = item.dataset.conversationId;
            
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.conversation-actions')) {
                    this.loadConversation(conversationId);
                }
            });
        });
        
        // 액션 버튼 이벤트
        list.querySelectorAll('.conversation-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = btn.dataset.action;
                const conversationId = btn.closest('.history-item').dataset.conversationId;
                
                if (action === 'favorite') {
                    this.toggleConversationFavorite(conversationId);
                } else if (action === 'delete') {
                    this.deleteConversation(conversationId);
                }
            });
        });
    }

    /**
     * 이력 항목 HTML 생성
     */
    createHistoryItemHTML(conversation) {
        const isActive = conversation.id === this.currentConversationId;
        const timeAgo = this.getTimeAgo(new Date(conversation.updated_at));
        
        return `
            <div class="history-item ${isActive ? 'active' : ''}" data-conversation-id="${conversation.id}">
                <div class="conversation-content">
                    <div class="conversation-title">${this.escapeHtml(conversation.title || '새 대화')}</div>
                    <div class="conversation-preview">${conversation.message_count}개 메시지</div>
                </div>
                <div class="conversation-time">${timeAgo}</div>
                <div class="conversation-actions">
                    <button class="conversation-action-btn favorite ${conversation.is_favorite ? 'active' : ''}" 
                            data-action="favorite" title="즐겨찾기">
                        <i class="fas fa-star"></i>
                    </button>
                    <button class="conversation-action-btn" data-action="delete" title="삭제">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * 상대 시간 표시
     */
    getTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffMins < 1) return '방금 전';
        if (diffMins < 60) return `${diffMins}분 전`;
        if (diffHours < 24) return `${diffHours}시간 전`;
        if (diffDays < 7) return `${diffDays}일 전`;
        
        return date.toLocaleDateString('ko-KR', { 
            month: 'short', 
            day: 'numeric' 
        });
    }

    /**
     * 로딩 상태 표시
     */
    showHistoryLoading(show) {
        const historyLoading = document.getElementById('historyLoading');
        const chatHistory = document.getElementById('chatHistory');
        
        if (historyLoading) {
            historyLoading.style.display = show ? 'flex' : 'none';
        }
        if (chatHistory) {
            chatHistory.style.display = show ? 'none' : 'block';
        }
    }

    /**
     * 빈 상태 표시
     */
    showHistoryEmpty() {
        const historyEmpty = document.getElementById('historyEmpty');
        const chatHistory = document.getElementById('chatHistory');
        
        if (historyEmpty) historyEmpty.style.display = 'flex';
        if (chatHistory) chatHistory.style.display = 'none';
    }

    /**
     * 새 대화 생성
     */
    async createNewConversation() {
        try {
            const response = await fetch('/api/conversations/new', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title: '새 대화' })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.currentConversationId = data.conversation.id;
                this.setState('chat');
                this.clearChatMessages();
                await this.loadConversationHistory(); // 이력 새로고침
            } else {
                console.error('새 대화 생성 실패:', data.error);
            }
        } catch (error) {
            console.error('새 대화 생성 오류:', error);
        }
    }

    /**
     * 대화 로드
     */
    async loadConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}`);
            const data = await response.json();
            
            if (response.ok) {
                this.currentConversationId = conversationId;
                this.setState('chat');
                this.clearChatMessages();
                
                // 메시지 표시
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        if (msg.message_type === 'user') {
                            this.displayUserMessage(msg.content, false);
                        } else {
                            this.displayAssistantMessage(msg.content, msg.citations || [], false);
                        }
                    });
                }
                
                await this.loadConversationHistory(); // 이력 새로고침
            } else {
                console.error('대화 로드 실패:', data.error);
            }
        } catch (error) {
            console.error('대화 로드 오류:', error);
        }
    }

    /**
     * 즐겨찾기 토글
     */
    async toggleConversationFavorite(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}/favorite`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                await this.loadConversationHistory(); // 이력 새로고침
            } else {
                console.error('즐겨찾기 토글 실패:', data.error);
            }
        } catch (error) {
            console.error('즐겨찾기 토글 오류:', error);
        }
    }

    /**
     * 대화 삭제
     */
    async deleteConversation(conversationId) {
        if (!confirm('이 대화를 삭제하시겠습니까?')) return;
        
        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                if (conversationId === this.currentConversationId) {
                    this.setState('welcome');
                    this.currentConversationId = null;
                }
                await this.loadConversationHistory(); // 이력 새로고침
            } else {
                console.error('대화 삭제 실패:', data.error);
            }
        } catch (error) {
            console.error('대화 삭제 오류:', error);
        }
    }

    /**
     * 더 많은 대화 로드
     */
    async loadMoreConversations() {
        if (this.searchHistory.currentPage >= this.searchHistory.totalPages) return;
        
        await this.loadConversationHistory(
            this.searchHistory.currentPage + 1, 
            this.searchHistory.searchQuery
        );
    }

    /**
     * 채팅 메시지 초기화
     */
    clearChatMessages() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }
    }

    /**
     * 사이드바 토글 (모바일용)
     */
    toggleSidebar() {
        const sidebar = document.getElementById('chatSidebar');
        const overlay = document.getElementById('sidebarOverlay');
        
        if (sidebar && overlay) {
            const isOpen = sidebar.classList.contains('mobile-open');
            
            if (isOpen) {
                sidebar.classList.remove('mobile-open');
                overlay.classList.remove('active');
            } else {
                sidebar.classList.add('mobile-open');
                overlay.classList.add('active');
            }
        }
    }

    /**
     * 설정 관련 이벤트 바인딩
     */
    bindSettingsEvents() {
        // 설정 모달 관련
        const closeSettings = document.getElementById('closeSettings');
        if (closeSettings) {
            closeSettings.addEventListener('click', () => {
                this.closeSettingsModal();
            });
        }
        
        const saveSettingsModal = document.getElementById('saveSettingsModal');
        if (saveSettingsModal) {
            saveSettingsModal.addEventListener('click', () => {
                this.saveSettingsFromModal();
            });
        }
        
        const resetSettings = document.getElementById('resetSettings');
        if (resetSettings) {
            resetSettings.addEventListener('click', () => {
                this.resetToDefaults();
            });
        }
        
        // 설정 탭 전환
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.target.getAttribute('data-tab') || e.target.closest('.tab-button').getAttribute('data-tab');
                if (tabName) {
                    this.switchTab(tabName);
                }
            });
        });
        
        // 모달 외부 클릭 시 닫기
        const settingsModal = document.getElementById('settingsModal');
        if (settingsModal) {
            settingsModal.addEventListener('click', (e) => {
                if (e.target.id === 'settingsModal') {
                    this.closeSettingsModal();
                }
            });
        }
    }

    /**
     * 상태 전환 (Welcome <-> Chat)
     */
    setState(newState) {
        if (this.currentState === newState) return;
        
        const welcomeScreen = document.getElementById('welcomeScreen');
        const chatInterface = document.getElementById('chatInterface');
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        
        this.currentState = newState;
        
        if (newState === 'welcome') {
            // Welcome Screen 표시
            if (welcomeScreen) welcomeScreen.style.display = 'flex';
            if (chatInterface) chatInterface.style.display = 'none';
            if (mobileMenuBtn) mobileMenuBtn.style.display = 'none';
            
            // Welcome 입력창에 포커스
            setTimeout(() => {
                const welcomeInput = document.getElementById('welcomeMessageInput');
                if (welcomeInput) welcomeInput.focus();
            }, 100);
            
        } else if (newState === 'chat') {
            // Chat Interface 표시
            if (welcomeScreen) welcomeScreen.style.display = 'none';
            if (chatInterface) chatInterface.style.display = 'flex';
            if (mobileMenuBtn) mobileMenuBtn.style.display = 'block';
            
            // Chat 입력창에 포커스
            setTimeout(() => {
                const chatInput = document.getElementById('chatMessageInput');
                if (chatInput) chatInput.focus();
            }, 100);
        }
        
        // 상태 변경 애니메이션
        this.animateStateTransition(newState);
    }

    /**
     * 상태 전환 애니메이션
     */
    animateStateTransition(newState) {
        const container = document.querySelector('.app-container');
        if (!container) return;
        
        container.style.opacity = '0.95';
        container.style.transform = 'scale(0.98)';
        
        setTimeout(() => {
            container.style.opacity = '1';
            container.style.transform = 'scale(1)';
            container.style.transition = 'all 0.3s ease';
        }, 150);
        
        setTimeout(() => {
            container.style.transition = '';
        }, 450);
    }

    /**
     * Welcome 화면에서 메시지 제출
     */
    async handleWelcomeSubmit() {
        const input = document.getElementById('welcomeMessageInput');
        if (!input) return;
        
        const message = input.value.trim();
        if (!message) return;
        
        // Chat 모드로 전환
        this.setState('chat');
        
        // 메시지 전송
        await this.sendMessage(message);
        
        // Welcome 입력창 초기화
        input.value = '';
    }

    /**
     * Chat 화면에서 메시지 제출
     */
    async handleChatSubmit() {
        const input = document.getElementById('chatMessageInput');
        if (!input) return;
        
        const message = input.value.trim();
        if (!message) return;
        
        // 메시지 전송
        await this.sendMessage(message);
        
        // Chat 입력창 초기화
        input.value = '';
        input.style.height = 'auto';
    }

    /**
     * 메시지 전송
     */
    async sendMessage(customMessage = null) {
        // 현재 상태에 따라 적절한 입력창에서 메시지 가져오기
        let message;
        let inputElement;
        
        if (customMessage) {
            message = customMessage;
        } else if (this.currentState === 'welcome') {
            inputElement = document.getElementById('welcomeMessageInput');
            message = inputElement ? inputElement.value.trim() : '';
        } else {
            inputElement = document.getElementById('chatMessageInput');
            message = inputElement ? inputElement.value.trim() : '';
        }
        
        if (!message || this.isLoading) return;
        
        this.isLoading = true;
        this.setLoadingState(true);
        
        try {
            // Chat 모드가 아니면 전환
            if (this.currentState !== 'chat') {
                this.setState('chat');
            }
            
            // UI에 사용자 메시지 표시
            this.displayUserMessage(message);
            
            // 입력창 초기화
            if (inputElement) {
                inputElement.value = '';
                if (inputElement.style) {
                    inputElement.style.height = 'auto';
                }
            }
            
            // API 요청
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    model: this.selectedModel,
                    search_scope: this.userSettings.search_scope
                })
            });
            
            this.hideTypingIndicator();
            
            if (response.ok) {
                const data = await response.json();
                this.displayAssistantMessage(
                    data.response, 
                    data.citations || [], 
                    data.timestamp, 
                    true,
                    data.question_type, 
                    data.model_used,
                    data.source_filtering
                );
            } else {
                const errorData = await response.json();
                this.displayErrorMessage(errorData.error || '오류가 발생했습니다.');
            }
            
        } catch (error) {
            console.error('메시지 전송 실패:', error);
            this.hideTypingIndicator();
            this.displayErrorMessage('네트워크 오류가 발생했습니다.');
        } finally {
            this.isLoading = false;
            this.setLoadingState(false);
        }
    }

    /**
     * 사용자 메시지 표시
     */
    displayUserMessage(message, timestamp = null, scroll = true, questionType = null) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message user-message';
        
        messageElement.innerHTML = `
            <div class="message-content">
                ${this.escapeHtml(message)}
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
    displayAssistantMessage(message, citations = [], timestamp = null, scroll = true, questionType = null, modelUsed = null, sourceFiltering = null) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message assistant-message';
        
        let citationsHtml = '';
        if (citations && citations.length > 0) {
            const citationLinks = citations.map(citation => 
                `<a href="${citation}" target="_blank" class="citation-link" title="${citation}">
                    <i class="fas fa-external-link-alt me-1"></i>
                    ${this.getDomainFromUrl(citation)}
                </a>`
            ).join('');
            
            // 소스 필터링 정보 표시
            let filteringInfo = '';
            if (sourceFiltering && sourceFiltering.filtered_count > 0) {
                filteringInfo = `
                    <div class="filtering-info">
                        <small class="text-muted">
                            <i class="fas fa-filter me-1"></i>
                            ${sourceFiltering.total_sources}개 소스 중 ${sourceFiltering.filtered_sources}개 선별
                            (${sourceFiltering.filtered_count}개 관련성 낮은 소스 제외)
                        </small>
                    </div>
                `;
            }
            
            citationsHtml = `
                <div class="citations">
                    <h6><i class="fas fa-link me-1"></i>참고 자료 (${citations.length}개)</h6>
                    ${filteringInfo}
                    ${citationLinks}
                </div>
            `;
        }
        
        messageElement.innerHTML = `
            <div class="assistant-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                ${this.formatMessage(message)}
                ${citationsHtml}
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
        if (!chatMessages) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message assistant-message error-message';
        
        messageElement.innerHTML = `
            <div class="assistant-avatar">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="message-content">
                <div class="error-content">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    ${this.escapeHtml(errorMessage)}
                </div>
            </div>
        `;
        
        chatMessages.appendChild(messageElement);
        this.scrollToBottom();
    }

    /**
     * Welcome 입력창 자동 리사이즈
     */
    setupWelcomeAutoResize() {
        const textarea = document.getElementById('welcomeMessageInput');
        if (!textarea) return;
        
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        });
    }

    /**
     * Chat 입력창 자동 리사이즈
     */
    setupChatAutoResize() {
        const textarea = document.getElementById('chatMessageInput');
        if (!textarea) return;
        
        textarea.addEventListener('input', () => {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        });
    }

    /**
     * Chat 사이드바 토글
     */
    toggleChatSidebar() {
        const sidebar = document.getElementById('chatSidebar');
        const overlay = document.getElementById('sidebarOverlay');
        
        if (sidebar) sidebar.classList.toggle('open');
        if (overlay) overlay.classList.toggle('active');
    }

    /**
     * Chat 사이드바 닫기
     */
    closeChatSidebar() {
        const sidebar = document.getElementById('chatSidebar');
        const overlay = document.getElementById('sidebarOverlay');
        
        if (sidebar) sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
    }

    /**
     * 초기 포커스 설정
     */
    setInitialFocus() {
        setTimeout(() => {
            if (this.currentState === 'welcome') {
                const welcomeInput = document.getElementById('welcomeMessageInput');
                if (welcomeInput) welcomeInput.focus();
            } else {
                const chatInput = document.getElementById('chatMessageInput');
                if (chatInput) chatInput.focus();
            }
        }, 100);
    }

    /**
     * 새 대화 시작
     */
    async startNewConversation() {
        try {
            // Chat 메시지 영역 초기화
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                chatMessages.innerHTML = '';
            }
            
            // 현재 대화 ID 초기화
            this.currentConversationId = null;
            
            // 입력창 초기화 및 포커스
            const chatInput = document.getElementById('chatMessageInput');
            if (chatInput) {
                chatInput.value = '';
                chatInput.focus();
            }
            
            // 모바일에서 사이드바 닫기
            this.closeChatSidebar();
            
            this.showNotification('새 대화를 시작했습니다.', 'success');
            
        } catch (error) {
            console.error('새 대화 시작 오류:', error);
            this.showNotification('새 대화 시작 중 오류가 발생했습니다.', 'error');
        }
    }

    /**
     * 타이핑 인디케이터 표시
     */
    showTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.style.display = 'flex';
        }
    }

    /**
     * 타이핑 인디케이터 숨기기
     */
    hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    /**
     * 로딩 상태 설정
     */
    setLoadingState(loading) {
        if (loading) {
            this.showTypingIndicator();
        } else {
            this.hideTypingIndicator();
        }
        
        // 전송 버튼들 비활성화/활성화
        const welcomeBtn = document.getElementById('welcomeSubmitBtn');
        const chatBtn = document.getElementById('chatSendBtn');
        
        if (welcomeBtn) welcomeBtn.disabled = loading;
        if (chatBtn) chatBtn.disabled = loading;
    }

    /**
     * 채팅 영역 하단으로 스크롤
     */
    scrollToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    /**
     * 사용자 인사말 업데이트
     */
    updateUserGreeting() {
        const chatUserName = document.getElementById('chatUserName');
        if (chatUserName) {
            chatUserName.textContent = this.userSettings.user_name || '사용자';
        }
    }

    /**
     * 테마 토글
     */
    toggleTheme(isDark = null) {
        const html = document.documentElement;
        const themeIcon = document.querySelector('.theme-icon');
        
        if (isDark === null) {
            // 현재 테마 확인하고 토글
            const currentTheme = html.getAttribute('data-theme');
            isDark = currentTheme !== 'dark';
        }
        
        if (isDark) {
            html.setAttribute('data-theme', 'dark');
            if (themeIcon) themeIcon.className = 'fas fa-sun theme-icon';
            this.userSettings.theme = 'dark';
        } else {
            html.setAttribute('data-theme', 'light');
            if (themeIcon) themeIcon.className = 'fas fa-moon theme-icon';
            this.userSettings.theme = 'light';
        }
        
        // 로컬 스토리지에 저장
        localStorage.setItem('theme', this.userSettings.theme);
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
        // 간단한 마크다운 지원
        let formatted = this.escapeHtml(text);
        
        // 코드 블록
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        
        // 인라인 코드
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // 굵은 글씨
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // 기울임
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // 줄바꿈
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }

    /**
     * URL에서 도메인 추출
     */
    getDomainFromUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname.replace('www.', '');
        } catch (e) {
            return url;
        }
    }

    /**
     * 알림 표시
     */
    showNotification(message, type = 'info', duration = 4000) {
        const container = document.getElementById('notificationContainer');
        if (!container) return;
        
        const notification = document.createElement('div');
        
        const icons = {
            success: '✅',
            error: '❌',
            info: 'ℹ️',
            warning: '⚠️'
        };
        
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="notification-icon">${icons[type]}</span>
            <span class="notification-text">${message}</span>
            <button class="notification-close" aria-label="알림 닫기">&times;</button>
        `;
        
        // 닫기 버튼 이벤트
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        container.appendChild(notification);
        
        // 자동 제거
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
        
        // 최대 알림 개수 제한 (5개)
        const notifications = container.querySelectorAll('.notification');
        if (notifications.length > 5) {
            notifications[0].remove();
        }
    }

    /**
     * 설정 모달 열기
     */
    openSettingsModal() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'flex';
            modal.setAttribute('aria-hidden', 'false');
            this.loadSettingsToModal();
        }
    }

    /**
     * 설정 모달 닫기
     */
    closeSettingsModal() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    /**
     * 설정 탭 전환
     */
    switchTab(tabName) {
        // 모든 탭 버튼과 내용 비활성화
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
            btn.setAttribute('aria-selected', 'false');
        });
        
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // 선택된 탭 활성화
        const selectedButton = document.querySelector(`[data-tab="${tabName}"]`);
        const selectedContent = document.getElementById(`${tabName}-tab`);
        
        if (selectedButton && selectedContent) {
            selectedButton.classList.add('active');
            selectedButton.setAttribute('aria-selected', 'true');
            selectedContent.classList.add('active');
        }
    }

    /**
     * 현재 설정값들을 모달에 로드
     */
    loadSettingsToModal() {
        const userNameModal = document.getElementById('userNameModal');
        const searchScopeModal = document.getElementById('searchScopeModal');
        
        if (userNameModal) userNameModal.value = this.userSettings.user_name || '사용자';
        if (searchScopeModal) searchScopeModal.value = this.userSettings.search_scope || 'general';
    }

    /**
     * 모달에서 설정 저장
     */
    async saveSettingsFromModal() {
        try {
            const userNameModal = document.getElementById('userNameModal');
            const searchScopeModal = document.getElementById('searchScopeModal');
            
            const userName = userNameModal ? userNameModal.value.trim() || '사용자' : '사용자';
            const searchScope = searchScopeModal ? searchScopeModal.value : 'general';
            
            // 설정 업데이트
            this.userSettings.user_name = userName;
            this.userSettings.search_scope = searchScope;
            
            // 로컬 스토리지에 저장
            localStorage.setItem('userSettings', JSON.stringify(this.userSettings));
            
            this.showNotification('설정이 저장되었습니다.', 'success');
            this.updateUserGreeting();
            this.closeSettingsModal();
            
        } catch (error) {
            console.error('설정 저장 실패:', error);
            this.showNotification('설정 저장에 실패했습니다.', 'error');
        }
    }

    /**
     * 기본값으로 복원
     */
    resetToDefaults() {
        if (confirm('모든 설정을 기본값으로 복원하시겠습니까?')) {
            this.userSettings = {
                user_name: '사용자',
                search_scope: 'general',
                preferred_model: 'sonar-pro',
                theme: 'light'
            };
            
            this.loadSettingsToModal();
            this.showNotification('설정이 기본값으로 복원되었습니다.', 'info');
        }
    }
}

// 앱 초기화
const app = new PPLXChatApp();
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});