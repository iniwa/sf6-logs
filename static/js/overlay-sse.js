/**
 * SSE client for overlay real-time updates.
 * Requires: updateStats(data) and optionally refreshHistory() to be defined by the page.
 * Uses overlayMode (set in base_overlay.html) to decide SSE vs polling.
 */
(function() {
    // preview モード時は SSE/ポーリングを無効化（親ウィンドウから直接制御）
    if (new URLSearchParams(window.location.search).get('preview') === '1') return;

    var pollFallback = null;
    var useMode = typeof overlayMode !== 'undefined' && overlayMode !== 'all';

    function startPolling() {
        if (pollFallback) return;
        pollFallback = setInterval(function() {
            if (typeof refresh === 'function') refresh();
        }, 5000);
    }

    // モード指定時は SSE の全体データが使えないためポーリング
    if (useMode || typeof EventSource === 'undefined') {
        startPolling();
        return;
    }

    var es = new EventSource('/api/stream');

    es.addEventListener('stats', function(e) {
        try {
            var d = JSON.parse(e.data);
            if (typeof updateStats === 'function') updateStats(d);
            if (typeof refreshHistory === 'function') refreshHistory();
        } catch (err) {}
    });

    es.onerror = function() {
        es.close();
        startPolling();
    };
})();
