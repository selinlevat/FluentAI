/**
 * FluentAI Speaking Module - AI Roleplay & Free Talk
 */

import { api } from './api.js';
import { toast, loading, audioRecorder } from './app.js';

let currentSession = null;
let isRecording = false;
let conversationHistory = [];

// Initialize Scenarios Page
export async function loadScenarios() {
    const container = document.getElementById('scenarios-container');
    if (!container) return;
    
    loading.show();
    
    try {
        const data = await api.getScenarios();
        
        container.innerHTML = `
            <div class="scenarios-grid">
                ${data.scenarios.map(scenario => `
                    <div class="scenario-card" onclick="startRoleplay('${scenario.id}')">
                        <div class="scenario-level">${scenario.level}</div>
                        <h3>${scenario.title}</h3>
                        <p>${scenario.description}</p>
                    </div>
                `).join('')}
            </div>
        `;
        
    } catch (error) {
        toast.error('Failed to load scenarios');
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🎭</div>
                <h3>Failed to Load</h3>
                <p>Please check your API key settings and try again.</p>
                <a href="settings.html" class="btn btn-primary">Go to Settings</a>
            </div>
        `;
    } finally {
        loading.hide();
    }
}

// Start Roleplay Session
window.startRoleplay = async function(scenarioId) {
    loading.show();
    
    try {
        const result = await api.startRoleplay(scenarioId);
        currentSession = result.session_id;
        conversationHistory = [];
        
        // Add AI's first message
        addMessage(result.ai_message, true);
        
        // Show conversation interface
        showConversationUI(result.scenario, result.max_turns);
        
        if (result.hint) {
            document.getElementById('hint-text').textContent = result.hint;
        }
        
    } catch (error) {
        toast.error('Failed to start roleplay. Check your API key settings.');
    } finally {
        loading.hide();
    }
};

function showConversationUI(scenario, maxTurns) {
    const container = document.getElementById('roleplay-container') || 
                     document.getElementById('scenarios-container');
    
    container.innerHTML = `
        <div class="speaking-interface">
            <div class="conversation-header">
                <h2>${scenario.title}</h2>
                <p class="scenario-context">${scenario.context}</p>
                <div class="turn-counter">Turn <span id="current-turn">1</span>/${maxTurns}</div>
            </div>
            
            <div class="chat-container" id="chat-container">
                <!-- Messages will be added here -->
            </div>
            
            <div class="hint-box" id="hint-box">
                <strong>💡 Hint:</strong> <span id="hint-text"></span>
            </div>
            
            <div class="input-area">
                <div class="mic-area">
                    <button class="mic-button" id="mic-btn" onclick="toggleRecording()">
                        🎤
                    </button>
                    <p class="recording-status" id="recording-status">Click to speak</p>
                </div>
                
                <div class="text-input-area">
                    <input type="text" id="text-input" placeholder="Or type your response..." 
                           onkeypress="if(event.key==='Enter')sendTextResponse()">
                    <button class="btn btn-primary" onclick="sendTextResponse()">Send</button>
                </div>
            </div>
            
            <div class="feedback-panel" id="feedback-panel" style="display:none;">
                <h4>Feedback</h4>
                <div class="score-display" id="score-display"></div>
                <p id="feedback-text"></p>
            </div>
        </div>
    `;
    
    // Re-render existing messages
    const chatContainer = document.getElementById('chat-container');
    conversationHistory.forEach(msg => {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${msg.isAi ? 'ai' : 'user'}`;
        bubble.textContent = msg.text;
        chatContainer.appendChild(bubble);
    });
}

