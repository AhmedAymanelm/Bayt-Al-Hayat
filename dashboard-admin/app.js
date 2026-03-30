// ─── Global Config ─────────────────────────────────────────────────────────────
window.API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : window.location.origin; // In production (Railway), frontend and backend share the same domain

// ─── Shared API Fetch Helper ───────────────────────────────────────────────────
window.apiFetch = async (path, options = {}) => {
  const token = localStorage.getItem('admin_token');
  if (!token) { window.location.href = 'index.html'; return null; }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  });

  if (res.status === 401 || res.status === 403) {
    localStorage.removeItem('admin_token');
    window.location.href = 'index.html';
    return null;
  }
  return res;
};

// ─── Logout ────────────────────────────────────────────────────────────────────
window.logout = () => {
  localStorage.removeItem('admin_token');
  window.location.href = 'index.html';
};

// ─── Token Guard (redirect if not logged in) ──────────────────────────────────
window.requireAuth = () => {
  const token = localStorage.getItem('admin_token');
  if (!token) { window.location.href = 'index.html'; }
};

// ─── Shared UI Setup ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Initialize i18n
  if (window.initI18n) window.initI18n();

  // Language toggle
  const langBtn = document.getElementById('toggleLanguage');
  if (langBtn) {
    langBtn.addEventListener('click', (e) => {
      e.preventDefault();
      console.log('🔘 Language toggle clicked');
      const current = localStorage.getItem('dashboard_lang') || 'en';
      const next = current === 'en' ? 'ar' : 'en';
      
      if (typeof setLanguage === 'function') {
        setLanguage(next);
        // Reload page-specific elements if needed
        if (typeof loadDashboard === 'function' && document.querySelector('.kpi-grid')) {
          loadDashboard();
        }
      } else {
        console.error('❌ setLanguage function not found!');
      }
    });
  }
  const timeDisplay = document.getElementById('currentDateTime');
  if (timeDisplay) {
    const tick = () => {
      const now = new Date();
      timeDisplay.textContent = now.toISOString().slice(0, 19).replace('T', ' ');
    };
    tick();
    setInterval(tick, 1000);
  }

  // Sidebar toggle
  const toggleBtn = document.getElementById('toggleSidebar');
  const sidebar = document.getElementById('sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });
  }

  // Dark mode toggle
  const themeBtn = document.getElementById('toggleTheme');
  if (themeBtn) {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') document.body.classList.add('dark-mode');

    themeBtn.addEventListener('click', () => {
      document.body.classList.toggle('dark-mode');
      const isDark = document.body.classList.contains('dark-mode');
      localStorage.setItem('theme', isDark ? 'dark' : 'light');
      themeBtn.querySelector('i').className = isDark ? 'bx bx-sun' : 'bx bx-moon';
    });

    if (saved === 'dark') themeBtn.querySelector('i').className = 'bx bx-sun';
  }

  // Fullscreen toggle
  const fsBtn = document.getElementById('toggleFullscreen');
  if (fsBtn) {
    fsBtn.addEventListener('click', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    });
  }

  // ─── Dashboard Page Logic ────────────────────────────────────────────────────
  const kpiGrid = document.querySelector('.kpi-grid');
  if (kpiGrid) {
    requireAuth();
    loadDashboard();
  }
});

