// LLM Arena Enhanced JavaScript

// State
let providers = {};
let configuredKeys = {};
let competitionHistory = [];
let templates = [];
let criteria = [];
let currentCompetition = null;
let currentView = 'list';
let selectedTemplate = null;

// Provider icons
const providerIcons = {
    openai: 'O',
    anthropic: 'A',
    google: 'G',
    mistral: 'M',
    cohere: 'C',
    groq: 'R',
    deepseek: 'D',
    xai: 'X',
    perplexity: 'P',
    together: 'T',
    ollama: '🦙'
};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadProviders();  // Must come before loadKeys (form rendering depends on providers)
    await loadKeys();
    await Promise.all([
        loadHistory(),
        loadTemplates(),
        loadCriteria()
    ]);
    setupEventListeners();
    updateLeaderboard();
    loadStats();
});

// Data loading functions
async function loadProviders() {
    try {
        const response = await fetch('/api/providers');
        providers = await response.json();
        renderProviders();
    } catch (error) {
        console.error('Failed to load providers:', error);
    }
}

async function loadKeys() {
    try {
        const response = await fetch('/api/keys');
        configuredKeys = await response.json();
        renderApiKeyForm();
        updateProviderStatus();
    } catch (error) {
        console.error('Failed to load keys:', error);
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        competitionHistory = await response.json();
        renderHistory();
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

async function loadTemplates() {
    try {
        const response = await fetch('/api/templates');
        templates = await response.json();
        renderTemplates();
    } catch (error) {
        console.error('Failed to load templates:', error);
    }
}

async function loadCriteria() {
    try {
        const response = await fetch('/api/criteria');
        criteria = await response.json();
    } catch (error) {
        console.error('Failed to load criteria:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        renderStats(stats);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Render functions
function renderProviders() {
    const grid = document.getElementById('providers-grid');
    grid.innerHTML = '';
    
    for (const [key, provider] of Object.entries(providers)) {
        const card = document.createElement('div');
        card.className = `provider-card ${key}`;
        card.dataset.provider = key;
        
        card.innerHTML = `
            <div class="provider-header">
                <div class="provider-icon">${providerIcons[key] || key[0].toUpperCase()}</div>
                <span class="provider-name">${provider.name}</span>
                <div class="provider-check">
                    <i class="fas fa-check"></i>
                </div>
            </div>
            <select class="model-select" data-provider="${key}">
                ${provider.models.map(model => 
                    `<option value="${model}" ${model === provider.default_model ? 'selected' : ''}>${model}</option>`
                ).join('')}
            </select>
            <div class="api-status not-configured" data-provider="${key}">
                <i class="fas fa-exclamation-circle"></i>
                <span>API key not configured</span>
            </div>
        `;
        
        card.addEventListener('click', (e) => {
            if (!e.target.classList.contains('model-select')) {
                card.classList.toggle('selected');
            }
        });
        
        grid.appendChild(card);
    }
    
    updateProviderStatus();
}

function updateProviderStatus() {
    for (const [key, provider] of Object.entries(providers)) {
        const status = document.querySelector(`.api-status[data-provider="${key}"]`);
        if (status) {
            if (key === 'ollama') {
                status.className = 'api-status configured free';
                status.innerHTML = `<i class="fas fa-leaf"></i><span>Free - Local (no API key)</span>`;
            } else if (configuredKeys[key]) {
                status.className = 'api-status configured';
                status.innerHTML = `<i class="fas fa-check-circle"></i><span>API key configured</span>`;
            } else {
                status.className = 'api-status not-configured';
                status.innerHTML = `<i class="fas fa-exclamation-circle"></i><span>API key not configured</span>`;
            }
        }
    }
}

function renderApiKeyForm() {
    const form = document.getElementById('api-keys-form');
    form.innerHTML = '';
    
    if (!providers || Object.keys(providers).length === 0) {
        console.warn('Providers not loaded yet - skipping API key form render');
        return;
    }
    
    for (const [key, provider] of Object.entries(providers)) {
        if (key === 'ollama') {
            // Skip API key input for free local Ollama
            continue;
        }
        
        const group = document.createElement('div');
        group.className = 'api-key-group';
        
        const hasKey = configuredKeys[key];
        const currentDisplay = hasKey ? `Current: ${hasKey}` : 'No key saved';
        
        group.innerHTML = `
            <div class="api-key-header">
                <div class="provider-icon" style="width: 30px; height: 30px; font-size: 0.9rem;">${providerIcons[key] || key[0].toUpperCase()}</div>
                <label for="key-${key}">${provider.name}</label>
                <span style="margin-left: auto; font-size: 0.75rem; color: var(--text-muted);">${currentDisplay}</span>
            </div>
            <input type="password" id="key-${key}" class="api-key-input" 
                   placeholder="${hasKey ? 'Enter new key to update (leave blank to keep current)' : 'Enter your API key'}"
                   data-provider="${key}">
        `;
        
        form.appendChild(group);
    }
    
    // Add note about free provider
    const note = document.createElement('div');
    note.className = 'free-provider-note';
    note.innerHTML = `
        <div style="background: var(--darker); padding: 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid var(--secondary);">
            <strong>🦙 Ollama (Free Local LLM)</strong><br>
            No API key required. Install Ollama from <a href="https://ollama.com" target="_blank">ollama.com</a>, run <code>ollama serve</code> and <code>ollama pull llama3.2</code>.
        </div>
    `;
    form.appendChild(note);
}

function renderTemplates() {
    const grid = document.getElementById('templates-grid');
    const modalGrid = document.getElementById('modal-templates-grid');
    
    const templateHTML = templates.map(t => `
        <div class="template-item" data-template-id="${t.id}">
            <div class="template-category">${t.category}</div>
            <div class="template-name">${t.name}</div>
            <div class="template-desc">${t.description || ''}</div>
        </div>
    `).join('');
    
    grid.innerHTML = templateHTML;
    modalGrid.innerHTML = templateHTML;
    
    // Add click handlers
    document.querySelectorAll('.template-item').forEach(item => {
        item.addEventListener('click', () => selectTemplate(item.dataset.templateId));
    });
}

function selectTemplate(templateId) {
    selectedTemplate = templates.find(t => t.id === templateId);
    if (!selectedTemplate) return;
    
    // Highlight selected
    document.querySelectorAll('.template-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.templateId === templateId);
    });
    
    // Show variables section if needed
    const varsSection = document.getElementById('template-variables-section');
    const varsInputs = document.getElementById('template-variables-inputs');
    
    if (selectedTemplate.variables && selectedTemplate.variables.length > 0) {
        varsSection.style.display = 'block';
        varsInputs.innerHTML = selectedTemplate.variables.map(v => `
            <label for="var-${v}">${v}</label>
            <input type="text" id="var-${v}" data-var="${v}" placeholder="Enter ${v}">
        `).join('');
    } else {
        varsSection.style.display = 'none';
        applyTemplateToPrompt();
    }
}

function applyTemplateToPrompt() {
    if (!selectedTemplate) return;
    
    let prompt = selectedTemplate.prompt;
    
    // Replace variables
    if (selectedTemplate.variables) {
        selectedTemplate.variables.forEach(v => {
            const input = document.getElementById(`var-${v}`);
            const value = input ? input.value : '';
            prompt = prompt.replace(new RegExp(`\\{${v}\\}`, 'g'), value);
        });
    }
    
    document.getElementById('prompt-input').value = prompt;
    closeTemplateModal();
    
    // Switch to arena tab
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector('.tab-btn[data-tab="arena"]').classList.add('active');
    document.getElementById('arena').classList.add('active');
}

function closeTemplateModal() {
    document.getElementById('template-modal').classList.remove('show');
    selectedTemplate = null;
    document.querySelectorAll('.template-item').forEach(item => item.classList.remove('selected'));
    document.getElementById('template-variables-section').style.display = 'none';
}

function renderHistory() {
    const list = document.getElementById('history-list');
    
    if (competitionHistory.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-history"></i>
                <p>No competitions yet. Start your first competition in the Arena!</p>
            </div>
        `;
        return;
    }
    
    list.innerHTML = competitionHistory.map((item) => {
        const winners = (item.results || [])
            .filter(r => r.success)
            .sort((a, b) => a.elapsed - b.elapsed)
            .slice(0, 3);
        
        const winnerBadges = winners.map((w, i) => {
            const rankClass = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : 'rank-3';
            return `<span class="winner-badge ${rankClass}">${w.provider_name || 'Unknown'} (${(w.elapsed || 0).toFixed(2)}s)</span>`;
        }).join('');
        
        return `
            <div class="history-item">
                <div class="history-header">
                    <span class="history-timestamp">${item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Unknown date'}</span>
                </div>
                <div class="history-prompt">${escapeHtml((item.prompt || '').substring(0, 200))}${(item.prompt || '').length > 200 ? '...' : ''}</div>
                <div class="history-winners">${winnerBadges || 'No successful responses'}</div>
            </div>
        `;
    }).join('');
}

function renderStats(stats) {
    const grid = document.getElementById('stats-grid');
    grid.innerHTML = `
        <div class="stat-card">
            <div class="value">${stats.total_competitions || 0}</div>
            <div class="label">Competitions</div>
        </div>
        <div class="stat-card">
            <div class="value">${stats.total_results || 0}</div>
            <div class="label">Total Results</div>
        </div>
        <div class="stat-card">
            <div class="value">${stats.successful_results || 0}</div>
            <div class="label">Successful</div>
        </div>
        <div class="stat-card">
            <div class="value">${stats.total_ratings || 0}</div>
            <div class="label">Ratings</div>
        </div>
        <div class="stat-card">
            <div class="value">${stats.providers_configured || 0}</div>
            <div class="label">APIs Configured</div>
        </div>
        <div class="stat-card">
            <div class="value">${stats.templates_available || 0}</div>
            <div class="label">Templates</div>
        </div>
    `;
    
    const topPerformers = document.getElementById('top-performers');
    topPerformers.innerHTML = `
        <div>
            <h4><i class="fas fa-trophy"></i> Top by Wins</h4>
            <div style="margin-top: 15px;">
                ${(stats.top_by_wins || []).map(w => `
                    <div style="display: flex; justify-content: space-between; padding: 10px; background: var(--darker); border-radius: 8px; margin-bottom: 10px;">
                        <span>${w.provider_name} - ${w.model}</span>
                        <span style="color: var(--gold);">${w.wins} wins</span>
                    </div>
                `).join('') || '<p style="color: var(--text-muted);">No data yet</p>'}
            </div>
        </div>
        <div>
            <h4><i class="fas fa-bolt"></i> Top by Speed</h4>
            <div style="margin-top: 15px;">
                ${(stats.top_by_speed || []).map(w => `
                    <div style="display: flex; justify-content: space-between; padding: 10px; background: var(--darker); border-radius: 8px; margin-bottom: 10px;">
                        <span>${w.provider_name} - ${w.model}</span>
                        <span style="color: var(--secondary);">${(w.best_time || 0).toFixed(2)}s</span>
                    </div>
                `).join('') || '<p style="color: var(--text-muted);">No data yet</p>'}
            </div>
        </div>
    `;
}

function updateLeaderboard() {
    fetch('/api/leaderboard')
        .then(res => res.json())
        .then(data => {
            const table = document.getElementById('leaderboard-table');
            
            if (!data || data.length === 0) {
                table.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-chart-bar"></i>
                        <p>No competition data yet. Complete some competitions to see the leaderboard!</p>
                    </div>
                `;
                return;
            }
            
            table.innerHTML = `
                <div class="leaderboard-row header">
                    <div>Rank</div>
                    <div>Provider</div>
                    <div>Wins</div>
                    <div>Avg Time</div>
                    <div>Success</div>
                    <div>Score</div>
                </div>
                ${data.map((item, i) => `
                    <div class="leaderboard-row">
                        <div class="leaderboard-rank">${i + 1}</div>
                        <div class="leaderboard-provider">
                            <div class="provider-icon" style="width: 30px; height: 30px; font-size: 0.9rem;">${providerIcons[item.provider] || item.provider[0].toUpperCase()}</div>
                            <span>${item.provider_name}<br><small style="color: var(--text-muted);">${item.model}</small></span>
                        </div>
                        <div class="leaderboard-stat">${item.wins || 0}</div>
                        <div class="leaderboard-stat">${(item.avg_time || 0).toFixed(2)}s</div>
                        <div class="leaderboard-stat">${item.total_competitions > 0 ? Math.round((item.successful || 0) / item.total_competitions * 100) : 0}%</div>
                        <div class="leaderboard-stat">${item.weighted_score || '-'}</div>
                    </div>
                `).join('')}
            `;
        })
        .catch(err => console.error('Failed to load leaderboard:', err));
}

// Setup event listeners
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
            
            if (btn.dataset.tab === 'stats') loadStats();
            if (btn.dataset.tab === 'leaderboard') updateLeaderboard();
        });
    });
    
    // Quick prompts
    document.querySelectorAll('.quick-btn[data-prompt]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('prompt-input').value = btn.dataset.prompt;
        });
    });
    
    // Template button
    document.getElementById('template-btn').addEventListener('click', () => {
        document.getElementById('template-modal').classList.add('show');
    });
    
    // Close modals
    document.getElementById('close-template-modal').addEventListener('click', closeTemplateModal);
    document.getElementById('close-rating-modal').addEventListener('click', () => {
        document.getElementById('rating-modal').classList.remove('show');
    });
    
    // Apply template
    document.getElementById('apply-template').addEventListener('click', applyTemplateToPrompt);
    
    // Select all / Deselect all
    document.getElementById('select-all').addEventListener('click', () => {
        document.querySelectorAll('.provider-card').forEach(card => card.classList.add('selected'));
    });
    
    document.getElementById('deselect-all').addEventListener('click', () => {
        document.querySelectorAll('.provider-card').forEach(card => card.classList.remove('selected'));
    });
    
    // Save API keys
    document.getElementById('save-keys').addEventListener('click', async () => {
        const keys = {};
        document.querySelectorAll('.api-key-input').forEach(input => {
            if (input.value.trim()) {
                keys[input.dataset.provider] = input.value.trim();
            }
        });
        
        if (Object.keys(keys).length === 0) {
            showToast('Please enter at least one API key', 'warning');
            return;
        }
        
        try {
            const response = await fetch('/api/keys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(keys)
            });
            
            if (response.ok) {
                showToast('API keys saved successfully!', 'success');
                await loadKeys();
            } else {
                showToast('Failed to save API keys', 'error');
            }
        } catch (error) {
            console.error('Error saving keys:', error);
            showToast('Error saving API keys', 'error');
        }
    });
    
    // Compete button
    document.getElementById('compete-btn').addEventListener('click', runCompetition);
    
    // Clear history
    document.getElementById('clear-history').addEventListener('click', async () => {
        if (confirm('Are you sure you want to clear all history?')) {
            try {
                await fetch('/api/history/clear', { method: 'POST' });
                competitionHistory = [];
                renderHistory();
                updateLeaderboard();
                loadStats();
                showToast('History cleared', 'success');
            } catch (error) {
                console.error('Error clearing history:', error);
            }
        }
    });
    
    // View toggle
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentView = btn.dataset.view;
            if (currentCompetition) {
                displayResults(currentCompetition);
            }
        });
    });
    
    // Export buttons
    document.getElementById('export-csv').addEventListener('click', () => exportResults('csv'));
    document.getElementById('export-json').addEventListener('click', () => exportResults('json'));
    document.getElementById('save-ratings-btn').addEventListener('click', saveAllRatings);
}