function addMessage(text, isAi) {
    conversationHistory.push({ text, isAi });
    
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${isAi ? 'ai' : 'user'}`;
        bubble.textContent = text;
        chatContainer.appendChild(bubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// Toggle Recording
window.toggleRecording = async function() {
    const micBtn = document.getElementById('mic-btn');
    const status = document.getElementById('recording-status');
    
    if (!isRecording) {
        // Start recording
        const started = await audioRecorder.start();
        if (started) {
            isRecording = true;
            micBtn.classList.add('recording');
            status.textContent = 'Recording... Click to stop';
            status.classList.add('active');
        }
    } else {
        // Stop and send
        isRecording = false;
        micBtn.classList.remove('recording');
        status.textContent = 'Processing...';
        status.classList.remove('active');
        
        const audioBlob = await audioRecorder.stop();
        if (audioBlob) {
            await sendAudioResponse(audioBlob);
        }
        status.textContent = 'Click to speak';
    }
};

async function sendAudioResponse(audioBlob) {
    loading.show();
    
    try {
        const result = await api.roleplayRespond(currentSession, null, audioBlob);
        handleRoleplayResponse(result);
    } catch (error) {
        toast.error('Failed to process audio');
    } finally {
        loading.hide();
    }
}

window.sendTextResponse = async function() {
    const input = document.getElementById('text-input');
    const text = input.value.trim();
    
    if (!text) {
        toast.warning('Please enter a message');
        return;
    }
    
    input.value = '';
    loading.show();
    
    try {
        const result = await api.roleplayRespond(currentSession, text);
        handleRoleplayResponse(result);
    } catch (error) {
        toast.error('Failed to send message');
    } finally {
        loading.hide();
    }
};

function handleRoleplayResponse(result) {
    // Add user message
    addMessage(result.user_message, false);
    
    // Update turn counter
    const turnEl = document.getElementById('current-turn');
    if (turnEl) turnEl.textContent = result.turn;
    
    // Show feedback
    showFeedback(result.analysis);
    
    // Add AI response if not complete
    if (!result.is_complete && result.ai_message) {
        setTimeout(() => {
            addMessage(result.ai_message, true);
            
            if (result.hint) {
                document.getElementById('hint-text').textContent = result.hint;
            }
        }, 500);
    }
    
    // Check if complete
    if (result.is_complete) {
        showSessionComplete(result);
    }
}

function showFeedback(analysis) {
    const panel = document.getElementById('feedback-panel');
    const scoreDisplay = document.getElementById('score-display');
    const feedbackText = document.getElementById('feedback-text');
    
    if (!panel) return;
    
    panel.style.display = 'block';
    
    scoreDisplay.innerHTML = `
        <div class="score-item">
            <div class="score-circle fluency">${Math.round(analysis.fluency_score)}</div>
            <div class="score-label">Fluency</div>
        </div>
        <div class="score-item">
            <div class="score-circle grammar">${Math.round(analysis.grammar_score)}</div>
            <div class="score-label">Grammar</div>
        </div>
        <div class="score-item">
            <div class="score-circle vocabulary">${Math.round(analysis.vocabulary_score)}</div>
            <div class="score-label">Vocabulary</div>
        </div>
    `;
    
    feedbackText.innerHTML = analysis.feedback || '';
    
    if (analysis.corrections && analysis.corrections.length > 0) {
        feedbackText.innerHTML += `<br><br><strong>Corrections:</strong><br>${analysis.corrections.join('<br>')}`;
    }
}

function showSessionComplete(result) {
    const container = document.getElementById('roleplay-container') || 
                     document.getElementById('scenarios-container');
    
    const avgScore = Math.round(
        (result.analysis.fluency_score + result.analysis.grammar_score + result.analysis.vocabulary_score) / 3
    );
    
    container.innerHTML = `
        <div class="result-screen">
            <div class="result-icon">🎉</div>
            <h2>Session Complete!</h2>
            <div class="result-score">${avgScore}</div>
            <p class="result-message">Average Score</p>
            
            <div class="score-display">
                <div class="score-item">
                    <div class="score-circle fluency">${Math.round(result.analysis.fluency_score)}</div>
                    <div class="score-label">Fluency</div>
                </div>
                <div class="score-item">
                    <div class="score-circle grammar">${Math.round(result.analysis.grammar_score)}</div>
                    <div class="score-label">Grammar</div>
                </div>
                <div class="score-item">
                    <div class="score-circle vocabulary">${Math.round(result.analysis.vocabulary_score)}</div>
                    <div class="score-label">Vocabulary</div>
                </div>
            </div>
            
            <div class="result-stats">
                <div class="result-stat">
                    <div class="result-stat-value">+${result.xp_earned || 40}</div>
                    <div class="result-stat-label">XP Earned</div>
                </div>
            </div>
            
            <div style="margin-top: 2rem; display: flex; gap: 1rem; justify-content: center;">
                <a href="dashboard.html" class="btn btn-secondary">Back to Dashboard</a>
                <button onclick="location.reload()" class="btn btn-primary">Try Again</button>
            </div>
        </div>
    `;
}

// Free Talk Mode
let freeTalkSession = null;

window.startFreeTalk = async function() {
    loading.show();
    
    try {
        const result = await api.startFreeTalk();
        freeTalkSession = result.session_id;
        conversationHistory = [];
        
        showFreeTalkUI();
        
        toast.success('Free talk started! Say anything to begin.');
        
    } catch (error) {
        toast.error('Failed to start free talk. Check your API key settings.');
    } finally {
        loading.hide();
    }
};

function showFreeTalkUI() {
    const container = document.getElementById('freetalk-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="speaking-interface">
            <div class="conversation-header">
                <h2>Free Talk</h2>
                <p>Practice open conversation with AI</p>
                <div class="session-stats">
                    <span id="message-count">0 messages</span> • 
                    <span id="session-avg">Avg: --</span>
                </div>
            </div>
            
            <div class="chat-container" id="chat-container">
                <div class="chat-bubble ai">
                    Hi! I'm here to practice English with you. What would you like to talk about today?
                </div>
            </div>
            
            <div class="input-area">
                <div class="mic-area">
                    <button class="mic-button" id="mic-btn" onclick="toggleFreeTalkRecording()">
                        🎤
                    </button>
                    <p class="recording-status" id="recording-status">Click to speak</p>
                </div>
                
                <div class="text-input-area">
                    <input type="text" id="text-input" placeholder="Or type your message..." 
                           onkeypress="if(event.key==='Enter')sendFreeTalkText()">
                    <button class="btn btn-primary" onclick="sendFreeTalkText()">Send</button>
                </div>
            </div>
            
            <div class="feedback-panel" id="feedback-panel" style="display:none;">
                <div class="score-display" id="score-display"></div>
            </div>
            
            <button class="btn btn-secondary" onclick="endFreeTalk()" style="margin-top: 1rem;">
                End Session
            </button>
        </div>
    `;
}

