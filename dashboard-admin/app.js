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

  // Live clock
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

    // Update KPI Cards
    const cards = document.querySelectorAll('.kpi-card h3');
    if (cards.length >= 5) {
      cards[0].textContent = stats.total_users.toLocaleString();
      cards[1].textContent = stats.active_users.toLocaleString();
      cards[2].textContent = stats.total_assessments.toLocaleString();
      cards[3].textContent = stats.total_videos.toLocaleString();
      cards[4].textContent = stats.new_users_30d.toLocaleString();
    }

    initCharts(stats, growth);
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
        "Only Psychology",
        "Psychology + Neuroscience",
        "Psychology + Neuro + Letter",
        "Psychology + Neuro + Letter + Astrology",
        "Fully Completed"
      ];

      const icons = ['bx-brain', 'bx-network-chart', 'bx-text', 'bx-star', 'bx-trophy'];
      const shortLabels = ['Psychology', 'Neuroscience', 'Letter Science', 'Astrology', 'Comprehensive'];

      // We need to calculate cumulative users who REACHED each stage
      // The backend returns users who STOPPED at each stage
      let cumulativeUsers = [];
      let runningTotal = 0;

      // Calculate from end to beginning to get running total of who reached the stage
      for (let i = stageOrder.length - 1; i >= 0; i--) {
        const stage = stageOrder[i];
        runningTotal += (journeyData[stage] || 0);
        cumulativeUsers[i] = runningTotal;
      }

      let html = `<div style="display: flex; align-items: center; justify-content: space-between; overflow-x: auto; padding: 1rem 0.5rem; gap: 1rem;">`;

      stageOrder.forEach((stage, index) => {
        const usersReachingHere = cumulativeUsers[index];
        const prevUsers = index === 0 ? cumulativeUsers[0] : cumulativeUsers[index - 1];

        // Calculate Drop-off from previous stage
        let dropOffHtml = '';
        if (index > 0) {
          const dropOffCount = prevUsers - usersReachingHere;
          const dropOffPercent = prevUsers === 0 ? 0 : Math.round((dropOffCount / prevUsers) * 100);

          dropOffHtml = `
            <div style="display: flex; flex-direction: column; align-items: center; min-width: 60px;">
              <span style="color: #ef4444; font-size: 0.75rem; font-weight: 700; white-space: nowrap; margin-bottom: 4px;">🔻 -${dropOffPercent}%</span>
              <div style="height: 2px; width: 100%; background: var(--border-color); position: relative;">
                <i class='bx bx-chevron-right' style="position: absolute; right: -8px; top: -6px; color: var(--text-muted); font-size: 1rem;"></i>
              </div>
            </div>
          `;
        }

        const isLast = index === stageOrder.length - 1;
        const color = isLast ? '#10b981' : 'var(--primary-color)';
        const bg = isLast ? '#d1fae5' : 'rgba(92, 109, 250, 0.1)';

        html += `
          ${dropOffHtml}
          <div style="display: flex; flex-direction: column; align-items: center; min-width: 120px; text-align: center; flex: 1;">
            <div style="width: 56px; height: 56px; border-radius: 12px; background: ${bg}; color: ${color}; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; margin-bottom: 0.75rem; border: 1px solid ${color}40; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
              <i class='bx ${icons[index]}'></i>
            </div>
            <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-main); margin-bottom: 0.25rem;">${shortLabels[index]}</span>
            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 500;">
              ${usersReachingHere} <i class='bx bx-user' style="font-size: 0.7rem;"></i>
            </span>
          </div>
        `;
      });

      html += `</div>`;

      // Override layout of the container locally for horizontal scroll if needed
      journeyContainer.style.flexDirection = 'row';
      journeyContainer.style.display = 'block';
      journeyContainer.innerHTML = html;
    }
  }
}