// Competition functions
async function runCompetition() {
    const prompt = document.getElementById('prompt-input').value.trim();
    
    if (!prompt) {
        showToast('Please enter a problem or question', 'warning');
        return;
    }
    
    const selectedCards = document.querySelectorAll('.provider-card.selected');
    
    if (selectedCards.length === 0) {
        showToast('Please select at least one LLM to compete', 'warning');
        return;
    }
    
    const selectedProviders = Array.from(selectedCards).map(card => {
        const provider = card.dataset.provider;
        const model = card.querySelector('.model-select').value;
        return { provider, model };
    });
    
    // Check for API keys (skip for free providers like Ollama)
    const missingKeys = selectedProviders.filter(p => !configuredKeys[p.provider] && p.provider !== 'ollama');
    if (missingKeys.length > 0) {
        const names = missingKeys.map(p => providers[p.provider]?.name || p.provider).join(', ');
        showToast(`Please configure API keys for: ${names}`, 'warning');
        return;
    }
    
    const blindMode = document.getElementById('blind-mode-toggle').checked;
    
    // Show loading
    document.getElementById('loading-overlay').style.display = 'flex';
    document.getElementById('results-section').style.display = 'none';
    
    try {
        const response = await fetch('/api/compete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                prompt, 
                providers: selectedProviders,
                blind_mode: blindMode
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentCompetition = data;
            displayResults(data);
            await loadHistory();
            updateLeaderboard();
            loadStats();
        } else {
            showToast('Error: ' + (data.error || 'Competition failed'), 'error');
        }
    } catch (error) {
        console.error('Competition error:', error);
        showToast('Error running competition', 'error');
    } finally {
        document.getElementById('loading-overlay').style.display = 'none';
    }
}

