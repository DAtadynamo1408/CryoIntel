/* =============================================
   CryoIntel — App Logic
   ============================================= */

Chart.defaults.color = 'rgba(180,190,210,0.75)';
Chart.defaults.font.family = 'Inter, sans-serif';
Chart.defaults.font.size = 12;

const BLEND_COLORS = {
    'R407':                          { line:'#3b82f6', fill:'rgba(59,130,246,0.12)' },
    'R32/R125/R152a (70/10/20)':     { line:'#8b5cf6', fill:'rgba(139,92,246,0.12)' },
    'R32/R125/R152a (20/10/70)':     { line:'#10b981', fill:'rgba(16,185,129,0.12)' },
    'R32/R125/R152a (15/15/70)':     { line:'#f59e0b', fill:'rgba(245,158,11,0.12)' },
    'R32/R125/R152a (30/10/60)':     { line:'#06b6d4', fill:'rgba(6,182,212,0.12)' },
};

let charts = {};
let predData = [];
let calcHistory = [];
let calcRowCount = 0;

/* =============================================
   TOAST NOTIFICATIONS
   ============================================= */
function toast(msg, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(() => el.remove(), 300); }, duration);
}

/* =============================================
   SIDEBAR NAVIGATION
   ============================================= */
document.addEventListener('DOMContentLoaded', () => {
    const navItems = document.querySelectorAll('.nav-item');
    const tabPages = document.querySelectorAll('.tab-page');

    navItems.forEach(btn => {
        btn.addEventListener('click', () => {
            navItems.forEach(b => b.classList.remove('active'));
            tabPages.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });

    // Slider live display
    bindSlider('massSlider',    'massValue',    v => `${parseFloat(v).toFixed(2)} kg`);
    bindSlider('durationSlider','durationValue',v => `${v} min`);
    bindSlider('cmpMassSlider', 'cmpMassValue', v => `${parseFloat(v).toFixed(2)} kg`);
    bindSlider('cmpDurSlider',  'cmpDurValue',  v => `${v} min`);

    // Table search
    document.getElementById('tableSearch')?.addEventListener('input', filterPredTable);

    // Form submissions
    document.getElementById('prediction-form')?.addEventListener('submit', handlePredict);
    document.getElementById('calc-form')?.addEventListener('submit', handleCalculate);
    document.getElementById('compare-form')?.addEventListener('submit', handleCompare);
    document.getElementById('clearCalcBtn')?.addEventListener('click', clearCalcHistory);
    document.getElementById('exportPredBtn')?.addEventListener('click', exportPredCSV);
    document.getElementById('exportCalcBtn')?.addEventListener('click', exportCalcCSV);
});

function bindSlider(sliderId, displayId, fmt) {
    const slider = document.getElementById(sliderId);
    const display = document.getElementById(displayId);
    if (!slider || !display) return;
    display.textContent = fmt(slider.value);
    slider.addEventListener('input', e => { display.textContent = fmt(e.target.value); });
}

/* =============================================
   ML PREDICTOR
   ============================================= */
async function handlePredict(e) {
    e.preventDefault();
    const btn = document.getElementById('predictBtn');
    const mass = parseFloat(document.getElementById('massSlider').value);
    const blend = document.getElementById('predBlend').value;
    const duration = parseInt(document.getElementById('durationSlider').value);

    setLoading(btn, true);
    try {
        const res = await fetch('/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mass, blend, duration })
        });
        const result = await res.json();
        if (result.success) {
            predData = result.data;
            updatePredDashboard(result.data, blend);
            document.getElementById('exportPredBtn').classList.remove('hidden');
            toast('Forecast generated successfully', 'success');
        } else {
            toast('Prediction error: ' + result.error, 'error');
        }
    } catch (err) {
        toast('Connection to server failed.', 'error');
    } finally {
        setLoading(btn, false);
    }
}

function updatePredDashboard(data, blend) {
    if (!data || !data.length) return;

    const cops      = data.map(d => d.COP);
    const wcomps    = data.map(d => d.Wcomp);
    const exergies  = data.map(d => d.ExergyMag);
    const tls       = data.map(d => d.TL);

    const peakCop   = Math.max(...cops);
    const minWcomp  = Math.min(...wcomps);
    const peakExergy= Math.max(...exergies);
    const minTL     = Math.min(...tls);

    // Animate metrics
    animVal('peakCop',    peakCop,        v => v.toFixed(3));
    animVal('minWcomp',   minWcomp,       v => v.toFixed(3) + '<span> kW</span>');
    animVal('peakExergy', peakExergy*100, v => v.toFixed(2) + '<span>%</span>');
    animVal('minTL',      minTL,          v => v.toFixed(1)  + '<span>°C</span>');

    // Update topbar quick stats
    document.getElementById('qs-cop-val').textContent   = peakCop.toFixed(3);
    document.getElementById('qs-wcomp-val').textContent = minWcomp.toFixed(3) + ' kW';
    document.getElementById('qs-exergy-val').textContent= (peakExergy*100).toFixed(2) + '%';

    updatePredCharts(data, blend);
    updatePredTable(data);
}

function updatePredCharts(data, blend) {
    const labels = data.map(d => d.Time);
    const color  = BLEND_COLORS[blend] || BLEND_COLORS['R407'];

    // --- COP + Exergy chart ---
    destroyChart('performanceChart');
    charts['performanceChart'] = new Chart(
        document.getElementById('performanceChart').getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'COP',
                    data: data.map(d => d.COP),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.1)',
                    borderWidth: 2.5, tension: 0.4, fill: true,
                    pointRadius: 0, pointHoverRadius: 5
                },
                {
                    label: '|η_exergy| ×10',
                    data: data.map(d => d.ExergyMag * 10),
                    borderColor: '#10b981',
                    borderWidth: 2, tension: 0.4,
                    borderDash: [5,4],
                    pointRadius: 0, pointHoverRadius: 5
                }
            ]
        },
        options: chartOpts('Time (min)', 'Value')
    });

    // --- Temperature chart ---
    destroyChart('tempChart');
    charts['tempChart'] = new Chart(
        document.getElementById('tempChart').getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'TL — Evaporator (°C)',
                    data: data.map(d => d.TL),
                    borderColor: '#06b6d4',
                    backgroundColor: 'rgba(6,182,212,0.1)',
                    borderWidth: 2.5, tension: 0.4, fill: true,
                    pointRadius: 0, pointHoverRadius: 5
                },
                {
                    label: 'TH — Compressor (°C)',
                    data: data.map(d => d.TH),
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245,158,11,0.07)',
                    borderWidth: 2.5, tension: 0.4, fill: true,
                    pointRadius: 0, pointHoverRadius: 5
                }
            ]
        },
        options: chartOpts('Time (min)', 'Temperature (°C)')
    });
}

