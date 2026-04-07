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
