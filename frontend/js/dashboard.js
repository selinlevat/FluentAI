/**
 * FluentAI Dashboard Module
 */

import { api } from './api.js?v=fix1';
import { toast, loading, checkAuth, formatNumber } from './app.js?v=fix1';

// Initialize Dashboard
export async function initDashboard() {
    if (!checkAuth()) return;

    loading.show();

    try {
        const data = await api.getDashboard();
        renderDashboard(data);
    } catch (error) {
        toast.error('Failed to load dashboard');
        console.error(error);
    } finally {
        loading.hide();
    }
}

function renderDashboard(data) {
    // Update user info
    document.getElementById('user-name')?.textContent &&
        (document.getElementById('user-name').textContent = data.name);

    document.getElementById('user-level')?.textContent &&
        (document.getElementById('user-level').textContent = data.cefr_level || 'Take Test');

    // Update Level Progress card with CEFR level (same as my-progress.html)
    updateElement('current-level', data.cefr_level || 'A1');

    // Update stats
    updateElement('xp-total', formatNumber(data.xp_total));
    updateElement('streak-count', data.current_streak);
    updateElement('longest-streak', data.longest_streak);

    // Daily goal progress
    const goal = data.daily_goal;
    if (goal) {
        updateElement('goal-xp', `${goal.earned_xp}/${goal.target_xp} XP`);

        const goalProgress = document.getElementById('goal-progress');
        if (goalProgress) {
            console.log("Daily Goal Data:", goal); // Debugging
            const earned = Number(goal.earned_xp) || 0;
            const target = Number(goal.target_xp) || 50;
            const percent = Math.min((earned / target) * 100, 100);
            goalProgress.style.width = `${percent}%`;
            // Force white color for visibility against green background
            goalProgress.style.backgroundColor = '#ffffff';
            // Add a subtle shadow to make it pop
            goalProgress.style.boxShadow = '0 0 10px rgba(255, 255, 255, 0.3)';
        }

        const goalStatus = document.getElementById('goal-status');
        if (goalStatus) {
            goalStatus.textContent = goal.completed ? '✓ Completed!' : 'In Progress';
            goalStatus.className = goal.completed ? 'success' : '';
        }
    }

    // Calculate level progress based on XP (CEFR level thresholds)
    const levelThresholds = {
        'A1': { min: 0, max: 500, next: 'A2' },
        'A2': { min: 500, max: 1500, next: 'B1' },
        'B1': { min: 1500, max: 3500, next: 'B2' },
        'B2': { min: 3500, max: 7000, next: 'C1' },
        'C1': { min: 7000, max: 12000, next: 'C2' },
        'C2': { min: 12000, max: 20000, next: 'Max' }
    };

    const currentLevel = data.cefr_level || 'A1';
    const xpTotal = data.xp_total || 0;
    const levelInfo = levelThresholds[currentLevel] || levelThresholds['A1'];

    // Calculate progress within current level
    const xpInLevel = xpTotal - levelInfo.min;
    const xpNeededForNext = levelInfo.max - levelInfo.min;
    const progressPercent = Math.min((xpInLevel / xpNeededForNext) * 100, 100);
    const xpRemaining = Math.max(levelInfo.max - xpTotal, 0);

    updateElement('next-level', levelInfo.next);
    updateElement('xp-needed', xpRemaining);

    const levelProgress = document.getElementById('level-progress');
    if (levelProgress) {
        levelProgress.style.width = `${progressPercent}%`;
    }

    // Weekly chart
    renderWeeklyChart(data.weekly_progress);

    // Load skill badges
    loadSkillBadges();

    // Recent achievements
    renderAchievements(data.recent_achievements);

    // Vocabulary to review
    updateElement('vocab-review-count', data.vocabulary_to_review);
}

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function renderWeeklyChart(weeklyData) {
    const container = document.getElementById('weekly-chart');
    if (!container || !weeklyData) return;

    const maxXP = Math.max(...weeklyData.map(d => d.xp_earned), 50);
    const today = new Date().getDay();

    container.innerHTML = weeklyData.map((day, i) => {
        const height = (day.xp_earned / maxXP) * 80;
        const isToday = i === weeklyData.length - 1;

        return `
            <div class="chart-bar ${day.active ? 'active' : ''} ${isToday ? 'today' : ''}">
                <div class="bar" style="height: 80px;">
                    <div class="fill" style="height: ${height}px;"></div>
                </div>
                <span class="day">${day.day}</span>
            </div>
        `;
    }).join('');
}

