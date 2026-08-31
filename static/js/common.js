function showToast(message, duration) {
    duration = duration || 3000;
    var container = document.getElementById('toast-container');
    var toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, duration);
}

function fetchJSON(url, callback) {
    fetch(url)
        .then(function(res) { return res.json(); })
        .then(callback)
        .catch(function(err) { console.error('Fetch error:', err); });
}

function updateStatus() {
    fetchJSON('/api/status', function(data) {
        updateRecentErrors(data.scheduler && data.scheduler.recent_errors);
        var cfnBadge = document.getElementById('cfn-badge');
        var mockBadge = document.getElementById('mock-badge');

        if (cfnBadge) {
            if (data.authenticated) {
                cfnBadge.className = 'badge badge-on';
                cfnBadge.textContent = 'CFN ON';
            } else {
                cfnBadge.className = 'badge badge-off';
                cfnBadge.textContent = 'CFN OFF';
            }
        }

        if (mockBadge) {
            if (data.mock_mode) {
                mockBadge.style.display = 'inline';
            } else {
                mockBadge.style.display = 'none';
            }
        }
    });
}

function updateRecentErrors(errors) {
    var list = document.getElementById('recent-errors-list');
    if (!list || !Array.isArray(errors)) return;
    list.textContent = '';
    if (errors.length === 0) {
        var empty = document.createElement('p');
        empty.style.cssText = 'color:var(--text-dim);padding:12px 0;';
        empty.textContent = 'エラー履歴はありません。';
        list.appendChild(empty);
        return;
    }
    var table = document.createElement('table');
    table.style.cssText = 'font-size:0.8rem;width:100%;';
    var head = document.createElement('thead');
    var headRow = document.createElement('tr');
    ['日時', '発生箇所', '内容', '例外', 'HTTP'].forEach(function(label) {
        var cell = document.createElement('th');
        cell.textContent = label;
        headRow.appendChild(cell);
    });
    head.appendChild(headRow);
    table.appendChild(head);
    var body = document.createElement('tbody');
    errors.forEach(function(error) {
        var row = document.createElement('tr');
        var values = [
            formatRecentErrorTime(error.timestamp),
            error.source_label || '-',
            (error.summary || '-') + (error.kind ? ' (' + error.kind + ')' : ''),
            error.exception_type || '-',
            error.status_code || '-',
        ];
        values.forEach(function(value) {
            var cell = document.createElement('td');
            cell.textContent = String(value);
            row.appendChild(cell);
        });
        body.appendChild(row);
    });
    table.appendChild(body);
    list.appendChild(table);
}

function formatRecentErrorTime(value) {
    if (!value) return '-';
    var date = new Date(value);
    if (isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat('ja-JP', {
        timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }).format(date) + ' JST';
}

function setTheme(theme) {
    document.body.className = theme;
    localStorage.setItem('dashboard_theme', theme);
}

// Apply saved theme on load
(function() {
    var saved = localStorage.getItem('dashboard_theme');
    if (saved) {
        document.body.className = saved;
        var sel = document.getElementById('theme-select');
        if (sel) sel.value = saved;
    }
})();

document.addEventListener('DOMContentLoaded', function() {
    updateStatus();
    setInterval(updateStatus, 10000);
});
