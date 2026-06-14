let currentAI = 'gpt'; // Match lowercase DB default
let fetchTimeout;
let equityChartInstance = null;
let pnlChartInstance = null;

// Utility functions
const formatCurrency = (val) => {
    const num = parseFloat(val) || 0;
    return (num >= 0 ? '₹' : '-₹') + Math.abs(num).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
};

const formatPercent = (val) => {
    const num = parseFloat(val) || 0;
    return num.toFixed(2) + '%';
};

const getColorClass = (val) => {
    const num = parseFloat(val) || 0;
    if (num > 0) return 'text-profit';
    if (num < 0) return 'text-loss';
    return '';
};

// Main Data Fetcher
const fetchDashboardData = async () => {
    document.getElementById('loading-indicator').classList.remove('d-none');
    clearTimeout(fetchTimeout); // Prevent double firing
    
    try {
        await Promise.all([
            loadLeaderboard(),
            loadStats(currentAI),
            loadTrades(currentAI),
            loadCharts(currentAI)
        ]);
    } catch (error) {
        console.error("Error fetching data:", error);
    } finally {
        document.getElementById('loading-indicator').classList.add('d-none');
        // Safely loop every 5 seconds
        fetchTimeout = setTimeout(fetchDashboardData, 5000);
    }
};

const switchAI = (aiName) => {
    currentAI = aiName;
    document.getElementById('table-ai-label').innerText = aiName.toUpperCase();
    fetchDashboardData();
};

// API calls & DOM Updates
const loadLeaderboard = async () => {
    const res = await fetch('/api/leaderboard');
    const data = await res.json();
    
    const medals = [1, 2, 3];
    medals.forEach((pos, index) => {
        const entry = data[index];
        const nameEl = document.getElementById(`rank-${pos}-name`);
        const pnlEl = document.getElementById(`rank-${pos}-pnl`);
        
        if (entry) {
            nameEl.innerText = entry.ai_name.toUpperCase();
            pnlEl.innerText = formatCurrency(entry.total_pnl);
            pnlEl.className = `badge ms-1 ${parseFloat(entry.total_pnl) >= 0 ? 'bg-success' : 'bg-danger'}`;
        } else {
            nameEl.innerText = "TBD";
            pnlEl.innerText = "-";
            pnlEl.className = 'badge bg-secondary ms-1';
        }
    });
};

const loadStats = async (aiName) => {
    const res = await fetch(`/api/dashboard/${aiName}`);
    const data = await res.json();

    const setEl = (id, val, isCurrency = false, isPercent = false, checkColor = false) => {
        const el = document.getElementById(id);
        if(!el) return;
        
        if (isCurrency) {
            el.innerText = formatCurrency(val);
        } else if (isPercent) {
            el.innerText = formatPercent(val);
        } else {
            el.innerText = val;
        }

        if (checkColor) {
            el.className = getColorClass(val);
        }
    };

    setEl('stat-capital', data.current_capital, true);
    setEl('stat-today-pnl', data.today_pnl, true, false, true);
    setEl('stat-total-pnl', data.total_pnl, true, false, true);
    setEl('stat-realized-pnl', data.realized_pnl, true, false, true);
    setEl('stat-unrealized-pnl', data.unrealized_pnl, true, false, true);
    
    setEl('stat-open-pos', data.open_position);
    setEl('stat-trades-today', data.trades_today);
    setEl('stat-win-rate', data.win_rate, false, true);
    setEl('stat-total-trades', data.total_trades);
    setEl('stat-rank', data.current_rank);
};

const loadTrades = async (aiName) => {
    const res = await fetch(`/api/trades/${aiName}`);
    const trades = await res.json();
    
    const tbody = document.querySelector('#trades-table tbody');
    const emptyState = document.getElementById('empty-state');
    const table = document.getElementById('trades-table');
    
    tbody.innerHTML = '';
    
    if (!trades || trades.length === 0) {
        table.classList.add('d-none');
        emptyState.classList.remove('d-none');
        return;
    }
    
    table.classList.remove('d-none');
    emptyState.classList.add('d-none');

    trades.forEach(t => {
        const row = document.createElement('tr');
        
        const isBuy = t.action.toUpperCase() === 'BUY';
        const actionClass = isBuy ? 'action-buy' : 'action-sell';
        
        // Ensure PnL is rendered correctly for closed trades only
        const pnlFormatted = t.pnl ? formatCurrency(t.pnl) : '-';
        const pnlClass = t.pnl ? getColorClass(t.pnl) : '';

        row.innerHTML = `
            <td>${t.time}</td>
            <td class="${actionClass}">${t.action}</td>
            <td class="fw-bold">${t.symbol}</td>
            <td>${t.quantity}</td>
            <td>${formatCurrency(t.price)}</td>
            <td class="${pnlClass} fw-bold">${pnlFormatted}</td>
            <td class="text-truncate" style="max-width: 150px;" title="${t.reason}">${t.reason}</td>
        `;
        tbody.appendChild(row);
    });
};

const loadCharts = async (aiName) => {
    const res = await fetch(`/api/equity/${aiName}`);
    const data = await res.json();

    const labels = data.dates || [];
    const equityData = data.equity || [];
    const dailyPnlData = data.daily_pnl || [];

    // Chart Options Default overrides
    Chart.defaults.color = '#a0a0a0';
    Chart.defaults.borderColor = '#333';

    // 1. Overall Equity Curve
    const ctxEquity = document.getElementById('equityCurveChart').getContext('2d');
    if (equityChartInstance) equityChartInstance.destroy();
    
    equityChartInstance = new Chart(ctxEquity, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Equity Curve',
                data: equityData,
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: true, text: 'Overall Equity Curve' }
            },
            interaction: {
                intersect: false,
                mode: 'index',
            }
        }
    });

    // 2. Daily P&L Bar Chart
    const ctxPnl = document.getElementById('dailyPnlChart').getContext('2d');
    if (pnlChartInstance) pnlChartInstance.destroy();

    const pnlColors = dailyPnlData.map(val => val >= 0 ? '#00e676' : '#ff5252');

    pnlChartInstance = new Chart(ctxPnl, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Daily P&L',
                data: dailyPnlData,
                backgroundColor: pnlColors,
                borderRadius: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: true, text: 'Daily P&L' }
            }
        }
    });
};

// Initialize First Call
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('table-ai-label').innerText = currentAI.toUpperCase();
    fetchDashboardData();
});