// Load Skill Badges
async function loadSkillBadges() {
    try {
        const data = await api.getSkillBadges();

        // Update circular progress badges
        updateCircularProgress('daily-xp-badge', data.daily_xp || 0);
        updateCircularProgress('grammar-badge', data.grammar_sprint || 0);
        updateCircularProgress('word-badge', data.word_sprint || 0);
    } catch (error) {
        console.error('Failed to load skill badges:', error);
        // Set default values on error
        updateCircularProgress('daily-xp-badge', 0);
        updateCircularProgress('grammar-badge', 0);
        updateCircularProgress('word-badge', 0);
    }
}

function updateCircularProgress(elementId, percentage) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const circle = element.querySelector('.progress-bar');
    const valueText = element.querySelector('.progress-value');

    if (!circle || !valueText) return;

    // Calculate stroke-dashoffset for circular progress
    const circumference = 283; // 2 * PI * 45 (radius)
    const offset = circumference - (percentage / 100) * circumference;

    circle.style.strokeDashoffset = offset;
    valueText.textContent = `${Math.round(percentage)}%`;
}

function renderAchievements(achievements) {
    const container = document.getElementById('achievements-list');
    if (!container) return;

    if (!achievements || achievements.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding: 1rem;">
                <p style="color: var(--text-muted);">Complete lessons to earn achievements!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = achievements.map(a => `
        <div class="achievement-card">
            <span class="achievement-icon">${a.icon}</span>
            <div class="achievement-info">
                <h4>${a.name}</h4>
                <p>${a.description || ''}</p>
            </div>
        </div>
    `).join('');
}

// Load Lesson Packs
export async function loadLessonPacks() {
    const container = document.getElementById('lesson-packs');
    if (!container) return;

    try {
        const data = await api.getLessonPacks();

        container.innerHTML = data.packs.map(pack => `
            <div class="pack-card ${pack.is_locked ? 'locked' : ''}" 
                 onclick="${pack.is_locked ? '' : `viewPack(${pack.id})`}">
                <div class="pack-icon">${pack.icon}</div>
                <div class="pack-info">
                    <div class="pack-title">${pack.title}</div>
                    <div class="pack-meta">
                        <span class="level-badge ${pack.cefr_level.toLowerCase()}">${pack.cefr_level}</span>
                        <span>${pack.completed_lessons}/${pack.total_lessons} lessons</span>
                    </div>
                </div>
                <div class="pack-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${pack.progress_percent}%"></div>
                    </div>
                </div>
                ${pack.is_locked ? '<span class="lock-icon">🔒</span>' : ''}
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to load packs:', error);
    }
}

window.viewPack = function (packId) {
    window.location.href = `pack.html?id=${packId}`;
};

// Quick Actions
window.startDailyLesson = function () {
    window.location.href = 'daily-lesson.html';
};

window.startGrammarSprint = function () {
    window.location.href = 'grammar-sprint.html';
};

window.startWordSprint = function () {
    window.location.href = 'word-sprint.html';
};

window.startSpeaking = function () {
    window.location.href = 'prepare-me.html';
};

window.startFreeTalk = function () {
    window.location.href = 'talk-loop.html';
};

window.openReview = function () {
    window.location.href = 'review-mode.html';
};

// Export functions for external use
// Export functions for external use
// export { initDashboard, loadLessonPacks };