function displayResults(data) {
    const section = document.getElementById('results-section');
    const container = document.getElementById('results-container');
    
    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth' });
    
    const isBlind = data.blind_mode;
    
    // Add blind mode indicator and reveal button
    let headerExtra = '';
    if (isBlind) {
        headerExtra = `<span class="blind-badge"><i class="fas fa-eye-slash"></i> Blind Mode</span>
            <button class="reveal-btn" onclick="revealProviders('${data.competition_id}')">
                <i class="fas fa-eye"></i> Reveal Models
            </button>`;
    }
    
    if (currentView === 'side-by-side') {
        container.className = 'results-container side-by-side';
    } else {
        container.className = 'results-container';
    }
    
    container.innerHTML = data.results.map((result, index) => {
        const isWinner = result.success && result.rank === 1;
        const isError = !result.success;
        
        let rankClass = 'rank-other';
        if (result.rank === 1) rankClass = 'rank-1';
        else if (result.rank === 2) rankClass = 'rank-2';
        else if (result.rank === 3) rankClass = 'rank-3';
        
        const displayName = isBlind ? result.provider_name_hidden : result.provider_name;
        const displayModel = isBlind ? '' : result.model;
        
        return `
            <div class="result-card ${isWinner ? 'winner' : ''} ${isError ? 'error' : ''}" data-result-id="${result.id}">
                <div class="result-header">
                    <div class="result-info">
                        <div class="result-rank ${rankClass}">${result.rank || '-'}</div>
                        <div>
                            <div class="result-provider">${displayName || 'Unknown'} ${headerExtra}</div>
                            ${displayModel ? `<div class="result-model">${displayModel}</div>` : ''}
                        </div>
                    </div>
                    <div class="result-stats">
                        <div class="stat">
                            <div class="stat-value">${result.elapsed ? result.elapsed.toFixed(2) : '-'}</div>
                            <div class="stat-label">Seconds</div>
                        </div>
                        ${result.tokens ? `
                        <div class="stat">
                            <div class="stat-value">${result.tokens.total_tokens || result.tokens.output || '-'}</div>
                            <div class="stat-label">Tokens</div>
                        </div>
                        ` : ''}
                    </div>
                </div>
                <div class="result-response">
                    ${result.success ? renderMarkdown(result.response) : `<div class="result-error"><i class="fas fa-exclamation-triangle"></i> ${escapeHtml(result.error || 'Unknown error')}</div>`}
                </div>
                ${result.success ? renderRatingSection(result, data.competition_id) : ''}
            </div>
        `;
    }).join('');
    
    // Setup rating interactions
    setupRatingListeners();
}