function updatePredTable(data) {
    const tbody = document.getElementById('dataTableBody');
    tbody.innerHTML = '';
    data.forEach((row, i) => {
        const deltaT = (row.TH - row.TL).toFixed(1);
        const tr = document.createElement('tr');
        tr.style.animationDelay = `${i * 0.02}s`;
        tr.innerHTML = `
            <td>${row.Time}</td>
            <td>${row.TL}</td>
            <td>${row.TH}</td>
            <td>${deltaT}</td>
            <td style="color:#3b82f6;font-weight:600">${row.COP.toFixed(4)}</td>
            <td>${row.Wcomp.toFixed(4)}</td>
            <td>${row.Exergy.toFixed(4)}</td>
            <td style="color:#10b981;font-weight:600">${row.ExergyMag.toFixed(4)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function filterPredTable() {
    const q = document.getElementById('tableSearch').value.toLowerCase();
    document.querySelectorAll('#dataTableBody tr').forEach(tr => {
        tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}

/* =============================================
   CALCULATOR
   ============================================= */
async function handleCalculate(e) {
    e.preventDefault();
    const btn  = document.getElementById('calcBtn');
    const time = document.getElementById('calcTime').value;
    const tl   = document.getElementById('calcTL').value;
    const th   = document.getElementById('calcTH').value;
    const blend= document.getElementById('calcBlend').value;
    const mass = document.getElementById('calcMass').value;

    if (parseFloat(th) <= parseFloat(tl)) {
        toast('TH must be strictly greater than TL', 'error'); return;
    }

    setLoading(btn, true);
    try {
        const res = await fetch('/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time, evap_temp: tl, comp_temp: th, blend, mass })
        });
        const result = await res.json();
        if (result.success) {
            showCalcResult(result.data);
            addCalcRow(result.data);
            calcHistory.push(result.data);
            toast('Calculation complete', 'success');
        } else {
            toast('Error: ' + result.error, 'error');
        }
    } catch(err) {
        toast('Connection failed.', 'error');
    } finally {
        setLoading(btn, false);
    }
}

function showCalcResult(d) {
    const preview = document.getElementById('calcResultPreview');
    preview.classList.remove('hidden');
    const deltaT = (d.TH - d.TL).toFixed(2);
    document.getElementById('rCOP').textContent    = d.COP.toFixed(4);
    document.getElementById('rWcomp').textContent  = d.Wcomp.toFixed(4);
    document.getElementById('rExergy').textContent = d.ExergyMag.toFixed(4);
    document.getElementById('rDeltaT').textContent = deltaT;

    // Update topbar
    document.getElementById('qs-cop-val').textContent    = d.COP.toFixed(3);
    document.getElementById('qs-wcomp-val').textContent  = d.Wcomp.toFixed(3) + ' kW';
    document.getElementById('qs-exergy-val').textContent = (d.ExergyMag*100).toFixed(2) + '%';
}

function addCalcRow(d) {
    const tbody = document.getElementById('calcTableBody');
    // Remove empty state row
    const emptyRow = tbody.querySelector('.empty-row') || tbody.querySelector('tr:first-child');
    if (emptyRow && emptyRow.querySelector('.empty-state')) emptyRow.remove();

    calcRowCount++;
    const deltaT = (d.TH - d.TL).toFixed(2);
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td style="color:var(--muted)">${calcRowCount}</td>
        <td>${shortBlend(d.Blend)}</td>
        <td>${d.Mass}</td>
        <td>${d.Time}</td>
        <td>${d.TL.toFixed(2)}</td>
        <td>${d.TH.toFixed(2)}</td>
        <td>${deltaT}</td>
        <td style="color:#3b82f6;font-weight:600">${d.COP.toFixed(4)}</td>
        <td>${d.Wcomp.toFixed(4)}</td>
        <td>${d.Exergy.toFixed(4)}</td>
        <td style="color:#10b981;font-weight:600">${d.ExergyMag.toFixed(4)}</td>
    `;
    tbody.insertBefore(tr, tbody.firstChild);

    document.getElementById('clearCalcBtn').classList.remove('hidden');
    document.getElementById('exportCalcBtn').classList.remove('hidden');
}

function clearCalcHistory() {
    const tbody = document.getElementById('calcTableBody');
    tbody.innerHTML = `<tr><td colspan="11"><div class="empty-state"><p>No calculations yet.</p></div></td></tr>`;
    calcHistory = [];
    calcRowCount = 0;
    document.getElementById('clearCalcBtn').classList.add('hidden');
    document.getElementById('exportCalcBtn').classList.add('hidden');
    document.getElementById('calcResultPreview').classList.add('hidden');
}

/* =============================================
   COMPARE
   ============================================= */
async function handleCompare(e) {
    e.preventDefault();
    const btn = document.getElementById('cmpBtn');
    const selected = [...document.querySelectorAll('input[name="cmpBlend"]:checked')].map(cb => cb.value);
    if (selected.length < 2) { toast('Select at least 2 blends to compare', 'error'); return; }

    const mass     = parseFloat(document.getElementById('cmpMassSlider').value);
    const duration = parseInt(document.getElementById('cmpDurSlider').value);

    setLoading(btn, true);
    try {
        const results = await Promise.all(selected.map(blend =>
            fetch('/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mass, blend, duration })
            }).then(r => r.json()).then(r => ({ blend, data: r.data }))
        ));
        buildCompareCharts(results);
        toast(`Compared ${selected.length} blends`, 'success');
    } catch(err) {
        toast('Comparison failed: ' + err.message, 'error');
    } finally {
        setLoading(btn, false);
    }
}

function buildCompareCharts(results) {
    const labels = results[0].data.map(d => d.Time);

    // COP comparison
    destroyChart('cmpCopChart');
    charts['cmpCopChart'] = new Chart(
        document.getElementById('cmpCopChart').getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: results.map(r => {
                const c = BLEND_COLORS[r.blend] || { line:'#888', fill:'rgba(128,128,128,0.1)' };
                return {
                    label: shortBlend(r.blend),
                    data: r.data.map(d => d.COP),
                    borderColor: c.line, backgroundColor: c.fill,
                    borderWidth: 2.5, tension: 0.4, fill: false,
                    pointRadius: 0, pointHoverRadius: 5
                };
            })
        },
        options: chartOpts('Time (min)', 'COP')
    });

    // Exergy comparison
    destroyChart('cmpExergyChart');
    charts['cmpExergyChart'] = new Chart(
        document.getElementById('cmpExergyChart').getContext('2d'), {
        type: 'line',
        data: {
            labels,
            datasets: results.map(r => {
                const c = BLEND_COLORS[r.blend] || { line:'#888', fill:'rgba(128,128,128,0.1)' };
                return {
                    label: shortBlend(r.blend),
                    data: r.data.map(d => d.ExergyMag * 100),
                    borderColor: c.line, backgroundColor: c.fill,
                    borderWidth: 2.5, tension: 0.4, fill: false,
                    pointRadius: 0, pointHoverRadius: 5
                };
            })
        },
        options: chartOpts('Time (min)', '|η_exergy| (%)')
    });

    // Bar: peak COP comparison
    destroyChart('cmpBarChart');
    charts['cmpBarChart'] = new Chart(
        document.getElementById('cmpBarChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: results.map(r => shortBlend(r.blend)),
            datasets: [
                {
                    label: 'Peak COP',
                    data: results.map(r => Math.max(...r.data.map(d => d.COP))),
                    backgroundColor: results.map(r => (BLEND_COLORS[r.blend] || { line:'#888' }).line + 'cc'),
                    borderRadius: 6, borderSkipped: false
                },
                {
                    label: 'Peak |η_exergy| ×10',
                    data: results.map(r => Math.max(...r.data.map(d => d.ExergyMag)) * 10),
                    backgroundColor: results.map(r => (BLEND_COLORS[r.blend] || { line:'#888' }).line + '66'),
                    borderRadius: 6, borderSkipped: false
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position:'top' }, tooltip: tooltipStyle() },
            scales: {
                y: { beginAtZero: true, grid:{ color:'rgba(255,255,255,0.04)' }, ticks:{ color:'rgba(180,190,210,0.75)' } },
                x: { grid:{ display:false }, ticks:{ color:'rgba(180,190,210,0.75)' } }
            }
        }
    });
}