window.toggleFreeTalkRecording = async function() {
    const micBtn = document.getElementById('mic-btn');
    const status = document.getElementById('recording-status');
    
    if (!isRecording) {
        const started = await audioRecorder.start();
        if (started) {
            isRecording = true;
            micBtn.classList.add('recording');
            status.textContent = 'Recording... Click to stop';
            status.classList.add('active');
        }
    } else {
        isRecording = false;
        micBtn.classList.remove('recording');
        status.textContent = 'Processing...';
        status.classList.remove('active');
        
        const audioBlob = await audioRecorder.stop();
        if (audioBlob) {
            await sendFreeTalkAudio(audioBlob);
        }
        status.textContent = 'Click to speak';
    }
};

async function sendFreeTalkAudio(audioBlob) {
    loading.show();
    try {
        const result = await api.freeTalkRespond(freeTalkSession, null, audioBlob);
        handleFreeTalkResponse(result);
    } catch (error) {
        toast.error('Failed to process audio');
    } finally {
        loading.hide();
    }
}

window.sendFreeTalkText = async function() {
    const input = document.getElementById('text-input');
    const text = input.value.trim();
    
    if (!text) return;
    
    input.value = '';
    loading.show();
    
    try {
        const result = await api.freeTalkRespond(freeTalkSession, text);
        handleFreeTalkResponse(result);
    } catch (error) {
        toast.error('Failed to send message');
    } finally {
        loading.hide();
    }
};

function handleFreeTalkResponse(result) {
    addMessage(result.user_message, false);
    
    setTimeout(() => {
        addMessage(result.ai_message, true);
    }, 500);
    
    // Update stats
    document.getElementById('message-count').textContent = `${result.message_count} messages`;
    
    const avg = Math.round(
        (result.session_averages.fluency + result.session_averages.grammar + result.session_averages.vocabulary) / 3
    );
    document.getElementById('session-avg').textContent = `Avg: ${avg}`;
    
    // Show current feedback
    showFeedback(result.current_analysis);
}

window.endFreeTalk = async function() {
    if (!freeTalkSession) return;
    
    loading.show();
    
    try {
        const result = await api.endFreeTalk(freeTalkSession);
        
        const container = document.getElementById('freetalk-container');
        container.innerHTML = `
            <div class="result-screen">
                <div class="result-icon">🎉</div>
                <h2>Great Session!</h2>
                <p class="result-message">${result.summary}</p>
                
                <div class="score-display">
                    <div class="score-item">
                        <div class="score-circle fluency">${Math.round(result.final_scores.fluency)}</div>
                        <div class="score-label">Fluency</div>
                    </div>
                    <div class="score-item">
                        <div class="score-circle grammar">${Math.round(result.final_scores.grammar)}</div>
                        <div class="score-label">Grammar</div>
                    </div>
                    <div class="score-item">
                        <div class="score-circle vocabulary">${Math.round(result.final_scores.vocabulary)}</div>
                        <div class="score-label">Vocabulary</div>
                    </div>
                </div>
                
                <div class="result-stats">
                    <div class="result-stat">
                        <div class="result-stat-value">+${result.xp_earned}</div>
                        <div class="result-stat-label">XP Earned</div>
                    </div>
                </div>
                
                <div style="margin-top: 2rem;">
                    <a href="dashboard.html" class="btn btn-primary">Back to Dashboard</a>
                </div>
            </div>
        `;
        
    } catch (error) {
        toast.error('Failed to end session');
    } finally {
        loading.hide();
    }
};

// Export for HTML
window.loadScenarios = loadScenarios;
