/**
 * FluentAI API Client
 * Updated: Fix TZ issue
 */

const API_BASE_URL = 'http://localhost:8000/api';

class APIClient {
    constructor() {
        this.baseUrl = API_BASE_URL;
    }

    getToken() {
        return localStorage.getItem('token');
    }

    setToken(token) {
        localStorage.setItem('token', token);
    }

    clearToken() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }

    getUser() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    }

    setUser(user) {
        localStorage.setItem('user', JSON.stringify(user));
    }

    isAuthenticated() {
        return !!this.getToken();
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const token = this.getToken();

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            if (response.status === 401) {
                this.clearToken();
                window.location.href = '/lingualearn/frontend/pages/login.html';
                throw new Error('Unauthorized');
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // Auth endpoints
    async register(email, password, name) {
        const data = await this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password, name }),
        });
        this.setToken(data.access_token);
        this.setUser(data.user);
        return data;
    }

    async login(email, password) {
        const data = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        this.setToken(data.access_token);
        this.setUser(data.user);
        return data;
    }

    async getCurrentUser() {
        return this.request('/auth/me');
    }

    logout() {
        this.clearToken();
        window.location.href = '/lingualearn/frontend/pages/login.html';
    }

    // Assessment endpoints
    async getPlacementTest() {
        return this.request('/assessment/placement');
    }

    async submitPlacementTest(answers) {
        return this.request('/assessment/submit', {
            method: 'POST',
            body: JSON.stringify(answers),
        });
    }

    async getTransitionTest(level) {
        return this.request(`/assessment/transition/${level}`);
    }

    // Lessons endpoints
    async getDailyLesson() {
        return this.request('/lessons/daily');
    }

    async getDailyCards() {
        return this.request('/lessons/daily/cards');
    }

    async getGrammarSprint() {
        return this.request('/lessons/grammar-sprint');
    }

    async getWordSprint() {
        return this.request('/lessons/word-sprint');
    }

    async getLessonPacks() {
        return this.request('/lessons/packs');
    }

    async getPackLessons(packId) {
        return this.request(`/lessons/packs/${packId}`);
    }

    async getLessonQuestions(lessonId) {
        return this.request(`/lessons/${lessonId}/questions`);
    }

    async submitLesson(lessonId, answers, totalTime) {
        return this.request(`/lessons/${lessonId}/submit`, {
            method: 'POST',
            body: JSON.stringify({
                lesson_id: lessonId,
                answers,
                total_time_seconds: totalTime,
            }),
        });
    }

    // Speaking endpoints
    async getScenarios() {
        return this.request('/speaking/scenarios');
    }

    async startRoleplay(scenarioId) {
        const formData = new FormData();
        formData.append('scenario_id', scenarioId);

        return fetch(`${this.baseUrl}/speaking/roleplay/start`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
            },
            body: formData,
        }).then(r => r.json());
    }

    async roleplayRespond(sessionId, text, audio = null) {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        if (text) formData.append('user_text', text);
        if (audio) formData.append('audio', audio);

        return fetch(`${this.baseUrl}/speaking/roleplay/respond`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
            },
            body: formData,
        }).then(r => r.json());
    }

    async startFreeTalk() {
        return this.request('/speaking/freetalk/start', { method: 'POST' });
    }

    async freeTalkRespond(sessionId, text, audio = null) {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        if (text) formData.append('user_text', text);
        if (audio) formData.append('audio', audio);

        return fetch(`${this.baseUrl}/speaking/freetalk/respond`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
            },
            body: formData,
        }).then(r => r.json());
    }

    async endFreeTalk(sessionId) {
        const formData = new FormData();
        formData.append('session_id', sessionId);

        return fetch(`${this.baseUrl}/speaking/freetalk/end`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
            },
            body: formData,
        }).then(r => r.json());
    }

    // Vocabulary endpoints
    async getVocabularyAdvisor() {
        return this.request('/vocabulary/advisor');
    }

    async addVocabulary(word, translation, context) {
        return this.request(`/vocabulary/add?word=${encodeURIComponent(word)}&translation=${encodeURIComponent(translation || '')}&context=${encodeURIComponent(context || '')}`, {
            method: 'POST',
        });
    }

    async markWordMastered(word) {
        return this.request(`/vocabulary/mark-mastered/${encodeURIComponent(word)}`, {
            method: 'POST',
        });
    }

    // Review endpoints
    async generateReview() {
        return this.request('/review/generate');
    }

    async submitReview(answers, partial = false) {
        return this.request(`/review/submit?partial=${partial}`, {
            method: 'POST',
            body: JSON.stringify(answers),
        });
    }

    // Progress endpoints
    async getDashboard() {
        return this.request('/progress/dashboard');
    }

    async getAchievements() {
        return this.request('/progress/achievements');
    }

    async getSkillBadges() {
        return this.request('/progress/skill-badges');
    }

    async downloadReport() {
        const token = this.getToken();
        try {
            const response = await fetch(`${this.baseUrl}/progress/report/pdf`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Download failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `FluentAI_Progress_Report_${new Date().toISOString().slice(0, 10)}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Download error:', error);
            throw error; // Propagate to caller for toast handling
        }
    }

    // Settings endpoints
    async getProfile() {
        return this.request('/settings/profile');
    }

    async updateProfile(data) {
        return this.request('/settings/profile', {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async updateAPIKeys(data) {
        return this.request('/settings/api-keys', {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async testAPIKey(provider) {
        return this.request(`/settings/test-api-key?provider=${provider}`, {
            method: 'POST',
        });
    }

    async deleteAPIKey(provider) {
        return this.request(`/settings/api-key/${provider}`, {
            method: 'DELETE',
        });
    }

    // Planner endpoints
    async getStudyPlan() {
        return this.request('/planner');
    }

    async updateStudyPlan(data) {
        return this.request('/planner', {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    async getReminderStatus() {
        return this.request('/planner/reminder-status');
    }

    // Admin endpoints
    async getAdminStats() {
        return this.request('/admin/stats');
    }

    async getAdminContent(type = null) {
        const query = type ? `?content_type=${type}` : '';
        return this.request(`/admin/content${query}`);
    }

    async createContent(type, data) {
        return this.request('/admin/content', {
            method: 'POST',
            body: JSON.stringify({ type, data }),
        });
    }

    async updateContent(type, id, data) {
        return this.request(`/admin/content/${type}/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ data }),
        });
    }

    async deleteContent(type, id) {
        return this.request(`/admin/content/${type}/${id}`, {
            method: 'DELETE',
        });
    }

    async getAdminUsers(page = 1) {
        return this.request(`/admin/users?page=${page}`);
    }
}

// Export singleton instance
export const api = new APIClient();
export default api;