/* =============================================
   CHART HELPERS
   ============================================= */
function chartOpts(xLabel, yLabel) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 600 },
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { position: 'top', labels:{ boxWidth:12, padding:16 } },
            tooltip: tooltipStyle()
        },
        scales: {
            x: {
                title: { display: true, text: xLabel, color:'rgba(180,190,210,0.6)', font:{size:11} },
                grid: { color:'rgba(255,255,255,0.03)' },
                ticks: { color:'rgba(180,190,210,0.7)', maxTicksLimit:12 }
            },
            y: {
                title: { display: true, text: yLabel, color:'rgba(180,190,210,0.6)', font:{size:11} },
                grid: { color:'rgba(255,255,255,0.04)' },
                ticks: { color:'rgba(180,190,210,0.7)' }
            }
        }
    };
}

function tooltipStyle() {
    return {
        backgroundColor: 'rgba(6,12,26,0.95)',
        titleColor: '#e2e8f8',
        bodyColor: '#94a3b8',
        borderColor: 'rgba(255,255,255,0.08)',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8
    };
}

function destroyChart(id) {
    if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

/* =============================================
   ANIMATE VALUE
   ============================================= */
function animVal(id, end, fmt, duration = 900) {
    const el = document.getElementById(id);
    if (!el) return;
    let start = null;
    const step = (ts) => {
        if (!start) start = ts;
        const progress = Math.min((ts - start) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        el.innerHTML = fmt(ease * end);
        if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

/* =============================================
   LOADING STATE
   ============================================= */
function setLoading(btn, loading) {
    const text   = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');
    if (loading) {
        text.style.display   = 'none';
        loader.style.display = 'block';
        btn.disabled = true;
    } else {
        text.style.display   = '';
        loader.style.display = 'none';
        btn.disabled = false;
    }
}

/* =============================================
   CSV EXPORT
   ============================================= */
function exportPredCSV() {
    if (!predData.length) return;
    const cols = ['Time','TL','TH','COP','Wcomp','Exergy','ExergyMag'];
    const csv  = [cols.join(','), ...predData.map(r => cols.map(c => r[c]).join(','))].join('\n');
    downloadCSV(csv, 'cryo_forecast.csv');
}

function exportCalcCSV() {
    if (!calcHistory.length) return;
    const cols = ['Time','Blend','Mass','TL','TH','COP','Wcomp','Exergy','ExergyMag'];
    const csv  = [cols.join(','), ...calcHistory.map(r => cols.map(c => r[c]).join(','))].join('\n');
    downloadCSV(csv, 'cryo_calculations.csv');
}

function downloadCSV(content, filename) {
    const a   = document.createElement('a');
    a.href    = 'data:text/csv;charset=utf-8,' + encodeURIComponent(content);
    a.download= filename;
    a.click();
    toast('CSV exported', 'success');
}

/* =============================================
   UTILITY
   ============================================= */
function shortBlend(blend) {
    if (blend.includes('R407')) return 'R407';
    const m = blend.match(/\(([^)]+)\)/);
    return m ? m[1] : blend;
}