// ─── Dashboard Data ────────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [statsRes, growthRes] = await Promise.all([
      apiFetch('/admin/stats'),
      apiFetch('/admin/users/growth')
    ]);
    if (!statsRes || !growthRes) return;

    const stats = await statsRes.json();
    const growth = await growthRes.json();

    if (document.getElementById('aiBalancesContainer')) {
      loadAiBalances();
    }

    // Update KPI Cards
    const cards = document.querySelectorAll('.kpi-card h3');
    if (cards.length >= 6) {
      cards[0].textContent = stats.total_users.toLocaleString();
      cards[1].textContent = stats.active_users.toLocaleString();
      cards[2].textContent = stats.total_assessments.toLocaleString();
      cards[3].textContent = stats.total_videos.toLocaleString();
      cards[4].textContent = stats.new_users_30d.toLocaleString();
      cards[5].textContent = stats.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2 }) + ' EGP';
    } else if (cards.length >= 5) {
      cards[0].textContent = stats.total_users.toLocaleString();
      cards[1].textContent = stats.active_users.toLocaleString();
      cards[2].textContent = stats.total_assessments.toLocaleString();
      cards[3].textContent = stats.total_videos.toLocaleString();
      cards[4].textContent = stats.new_users_30d.toLocaleString();
    }

    initCharts(stats, growth);
    if (window.applyTranslations) window.applyTranslations();
  } catch (err) {
    console.error('Dashboard load error:', err);
  }
}

function initCharts(stats, growth) {
  // User Growth Line Chart
  const growthCtx = document.getElementById('userGrowthChart');
  if (growthCtx) {
    new Chart(growthCtx, {
      type: 'line',
      data: {
        labels: growth.map(g => g.month),
        datasets: [{
          label: 'New Users',
          data: growth.map(g => g.count),
          borderColor: '#4361ee',
          backgroundColor: 'rgba(67, 97, 238, 0.1)',
          tension: 0.4,
          fill: true,
          pointBackgroundColor: '#4361ee',
          pointRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } }
        }
      }
    });
  }

  // Assessment Breakdown Donut
  const pieCtx = document.getElementById('assessmentPieChart');
  if (pieCtx && stats.breakdown) {
    const labels = Object.keys(stats.breakdown);
    const values = Object.values(stats.breakdown);
    new Chart(pieCtx, {
      type: 'doughnut',
      data: {
        labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
        datasets: [{
          data: values,
          backgroundColor: ['#4361ee', '#4cc9f0', '#f72585', '#7209b7', '#3a0ca3'],
          borderWidth: 2,
          borderColor: 'var(--bg-surface)'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'right',
            labels: { boxWidth: 10, padding: 10, font: { size: 11 }, color: 'var(--text-muted)' }
          }
        }
      }
    });
  }

  // Journey Drop-off Funnel Visuals
  const journeyContainer = document.getElementById('journeyDropoffContainer');
  if (journeyContainer && stats.journey) {
    journeyContainer.innerHTML = '';
    const journeyData = stats.journey;

    if (journeyData["No Data Yet"]) {
      journeyContainer.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 1rem;">Not enough data yet.</div>';
    } else {
      const stageOrder = [
        "letter",
        "astrology",
        "psychology",
        "neuroscience",
        "comprehensive"
      ];

      const stageLabels = {
        "letter": "Letter Science",
        "astrology": "Astrology",
        "psychology": "Psychology",
        "neuroscience": "Neuroscience",
        "comprehensive": "Comprehensive"
      };

      const icons      = ['bx-text', 'bx-star', 'bx-brain', 'bx-network-chart', 'bx-trophy'];
      const stageColors = ['#f59e0b', '#8b5cf6', '#6366f1', '#06b6d4', '#10b981'];
      const stageBgs    = ['rgba(245,158,11,0.1)', 'rgba(139,92,246,0.1)', 'rgba(99,102,241,0.1)', 'rgba(6,182,212,0.1)', 'rgba(16,185,129,0.1)'];

      const counts = stageOrder.map(s => journeyData[s] || 0);

      let html = `<div style="display:flex;align-items:center;justify-content:space-between;overflow-x:auto;padding:1rem 0.5rem;gap:0.5rem;">`;

      stageOrder.forEach((stage, i) => {
        const count  = counts[i];
        const color  = stageColors[i];
        const bg     = stageBgs[i];

        // Retention rate: what % of previous stage users continued
        let arrowHtml = '';
        if (i > 0) {
          const prev       = counts[i - 1];
          const retention  = prev === 0 ? 100 : Math.round((count / prev) * 100);
          const isGood     = retention === 100;
          const color_a    = isGood ? '#10b981' : '#ef4444';
          const icon_a     = isGood ? '▲' : '🔻';

          arrowHtml = `
            <div style="display:flex;flex-direction:column;align-items:center;min-width:54px;flex-shrink:0;">
              <span style="color:${color_a};font-size:0.72rem;font-weight:700;white-space:nowrap;margin-bottom:3px;">${icon_a} ${retention}%</span>
              <div style="height:2px;width:100%;background:var(--border-color);position:relative;">
                <i class='bx bx-chevron-right' style="position:absolute;right:-8px;top:-7px;color:var(--text-muted);font-size:1rem;"></i>
              </div>
            </div>`;
        }

        html += `
          ${arrowHtml}
          <div style="display:flex;flex-direction:column;align-items:center;min-width:100px;text-align:center;flex:1;">
            <div style="width:52px;height:52px;border-radius:12px;background:${bg};color:${color};display:flex;align-items:center;justify-content:center;font-size:1.4rem;margin-bottom:0.6rem;border:1.5px solid ${color}40;">
              <i class='bx ${icons[i]}'></i>
            </div>
            <span style="font-size:0.78rem;font-weight:600;color:var(--text-main);margin-bottom:0.2rem;" data-i18n="type-${stage}">${stageLabels[stage]}</span>
            <span style="font-size:0.8rem;font-weight:700;color:${color};">${count} <i class='bx bx-user' style="font-size:0.7rem;font-weight:400;color:var(--text-muted);"></i></span>
          </div>`;
      });

      html += `</div>`;
      journeyContainer.style.display = 'block';
      journeyContainer.innerHTML = html;
    }
  }
}

