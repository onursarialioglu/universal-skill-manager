// Universal Skill Manager (USM) Dashboard Logic
let currentLang = 'en';
let cachedSkills = [];
let cachedClients = [];
let cachedSettings = {};
let activeAddTab = 'mcp';

const CODE_REVIEW_TEMPLATE = `# Senior Code Review & Security Guidelines

## Review Principles
1. Security: Validate all inputs, prevent SQL/command injection, verify authorization tokens.
2. Error Handling: Never swallow exceptions silently; use structured errors and logs.
3. Resource Management: Prevent connection leaks, unclosed files, or lingering sockets.
4. Test Coverage: Require unit tests for critical business logic and boundary conditions.
5. Code Style: Follow idioms, enforce consistent formatting, and avoid dead code.`;

const ARCHITECTURE_TEMPLATE = `# Architecture Decision Record (ADR)

## Title
[Short and descriptive decision name]

## Status
[Proposed | Accepted | Rejected | Superseded]

## Context
Technical, architectural, or business drivers necessitating this decision.

## Decision
Selected solution, architectural pattern, and implementation strategy.

## Consequences
Positive impacts, architectural trade-offs, and operational risks.`;

const API_DESIGN_TEMPLATE = `# REST API & GraphQL Design Standards

## Principles
1. Resource Naming: Plural nouns (e.g. /v1/users, /v1/projects).
2. HTTP Methods: GET for retrieval, POST for creation, PUT/PATCH for updates, DELETE for removal.
3. Status Codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 404 Not Found, 500 Internal Error.
4. Error Envelope: Standard JSON error with 'error', 'code', and 'message' fields.
5. Idempotency: Use Idempotency-Key headers on critical mutating endpoints.`;

const I18N = {
  en: {
    app_subtitle: "Central MCP & Agent Skill Hub",
    btn_add_skill: "+ Add Skill / MCP",
    btn_settings: "Settings",
    btn_undo: "Undo",
    btn_sync: "Sync All",
    sec_clients_title: "Connected AI Clients",
    sec_skills_title: "Registered MCP Servers & Skills",
    btn_new_skill: "Add New Skill",
    search_placeholder: "Search skills or tools...",
    sec_history_title: "Transaction History & Automatic Backups",
    th_id: "ID",
    th_name: "Name",
    th_transport: "Protocol",
    th_cmd: "Command / Content",
    th_targets: "Targets",
    th_health: "Health",
    th_action: "Actions",
    th_tx_id: "Tx ID",
    th_timestamp: "Timestamp",
    th_status: "Status",
    th_steps: "Details",
    modal_add_title: "Register Skill or MCP Server",
    tab_mcp: "MCP Server (Executable Tool)",
    tab_prompt: "Agent Skill (Prompt / Rule)",
    lbl_template: "Quick Template",
    opt_custom: "-- Custom Server (Manual) --",
    lbl_prompt_template: "Predefined Skill Template",
    opt_prompt_custom: "-- Custom Rule / Instructions --",
    lbl_id: "Skill / Server ID",
    lbl_name: "Display Name",
    lbl_desc: "Description",
    lbl_scope: "Deployment Scope",
    lbl_prompt_content: "Skill Rules / Instructions (Markdown)",
    lbl_transport: "Communication Protocol",
    lbl_cmd: "Execution Command",
    lbl_args: "Command Arguments (space separated)",
    lbl_env: "Environment Variables (KEY=VALUE per line)",
    lbl_targets: "Target AI Clients",
    target_all: "All Connected Clients",
    btn_cancel: "Cancel",
    btn_save_sync: "Save & Sync",
    modal_settings_title: "USM System Settings",
    set_general_title: "General Preferences",
    lbl_set_lang: "Interface Language",
    lbl_set_approval: "Sync Approval Mode",
    opt_always_ask: "Always Ask for Approval (always_ask)",
    opt_ask_on_risk: "Ask Only on Risk / Drift (ask_on_risk)",
    opt_auto: "Fully Autonomous (auto)",
    set_backup_title: "Backup & Rollback",
    lbl_max_backups: "Max Backups per Client",
    lbl_retention_days: "Retention Period (Days)",
    set_clients_title: "AI Clients & Configuration Paths",
    set_clients_hint: "USM automatically detects installed client configurations. You can optionally override active configuration paths below:",
    btn_save_settings: "Save Settings",
    toast_added: "Skill successfully registered and synchronized across target clients!",
    toast_deleted: "Skill removed and client configurations updated.",
    toast_synced: "Configurations synchronized across all clients successfully!",
    toast_undo: "Configuration rolled back to previous state from backup.",
    toast_saved: "System settings saved successfully!",
    toast_error: "An error occurred during operation:",
    no_skills: "No skills or MCP servers registered yet. Click '+ Add Skill / MCP' above to get started.",
    no_history: "No audit transactions recorded yet.",
    confirm_delete: "Are you sure you want to remove this skill/server from USM and all clients?",
    confirm_undo: "Are you sure you want to roll back the last transaction to its previous backup?"
  }
};

