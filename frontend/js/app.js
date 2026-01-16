/**
 * FluentAI Main Application
 */

import { api } from './api.js?v=fix1';

// Toast Notification System
class Toast {
    constructor() {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${this.getIcon(type)}</span>
            <span class="toast-message">${message}</span>
        `;
        this.container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
        };
        return icons[type] || icons.info;
    }

    success(message) { this.show(message, 'success'); }
    error(message) { this.show(message, 'error'); }
    warning(message) { this.show(message, 'warning'); }
    info(message) { this.show(message, 'info'); }
}

export const toast = new Toast();

// Loading Overlay
class Loading {
    constructor() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'loading-overlay';
        this.overlay.style.display = 'none';
        this.overlay.innerHTML = '<div class="loading-spinner"></div>';
        document.body.appendChild(this.overlay);
    }

    show() {
        this.overlay.style.display = 'flex';
    }

    hide() {
        this.overlay.style.display = 'none';
    }
}

export const loading = new Loading();

// Audio Recorder for Speaking Features
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
    }

    async start() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            return true;
        } catch (error) {
            console.error('Microphone access error:', error);
            toast.error('Could not access microphone. Please check permissions.');
            return false;
        }
    }

    stop() {
        return new Promise((resolve) => {
            if (this.mediaRecorder && this.isRecording) {
                this.mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                    this.isRecording = false;
                    resolve(audioBlob);
                };
                this.mediaRecorder.stop();
                this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            } else {
                resolve(null);
            }
        });
    }
}

export const audioRecorder = new AudioRecorder();

// Utility Functions
export function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

export function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

// Check Authentication
export function checkAuth() {
    if (!api.isAuthenticated()) {
        window.location.href = '/lingualearn/frontend/pages/login.html';
        return false;
    }
    return true;
}

// Navigate function
export function navigate(path) {
    window.location.href = `/lingualearn/frontend/pages/${path}`;
}

// Initialize Sidebar
export function initSidebar() {
    const user = api.getUser();
    if (!user) return;

    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;

    // Update user info in sidebar
    const userNameEl = sidebar.querySelector('.user-name');
    const userLevelEl = sidebar.querySelector('.user-level');

    if (userNameEl) userNameEl.textContent = user.name;
    if (userLevelEl) userLevelEl.textContent = user.cefr_level || 'Take Assessment';

    // Handle navigation
    const navItems = sidebar.querySelectorAll('.nav-item');
    const currentPath = window.location.pathname;

    navItems.forEach(item => {
        const href = item.getAttribute('href');
        if (href && currentPath.includes(href.replace('.html', ''))) {
            item.classList.add('active');
        }

        item.addEventListener('click', (e) => {
            if (item.dataset.action === 'logout') {
                e.preventDefault();
                api.logout();
            }
        });
    });

    // Mobile menu toggle
    const menuToggle = document.querySelector('.menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }
}

// Question Renderer
export class QuestionRenderer {
    constructor(container) {
        this.container = container;
        this.currentAnswer = null;
    }

    render(question, index, total, onAnswer) {
        this.currentAnswer = null;

        const html = `
            <div class="question-container">
                <div class="question-progress">
                    <div class="question-dots">
                        ${Array(total).fill(0).map((_, i) => `
                            <div class="question-dot ${i < index ? 'correct' : ''} ${i === index ? 'active' : ''}"></div>
                        `).join('')}
                    </div>
                </div>
                <div class="question-text">
                    ${this.formatQuestion(question)}
                </div>
                <div class="options-grid">
                    ${this.renderOptions(question, onAnswer)}
                </div>
            </div>
        `;

        this.container.innerHTML = html;
    }

    formatQuestion(question) {
        if (question.type === 'gap_fill') {
            return question.sentence.replace('___', '<span class="blank"></span>');
        }
        return question.question;
    }

    renderOptions(question, onAnswer) {
        const options = question.options || [];
        return options.map((option, i) => {
            // Escape single quotes for the JS function call: ' -> \'
            const jsSafeOption = option.replace(/'/g, "\\'");
            // Escape double quotes for the HTML attribute: " -> &quot;
            const htmlSafeOption = option.replace(/"/g, '&quot;');

            return `
            <button class="option-btn" data-answer="${htmlSafeOption}" onclick="window.handleAnswer('${jsSafeOption}')">
                ${option}
            </button>
            `;
        }).join('');
    }

    showResult(isCorrect, correctAnswer) {
        const buttons = this.container.querySelectorAll('.option-btn');
        buttons.forEach(btn => {
            btn.disabled = true;
            const answer = btn.dataset.answer;
            const originalText = btn.textContent.trim();

            if (answer === correctAnswer) {
                btn.classList.add('correct');
                // Add checkmark icon to correct answer
                btn.innerHTML = `<span style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                    <span>✓</span>
                    <span>${originalText}</span>
                </span>`;
            } else if (btn.classList.contains('selected') && !isCorrect) {
                btn.classList.add('wrong');
                // Add X icon to wrong answer
                btn.innerHTML = `<span style="display: flex; align-items: center; justify-content: center; gap: 0.5rem;">
                    <span>✕</span>
                    <span>${originalText}</span>
                </span>`;
            }
        });
    }

    selectAnswer(answer) {
        const buttons = this.container.querySelectorAll('.option-btn');
        buttons.forEach(btn => {
            btn.classList.toggle('selected', btn.dataset.answer === answer);
        });
        this.currentAnswer = answer;
    }
}

// Timer Component
export class Timer {
    constructor(element, duration, onTick, onComplete) {
        this.element = element;
        this.duration = duration;
        this.remaining = duration;
        this.onTick = onTick;
        this.onComplete = onComplete;
        this.interval = null;
    }

    start() {
        this.interval = setInterval(() => {
            this.remaining--;
            this.update();

            if (this.onTick) this.onTick(this.remaining);

            if (this.remaining <= 0) {
                this.stop();
                if (this.onComplete) this.onComplete();
            }
        }, 1000);
    }

    stop() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }

    update() {
        if (!this.element) return;

        this.element.textContent = formatTime(this.remaining);
        this.element.classList.remove('warning', 'danger');

        if (this.remaining <= 5) {
            this.element.classList.add('danger');
        } else if (this.remaining <= 10) {
            this.element.classList.add('warning');
        }
    }

    reset() {
        this.stop();
        this.remaining = this.duration;
        this.update();
    }
}

// Modal Component
export class Modal {
    constructor(id) {
        this.overlay = document.getElementById(id);
        if (this.overlay) {
            this.modal = this.overlay.querySelector('.modal');
            this.setupEvents();
        }
    }

    setupEvents() {
        // Close on overlay click
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.close();
        });

        // Close button
        const closeBtn = this.overlay.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.overlay.classList.contains('active')) {
                this.close();
            }
        });
    }

    open() {
        this.overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    close() {
        this.overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    setContent(html) {
        const content = this.modal.querySelector('.modal-content');
        if (content) content.innerHTML = html;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize sidebar if present
    initSidebar();

    // Check for auth pages
    const isAuthPage = window.location.pathname.includes('login') ||
        window.location.pathname.includes('register');
    const isLandingPage = window.location.pathname.endsWith('index.html') ||
        window.location.pathname.endsWith('/frontend/');

    // Redirect to dashboard if logged in on landing/auth pages
    if ((isAuthPage || isLandingPage) && api.isAuthenticated()) {
        // Don't redirect, let user access
    }
});

// Global error handler
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    toast.error('An error occurred. Please try again.');
});
