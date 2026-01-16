/**
 * FluentAI Lessons Module
 */

import { api } from './api.js';
import { toast, loading, QuestionRenderer, Timer, formatTime } from './app.js';

// Lesson State
let currentLesson = null;
let currentQuestions = [];
let currentIndex = 0;
let answers = [];
let startTime = null;
let lessonTimer = null;
let questionRenderer = null;
let currentLessonType = null; // Store the lesson type for timer reset

// Initialize Lesson
export async function initLesson(type = 'daily') {
    const container = document.getElementById('lesson-container');
    if (!container) return;

    loading.show();

    try {
        // Load lesson based on type
        switch (type) {
            case 'daily':
                currentLesson = await api.getDailyLesson();
                break;
            case 'grammar-sprint':
                currentLesson = await api.getGrammarSprint();
                break;
            case 'word-sprint':
                currentLesson = await api.getWordSprint();
                break;
            default:
                const lessonId = type;
                currentLesson = await api.getLessonQuestions(lessonId);
        }

        currentQuestions = currentLesson.questions || [];
        currentIndex = 0;
        answers = [];
        startTime = Date.now();
        currentLessonType = type; // Save the lesson type for timer reset

        if (currentQuestions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📚</div>
                    <h3>No Questions Available</h3>
                    <p>Please check back later or try a different lesson.</p>
                    <a href="dashboard.html" class="btn btn-primary">Back to Dashboard</a>
                </div>
            `;
            return;
        }

        // Setup renderer
        questionRenderer = new QuestionRenderer(container);

        // Setup timer for timed lessons (per question)
        if (type === 'grammar-sprint' || type === 'word-sprint') {
            const duration = currentLesson.time_per_question || 20;
            setupTimer(duration, true);
        }

        // Render first question
        renderCurrentQuestion();

    } catch (error) {
        toast.error('Failed to load lesson');
        console.error(error);
    } finally {
        loading.hide();
    }
}

function setupTimer(duration, perQuestion = false) {
    const timerEl = document.getElementById('timer');
    if (!timerEl) return;

    timerEl.style.display = 'flex';

    const onComplete = () => {
        if (perQuestion) {
            // Auto-submit and move to next
            handleAnswer(null);
        } else {
            // End entire lesson
            submitLesson();
        }
    };

    lessonTimer = new Timer(timerEl, duration, null, onComplete);
    lessonTimer.start();
}

function renderCurrentQuestion() {
    if (currentIndex >= currentQuestions.length) {
        submitLesson();
        return;
    }

    const question = currentQuestions[currentIndex];

    questionRenderer.render(
        question,
        currentIndex,
        currentQuestions.length,
        handleAnswer
    );

    // Update progress bar
    const progressBar = document.getElementById('progress-fill');
    if (progressBar) {
        const progress = ((currentIndex) / currentQuestions.length) * 100;
        progressBar.style.width = `${progress}%`;
    }
}

// Global answer handler
window.handleAnswer = function (answer) {
    if (!currentQuestions[currentIndex]) return;

    const question = currentQuestions[currentIndex];

    // Select the answer visually
    questionRenderer.selectAnswer(answer);

    // Record answer with question info for sample questions
    answers.push({
        question_id: question.id,
        user_answer: answer,
        time_taken_ms: Date.now() - startTime,
        question_text: question.question || question.sentence || '',
        correct_answer: question.correct_answer,
        options: question.options
    });

    // Check if correct
    let correctAnswer = question.correct_answer;
    if (typeof correctAnswer === 'string') {
        try {
            correctAnswer = JSON.parse(correctAnswer);
        } catch { }
    }

    const isCorrect = String(answer).toLowerCase().trim() ===
        String(correctAnswer).toLowerCase().trim();

    // Show result
    questionRenderer.showResult(isCorrect, correctAnswer);

    // Play sound feedback
    playFeedbackSound(isCorrect);

    // Move to next after delay
    setTimeout(() => {
        currentIndex++;

        // Reset timer for per-question timed lessons (both sprint types)
        if (lessonTimer && (currentLessonType === 'grammar-sprint' || currentLessonType === 'word-sprint')) {
            lessonTimer.reset();
            lessonTimer.start();
        }

        renderCurrentQuestion();
    }, 1000);
};

function playFeedbackSound(correct) {
    // Simple audio feedback (could be enhanced with actual audio files)
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.frequency.value = correct ? 800 : 300;
    gain.gain.value = 0.1;

    osc.start();
    setTimeout(() => osc.stop(), 150);
}

async function submitLesson() {
    if (lessonTimer) {
        lessonTimer.stop();
    }

    const totalTime = Math.floor((Date.now() - startTime) / 1000);

    loading.show();

    try {
        const result = await api.submitLesson(
            currentLesson.lesson_id || 0,
            answers,
            totalTime
        );

        showResults(result);

    } catch (error) {
        toast.error('Failed to submit lesson');
        console.error(error);
    } finally {
        loading.hide();
    }
}

function showResults(result) {
    const container = document.getElementById('lesson-container');
    if (!container) return;

    const percentage = result.score;
    const emoji = percentage >= 80 ? '🎉' : percentage >= 60 ? '👍' : '💪';
    const message = percentage >= 80 ? 'Excellent work!' :
        percentage >= 60 ? 'Good job!' : 'Keep practicing!';

    container.innerHTML = `
        <div class="result-screen">
            <div class="result-icon">${emoji}</div>
            <div class="result-score">${percentage}%</div>
            <div class="result-message">${message}</div>
            
            <div class="result-stats">
                <div class="result-stat">
                    <div class="result-stat-value">+${result.xp_earned}</div>
                    <div class="result-stat-label">XP Earned</div>
                </div>
                <div class="result-stat">
                    <div class="result-stat-value">${result.correct_count}/${result.total_questions}</div>
                    <div class="result-stat-label">Correct</div>
                </div>
                <div class="result-stat">
                    <div class="result-stat-value">🔥 ${result.new_streak}</div>
                    <div class="result-stat-label">Day Streak</div>
                </div>
            </div>
            
            ${result.level_up ? `
                <div class="level-up-banner">
                    <h3>🎊 Level Up!</h3>
                    <p>You've reached ${result.new_level}!</p>
                </div>
            ` : ''}
            
            ${result.mistakes && result.mistakes.length > 0 ? `
                <div class="mistakes-section card" style="margin-top: 2rem; text-align: left;">
                    <h4>Review Your Mistakes</h4>
                    <div style="margin-top: 1rem;">
                        ${result.mistakes.map(m => `
                            <div style="padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
                                <p><strong>Q:</strong> ${m.question}</p>
                                <p style="color: var(--error);">Your answer: ${m.your_answer}</p>
                                <p style="color: var(--success);">Correct: ${m.correct_answer}</p>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            <div style="margin-top: 2rem; display: flex; gap: 1rem; justify-content: center;">
                <a href="dashboard.html" class="btn btn-secondary">Back to Dashboard</a>
                <button onclick="location.reload()" class="btn btn-primary">Try Again</button>
            </div>
        </div>
    `;

    // Update progress bar to 100%
    const progressBar = document.getElementById('progress-fill');
    if (progressBar) {
        progressBar.style.width = '100%';
    }

    // Update user data in localStorage
    const user = api.getUser();
    if (user) {
        user.xp_total = (user.xp_total || 0) + result.xp_earned;
        user.current_streak = result.new_streak;
        if (result.level_up) {
            user.cefr_level = result.new_level;
        }
        api.setUser(user);
    }
}

// Export for use in HTML
window.initLesson = initLesson;