function renderRatingSection(result, competitionId) {
    return `
        <div class="rating-section">
            <h4><i class="fas fa-star"></i> Rate this response</h4>
            <div class="rating-criteria">
                ${criteria.map(c => `
                    <div class="rating-item">
                        <label>${c.name}</label>
                        <div class="rating-stars" data-criterion="${c.id}" data-result-id="${result.id}" data-competition-id="${competitionId}">
                            ${[1,2,3,4,5].map(n => `<i class="fas fa-star" data-score="${n}"></i>`).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function setupRatingListeners() {
    document.querySelectorAll('.rating-stars i').forEach(star => {
        star.addEventListener('click', function() {
            const starsDiv = this.closest('.rating-stars');
            const score = parseInt(this.dataset.score);
            const criterion = starsDiv.dataset.criterion;
            const resultId = starsDiv.dataset.resultId;
            const competitionId = starsDiv.dataset.competitionId;
            
            // Update visual
            starsDiv.querySelectorAll('i').forEach((s, i) => {
                s.classList.toggle('active', i < score);
            });
            
            // Store rating
            starsDiv.dataset.currentScore = score;
        });
    });
}

async function saveAllRatings() {
    const ratings = [];
    
    document.querySelectorAll('.rating-stars').forEach(starsDiv => {
        const score = starsDiv.dataset.currentScore;
        if (score) {
            ratings.push({
                result_id: starsDiv.dataset.resultId,
                competition_id: starsDiv.dataset.competitionId,
                criterion: starsDiv.dataset.criterion,
                score: parseInt(score)
            });
        }
    });
    
    if (ratings.length === 0) {
        showToast('Please rate at least one response', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/ratings/bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ratings })
        });
        
        if (response.ok) {
            showToast(`Saved ${ratings.length} ratings!`, 'success');
            updateLeaderboard();
        } else {
            showToast('Failed to save ratings', 'error');
        }
    } catch (error) {
        console.error('Error saving ratings:', error);
        showToast('Error saving ratings', 'error');
    }
}

