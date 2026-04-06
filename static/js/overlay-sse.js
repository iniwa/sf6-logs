/**
 * SSE client for overlay real-time updates.
 * Requires: updateStats(data) and optionally refreshHistory() to be defined by the page.
 */
(function() {
    var pollFallback = null;

    function startPolling() {
        if (pollFallback) return;
        pollFallback = setInterval(function() {
            if (typeof refresh === 'function') refresh();
        }, 5000);
    }

    if (typeof EventSource === 'undefined') {
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