// API Helpers
async function apiGet(endpoint) {
  const res = await fetch(endpoint);
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

async function apiPost(endpoint, body) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

async function apiPut(endpoint, body) {
  const res = await fetch(endpoint, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

async function apiDelete(endpoint) {
  const res = await fetch(endpoint, { method: 'DELETE' });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

// Toast Notifications
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const icon = type === 'success' ? '✔' : (type === 'error' ? '✖' : 'ℹ');
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function t(key) {
  return (I18N.en && I18N.en[key]) || key;
}

// Load Clients
async function loadClients() {
  try {
    cachedClients = await apiGet('/api/status');
    renderClients();
    updateTargetCheckboxes();
  } catch (err) {
    console.error('Failed to load clients', err);
  }
}

function renderClients() {
  const container = document.getElementById('clients-container');
  container.innerHTML = '';

  let readyCount = 0;
  cachedClients.forEach(c => {
    if (c.status === 'ready') readyCount++;

    const card = document.createElement('div');
    card.className = 'client-card';

    let badgeClass = 'badge-not-installed';
    let label = c.status;
    if (c.status === 'ready') {
      badgeClass = 'badge-ready';
      label = 'Ready';
    } else if (c.status === 'installed_no_config') {
      badgeClass = 'badge-warning';
      label = 'No Config';
    } else if (c.status === 'ambiguous') {
      badgeClass = 'badge-warning';
      label = 'Ambiguous';
    } else {
      label = 'Not Installed';
    }

    card.innerHTML = `
      <div>
        <div class="client-card-header">
          <span class="client-card-name">${c.client_id}</span>
          <span class="status-badge ${badgeClass}">${label}</span>
        </div>
        <div class="client-path" title="${c.path || ''}">${c.path || 'Not detected'}</div>
      </div>
    `;
    container.appendChild(card);
  });

  const summary = document.getElementById('client-summary');
  summary.textContent = `${readyCount} of ${cachedClients.length} Ready`;
}

// Target Checkboxes in Add Modal
function updateTargetCheckboxes() {
  const list = document.getElementById('targets-clients-list');
  list.innerHTML = '';
  cachedClients.forEach(c => {
    const item = document.createElement('label');
    item.className = 'target-checkbox-item';
    item.innerHTML = `
      <input type="checkbox" class="target-client-check" value="${c.client_id}" checked>
      <span>${c.client_id}</span>
    `;
    list.appendChild(item);
  });
}

// Load Skills
async function loadSkills() {
  try {
    cachedSkills = await apiGet('/api/skills');
    renderSkills();
  } catch (err) {
    console.error('Failed to load skills', err);
  }
}

function renderSkills() {
  const tbody = document.getElementById('skills-tbody');
  const search = document.getElementById('skills-search').value.toLowerCase().trim();
  tbody.innerHTML = '';

  const filtered = cachedSkills.filter(sk => {
    if (!search) return true;
    return sk.id.toLowerCase().includes(search) || 
           (sk.name && sk.name.toLowerCase().includes(search)) ||
           (sk.command && sk.command.toLowerCase().includes(search)) ||
           (sk.content && sk.content.toLowerCase().includes(search));
  });

  document.getElementById('skills-summary').textContent = `${cachedSkills.length} Skills`;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-secondary); padding: 2.5rem;">${t('no_skills')}</td></tr>`;
    return;
  }

  filtered.forEach(sk => {
    const tr = document.createElement('tr');
    
    let typeBadge = '';
    let cmdOrContent = '';

    if (sk.kind === 'agent_skill') {
      typeBadge = `<span class="status-badge badge-prompt">Prompt Skill</span>`;
      const charCount = (sk.content || '').length;
      cmdOrContent = `<span style="font-family: var(--font-mono); font-size: 0.78rem; color: #c084fc;">Markdown (${charCount} chars)</span>`;
    } else {
      typeBadge = `<span class="status-badge badge-mcp">${sk.transport}</span>`;
      const cmd = sk.command ? `${sk.command} ${(sk.args || []).join(' ')}` : (sk.url || '-');
      cmdOrContent = `<span style="font-family: var(--font-mono); font-size: 0.78rem;" title="${cmd}">${cmd}</span>`;
    }
    
    let targetsStr = '-';
    if (sk.targets === 'all') {
      targetsStr = 'All Clients';
    } else if (Array.isArray(sk.targets)) {
      targetsStr = sk.targets.map(t => typeof t === 'string' ? t : t.client_id).join(', ');
    }

    const isHealthy = sk.kind === 'agent_skill' || (sk.health && sk.health.status === 'healthy');
    const healthBadge = isHealthy
      ? `<span style="color: var(--accent-green); font-weight: 600;">✔ OK</span>`
      : `<span style="color: var(--accent-yellow); font-weight: 600;" title="${sk.health ? sk.health.message : ''}">⚠ ${sk.health ? sk.health.status : 'Check'}</span>`;

    tr.innerHTML = `
      <td style="font-weight: 700; color: var(--accent-blue);">${sk.id}</td>
      <td style="font-weight: 500;">${sk.name || sk.id}</td>
      <td>${typeBadge}</td>
      <td style="max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${cmdOrContent}</td>
      <td><span style="font-size: 0.8rem; color: var(--text-secondary);">${targetsStr}</span></td>
      <td>${healthBadge}</td>
      <td style="text-align: right;">
        <button class="btn btn-sm btn-danger" onclick="removeServer('${sk.id}')">Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Load History
async function loadHistory() {
  try {
    const history = await apiGet('/api/history');
    const tbody = document.getElementById('history-tbody');
    tbody.innerHTML = '';

    if (history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary); padding: 1.5rem;">${t('no_history')}</td></tr>`;
      return;
    }

    history.forEach(h => {
      const tr = document.createElement('tr');
      const isApplied = h.status === 'applied';
      const statusColor = isApplied ? 'var(--accent-green)' : 'var(--accent-yellow)';
      const dateStr = new Date(h.created_at).toLocaleString();
      const stepsCount = h.steps ? h.steps.length : 0;

      tr.innerHTML = `
        <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-blue);">${h.id}</td>
        <td>${dateStr}</td>
        <td style="color: ${statusColor}; font-weight: 600;">${h.status}</td>
        <td style="font-size: 0.82rem; color: var(--text-secondary);">${stepsCount} steps executed</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Failed to load history', err);
  }
}

// Remove Server / Skill
window.removeServer = async function(skillId) {
  if (!confirm(`${t('confirm_delete')}\nID: ${skillId}`)) return;
  try {
    await apiDelete(`/api/skills/${skillId}`);
    showToast(t('toast_deleted'), 'success');
    await refreshAll();
  } catch (err) {
    showToast(`${t('toast_error')} ${err.message}`, 'error');
  }
};

async function refreshAll() {
  await Promise.all([loadClients(), loadSkills(), loadHistory()]);
}

// Modals Handling
const addModal = document.getElementById('add-modal');
const settingsModal = document.getElementById('settings-modal');

// Tab Switching inside Add Modal
function switchAddTab(tab) {
  activeAddTab = tab;
  const mcpBtn = document.getElementById('tab-btn-mcp');
  const promptBtn = document.getElementById('tab-btn-prompt');
  const mcpForm = document.getElementById('form-mcp');
  const promptForm = document.getElementById('form-prompt');

  if (tab === 'prompt') {
    promptBtn.classList.add('active');
    mcpBtn.classList.remove('active');
    promptForm.style.display = 'block';
    mcpForm.style.display = 'none';
  } else {
    mcpBtn.classList.add('active');
    promptBtn.classList.remove('active');
    mcpForm.style.display = 'block';
    promptForm.style.display = 'none';
  }
}

document.getElementById('tab-btn-mcp').onclick = () => switchAddTab('mcp');
document.getElementById('tab-btn-prompt').onclick = () => switchAddTab('prompt');

// Open Add Skill Modal
function openAddModal() {
  // Reset MCP inputs
  document.getElementById('input-id').value = '';
  document.getElementById('input-name').value = '';
  document.getElementById('input-cmd').value = '';
  document.getElementById('input-args').value = '';
  document.getElementById('input-env').value = '';
  document.getElementById('template-select').value = '';

  // Reset Prompt inputs
  document.getElementById('input-prompt-id').value = '';
  document.getElementById('input-prompt-name').value = '';
  document.getElementById('input-prompt-desc').value = '';
  document.getElementById('input-prompt-content').value = '';
  document.getElementById('prompt-template-select').value = '';

  document.getElementById('target-all').checked = true;
  document.getElementById('targets-clients-list').style.display = 'none';

  switchAddTab('mcp');
  addModal.style.display = 'flex';
}

function closeAddModal() {
  addModal.style.display = 'none';
}

document.getElementById('btn-header-add').onclick = openAddModal;
document.getElementById('btn-open-add').onclick = openAddModal;
document.getElementById('btn-close-modal').onclick = closeAddModal;
document.getElementById('btn-cancel-modal').onclick = closeAddModal;

// Target All checkbox toggle
document.getElementById('target-all').onchange = (e) => {
  const sublist = document.getElementById('targets-clients-list');
  sublist.style.display = e.target.checked ? 'none' : 'grid';
};

// MCP Templates
document.getElementById('template-select').onchange = (e) => {
  const val = e.target.value;
  const idInput = document.getElementById('input-id');
  const nameInput = document.getElementById('input-name');
  const cmdInput = document.getElementById('input-cmd');
  const argsInput = document.getElementById('input-args');
  const envInput = document.getElementById('input-env');

  if (val === 'github') {
    idInput.value = 'github';
    nameInput.value = 'GitHub Integration';
    cmdInput.value = 'npx';
    argsInput.value = '-y @modelcontextprotocol/server-github';
    envInput.value = 'GITHUB_PERSONAL_ACCESS_TOKEN=your_token_here';
  } else if (val === 'filesystem') {
    idInput.value = 'filesystem';
    nameInput.value = 'Filesystem Access';
    cmdInput.value = 'npx';
    argsInput.value = '-y @modelcontextprotocol/server-filesystem C:\\Users';
    envInput.value = '';
  } else if (val === 'fetch') {
    idInput.value = 'fetch';
    nameInput.value = 'Fetch Web Scraper';
    cmdInput.value = 'uvx';
    argsInput.value = 'mcp-server-fetch';
    envInput.value = '';
  } else if (val === 'sqlite') {
    idInput.value = 'sqlite';
    nameInput.value = 'SQLite Database';
    cmdInput.value = 'uvx';
    argsInput.value = 'mcp-server-sqlite --db-path my_database.db';
    envInput.value = '';
  } else if (val === 'memory') {
    idInput.value = 'memory';
    nameInput.value = 'Knowledge Graph Memory';
    cmdInput.value = 'npx';
    argsInput.value = '-y @modelcontextprotocol/server-memory';
    envInput.value = '';
  } else if (val === 'brave') {
    idInput.value = 'brave-search';
    nameInput.value = 'Brave Web Search';
    cmdInput.value = 'npx';
    argsInput.value = '-y @modelcontextprotocol/server-brave-search';
    envInput.value = 'BRAVE_API_KEY=your_brave_api_key';
  } else if (val === 'postgres') {
    idInput.value = 'postgres';
    nameInput.value = 'PostgreSQL Connector';
    cmdInput.value = 'npx';
    argsInput.value = '-y @modelcontextprotocol/server-postgres postgresql://localhost/mydb';
    envInput.value = '';
  }
};

// Prompt Skill Templates
document.getElementById('prompt-template-select').onchange = (e) => {
  const val = e.target.value;
  const idInput = document.getElementById('input-prompt-id');
  const nameInput = document.getElementById('input-prompt-name');
  const descInput = document.getElementById('input-prompt-desc');
  const contentInput = document.getElementById('input-prompt-content');

  if (val === 'code_review') {
    idInput.value = 'code-review-standards';
    nameInput.value = 'Senior Code Review Guidelines';
    descInput.value = 'Engineering standards for pull request reviews and safety checks';
    contentInput.value = CODE_REVIEW_TEMPLATE;
  } else if (val === 'architecture') {
    idInput.value = 'adr-architecture';
    nameInput.value = 'Architecture Decision Record';
    descInput.value = 'Architecture decision and technical specification standard';
    contentInput.value = ARCHITECTURE_TEMPLATE;
  } else if (val === 'api_design') {
    idInput.value = 'api-design-standards';
    nameInput.value = 'REST & GraphQL Design Standards';
    descInput.value = 'Conventions for endpoint naming, HTTP codes, and error envelopes';
    contentInput.value = API_DESIGN_TEMPLATE;
  }
};

// Save New Skill (Handles both MCP and Prompt Skill)
document.getElementById('btn-save-server').onclick = async () => {
  // Parse common targets
  const targetAll = document.getElementById('target-all').checked;
  const targets = [];
  if (!targetAll) {
    document.querySelectorAll('.target-client-check:checked').forEach(chk => {
      targets.push(chk.value);
    });
  }

  if (activeAddTab === 'prompt') {
    const id = document.getElementById('input-prompt-id').value.trim();
    const name = document.getElementById('input-prompt-name').value.trim() || id;
    const desc = document.getElementById('input-prompt-desc').value.trim();
    const content = document.getElementById('input-prompt-content').value.trim();
    const scope = document.getElementById('input-prompt-scope').value;

    if (!id || !content) {
      alert('Skill ID and Prompt Content are required!');
      return;
    }

    try {
      await apiPost('/api/skills', {
        id: id,
        name: name,
        description: desc,
        kind: 'agent_skill',
        content: content,
        scope: scope,
        targets: targets
      });

      closeAddModal();
      showToast(t('toast_added'), 'success');
      await refreshAll();
    } catch (err) {
      showToast(`${t('toast_error')} ${err.message}`, 'error');
    }
  } else {
    const id = document.getElementById('input-id').value.trim();
    const name = document.getElementById('input-name').value.trim() || id;
    const transport = document.getElementById('input-transport').value;
    const cmd = document.getElementById('input-cmd').value.trim();
    const argsStr = document.getElementById('input-args').value.trim();
    const envStr = document.getElementById('input-env').value.trim();

    if (!id || !cmd) {
      alert('Server ID and Command are required!');
      return;
    }

    const env = {};
    if (envStr) {
      envStr.split('\n').forEach(line => {
        const idx = line.indexOf('=');
        if (idx !== -1) {
          env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
        }
      });
    }

    try {
      await apiPost('/api/skills', {
        id: id,
        name: name,
        transport: transport,
        command: cmd,
        args: argsStr ? argsStr.split(/\s+/).filter(Boolean) : [],
        env: env,
        kind: 'mcp_server',
        targets: targets
      });

      closeAddModal();
      showToast(t('toast_added'), 'success');
      await refreshAll();
    } catch (err) {
      showToast(`${t('toast_error')} ${err.message}`, 'error');
    }
  }
};

// Open Settings Modal
async function openSettingsModal() {
  try {
    cachedSettings = await apiGet('/api/settings');
    document.getElementById('set-language').value = 'en';
    document.getElementById('set-approval-mode').value = cachedSettings.approval_mode || 'always_ask';
    document.getElementById('set-max-backups').value = cachedSettings.backup ? cachedSettings.backup.per_client_retention : 20;
    document.getElementById('set-retention-days').value = cachedSettings.backup ? cachedSettings.backup.retention_days : 30;

    // Render client overrides
    const container = document.getElementById('client-overrides-container');
    container.innerHTML = '';

    cachedClients.forEach(c => {
      const existingOverride = (cachedSettings.clients && cachedSettings.clients[c.client_id]) 
        ? cachedSettings.clients[c.client_id].path_override 
        : '';

      const row = document.createElement('div');
      row.className = 'client-override-row';
      row.innerHTML = `
        <span class="name">${c.client_id}</span>
        <div class="input-wrapper">
          <input type="text" class="form-control font-mono client-override-input" 
            data-client="${c.client_id}" 
            value="${existingOverride || ''}" 
            placeholder="${c.path || 'Enter custom config file path...'}">
        </div>
      `;
      container.appendChild(row);
    });

    settingsModal.style.display = 'flex';
  } catch (err) {
    showToast(`${t('toast_error')} ${err.message}`, 'error');
  }
}

function closeSettingsModal() {
  settingsModal.style.display = 'none';
}

document.getElementById('btn-open-settings').onclick = openSettingsModal;
document.getElementById('btn-close-settings').onclick = closeSettingsModal;
document.getElementById('btn-cancel-settings').onclick = closeSettingsModal;

// Save Settings
document.getElementById('btn-save-settings').onclick = async () => {
  const newApproval = document.getElementById('set-approval-mode').value;
  const maxBackups = parseInt(document.getElementById('set-max-backups').value, 10) || 20;
  const retentionDays = parseInt(document.getElementById('set-retention-days').value, 10) || 30;

  // Gather client overrides
  const clientsObj = cachedSettings.clients || {};
  document.querySelectorAll('.client-override-input').forEach(inp => {
    const cid = inp.getAttribute('data-client');
    const val = inp.value.trim();
    if (!clientsObj[cid]) {
      clientsObj[cid] = { enabled: true, strategy: "file" };
    }
    clientsObj[cid].path_override = val || null;
  });

  const payload = {
    language: 'en',
    approval_mode: newApproval,
    backup: {
      per_client_retention: maxBackups,
      retention_days: retentionDays,
      mirror_central: true
    },
    clients: clientsObj
  };

  try {
    await apiPut('/api/settings', payload);
    cachedSettings = payload;
    closeSettingsModal();
    showToast(t('toast_saved'), 'success');
    await refreshAll();
  } catch (err) {
    showToast(`${t('toast_error')} ${err.message}`, 'error');
  }
};

// Sync All Button
document.getElementById('btn-sync').onclick = async () => {
  const btn = document.getElementById('btn-sync');
  const btnText = document.getElementById('sync-btn-text');
  const origText = btnText.textContent;
  btnText.textContent = 'Syncing...';
  btn.disabled = true;

  try {
    await apiPost('/api/sync');
    showToast(t('toast_synced'), 'success');
    await refreshAll();
  } catch (err) {
    showToast(`${t('toast_error')} ${err.message}`, 'error');
  } finally {
    btnText.textContent = origText;
    btn.disabled = false;
  }
};

// Undo Button
document.getElementById('btn-undo').onclick = async () => {
  if (!confirm(t('confirm_undo'))) return;
  try {
    const res = await apiPost('/api/undo');
    if (res.status === 'ok') {
      showToast(t('toast_undo'), 'success');
      await refreshAll();
    } else {
      showToast('No transaction to undo!', 'error');
    }
  } catch (err) {
    showToast(`${t('toast_error')} ${err.message}`, 'error');
  }
};

// Search filter
document.getElementById('skills-search').oninput = () => {
  renderSkills();
};

// Init
window.addEventListener('DOMContentLoaded', async () => {
  try {
    cachedSettings = await apiGet('/api/settings');
  } catch (err) {
    // Offline / local fallback
  }
  await refreshAll();
});