async function revealProviders(competitionId) {
    try {
        const response = await fetch(`/api/competitions/${competitionId}/reveal`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const data = await response.json();
            // Update the display with revealed names
            if (currentCompetition && currentCompetition.competition_id === competitionId) {
                currentCompetition.blind_mode = false;
                currentCompetition.results.forEach(result => {
                    const revealed = data.results.find(r => r.id === result.id);
                    if (revealed) {
                        result.provider_name = revealed.provider_name;
                        result.model = revealed.model;
                        result.provider = revealed.provider;
                    }
                });
                displayResults(currentCompetition);
            }
            showToast('Models revealed!', 'success');
        }
    } catch (error) {
        console.error('Error revealing providers:', error);
        showToast('Error revealing models', 'error');
    }
}

async function exportResults(format) {
    if (!currentCompetition) {
        showToast('No competition to export', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/export/${format}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ competition_ids: [currentCompetition.competition_id] })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `llm_arena_results.${format}`;
            a.click();
            window.URL.revokeObjectURL(url);
            showToast(`Exported as ${format.toUpperCase()}`, 'success');
        } else {
            showToast('Export failed', 'error');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Export failed', 'error');
    }
}

// Utility functions
function renderMarkdown(text) {
    if (typeof marked !== 'undefined') {
        return marked.parse(text || '');
    }
    return escapeHtml(text || '').replace(/\n/g, '<br>');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? 'var(--secondary)' : type === 'error' ? 'var(--danger)' : type === 'warning' ? 'var(--accent)' : 'var(--primary)'};
        color: white;
        border-radius: 8px;
        z-index: 3000;
        animation: slideIn 0.3s ease;
    `;
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : type === 'warning' ? 'exclamation' : 'info'}-circle"></i> ${message}`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add CSS animations for toast
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Make revealProviders globally accessible
window.revealProviders = revealProviders;