// ─── AI Models Balances ────────────────────────────────────────────────────────
async function loadAiBalances() {
  const container = document.getElementById('aiBalancesContainer');
  if (!container) return;
  try {
    const res = await apiFetch('/admin/settings/models/balances');
    if (!res) return;
    const balances = await res.json();
    
    if (!balances || balances.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); text-align: center; grid-column: 1 / -1;">No AI models configured.</div>';
      return;
    }

    const icons = {
      'OpenAI': 'bx-message-square-dots',
      'RunwayML': 'bx-film',
      'Cloudinary': 'bx-cloud-upload',
      'Astrology API': 'bx-planet'
    };

    container.innerHTML = balances.map(b => {
      const icon = icons[b.service] || 'bx-brain';
      const statusColor = b.status === 'ok' ? '#10b981' : (b.status === 'warning' ? '#f59e0b' : '#ef4444');
      const bgMap = {
        'ok': 'rgba(16, 185, 129, 0.1)',
        'warning': 'rgba(245, 158, 11, 0.1)',
        'error': 'rgba(239, 68, 68, 0.1)'
      };
      const bg = bgMap[b.status] || 'rgba(100,100,100,0.1)';

      return `
        <div style="border: 1px solid var(--border-color); border-radius: 10px; padding: 1.25rem; display: flex; align-items: center; gap: 1rem; background: var(--bg-body);">
          <div style="width: 48px; height: 48px; border-radius: 12px; background: ${bg}; color: ${statusColor}; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; flex-shrink: 0;">
            <i class='bx ${icon}'></i>
          </div>
          <div style="flex: 1; overflow: hidden;">
            <h4 style="margin: 0 0 0.25rem 0; font-size: 0.9rem; color: var(--text-main); font-weight: 600;">${b.service}</h4>
            <p style="margin: 0; font-size: 0.8rem; color: ${statusColor}; font-weight: 700; line-height: 1.3; overflow-wrap: break-word;" title="${b.balance}">${b.balance}</p>
          </div>
        </div>
      `;
    }).join('');
    
  } catch (err) {
    container.innerHTML = '<div style="color: #ef4444; text-align: center; grid-column: 1 / -1;">Failed to load AI balances.</div>';
  }
}
