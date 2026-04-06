/**
 * Inline SVG LP/MR chart renderer.
 * Usage: renderLpChart('container-id', [{played_at, lp_after, mr_after, result}, ...])
 */
function renderLpChart(containerId, data) {
    var container = document.getElementById(containerId);
    if (!container || !data || data.length < 2) {
        if (container) container.innerHTML = '<p style="color:#8892a0;text-align:center;padding:40px 0;">Not enough data</p>';
        return;
    }

    var W = container.clientWidth || 600;
    var H = 200;
    var pad = {top: 20, right: 20, bottom: 30, left: 55};
    var cw = W - pad.left - pad.right;
    var ch = H - pad.top - pad.bottom;

    // Auto-detect: MR があれば MASTER → MR を使う
    var useMR = data.some(function(d) { return d.mr_after !== null && d.mr_after !== undefined; });
    var key = useMR ? 'mr_after' : 'lp_after';
    var chartLabel = useMR ? 'MR' : 'LP';

    var points = [];
    for (var i = 0; i < data.length; i++) {
        if (data[i][key] !== null && data[i][key] !== undefined) {
            points.push({x: i, lp: data[i][key], result: data[i].result, time: data[i].played_at});
        }
    }
    if (points.length < 2) {
        container.innerHTML = '<p style="color:#8892a0;text-align:center;padding:40px 0;">Not enough ' + chartLabel + ' data</p>';
        return;
    }

    var lpMin = Infinity, lpMax = -Infinity;
    for (var i = 0; i < points.length; i++) {
        if (points[i].lp < lpMin) lpMin = points[i].lp;
        if (points[i].lp > lpMax) lpMax = points[i].lp;
    }
    // Add padding to y range
    var yRange = lpMax - lpMin || 1;
    lpMin -= yRange * 0.1;
    lpMax += yRange * 0.1;

    function sx(i) { return pad.left + (i / (points.length - 1)) * cw; }
    function sy(v) { return pad.top + ch - ((v - lpMin) / (lpMax - lpMin)) * ch; }

    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '" style="display:block;">';

    // Grid lines
    var gridCount = 4;
    for (var g = 0; g <= gridCount; g++) {
        var gy = pad.top + (g / gridCount) * ch;
        var gv = Math.round(lpMax - (g / gridCount) * (lpMax - lpMin));
        svg += '<line x1="' + pad.left + '" y1="' + gy + '" x2="' + (W - pad.right) + '" y2="' + gy + '" stroke="#2a3a5c" stroke-width="1"/>';
        svg += '<text x="' + (pad.left - 8) + '" y="' + (gy + 4) + '" fill="#8892a0" font-size="11" text-anchor="end">' + gv + '</text>';
    }

    // Line path
    var pathD = '';
    for (var i = 0; i < points.length; i++) {
        pathD += (i === 0 ? 'M' : 'L') + sx(i).toFixed(1) + ',' + sy(points[i].lp).toFixed(1);
    }
    svg += '<path d="' + pathD + '" fill="none" stroke="#4ecca3" stroke-width="2" stroke-linejoin="round"/>';

    // Data points
    for (var i = 0; i < points.length; i++) {
        var color = points[i].result === 'win' ? '#4ecca3' : '#e94560';
        svg += '<circle cx="' + sx(i).toFixed(1) + '" cy="' + sy(points[i].lp).toFixed(1) + '" r="3" fill="' + color + '"/>';
    }

    // X-axis labels (show a few)
    var labelInterval = Math.max(1, Math.floor(points.length / 6));
    for (var i = 0; i < points.length; i += labelInterval) {
        var t = points[i].time;
        var label = t ? t.substring(5, 16).replace('T', ' ') : '';
        svg += '<text x="' + sx(i).toFixed(1) + '" y="' + (H - 5) + '" fill="#8892a0" font-size="10" text-anchor="middle">' + label + '</text>';
    }

    svg += '</svg>';
    container.innerHTML = svg;
}
