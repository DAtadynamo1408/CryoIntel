// Chart instance reference
let performanceChart;

document.addEventListener('DOMContentLoaded', () => {
    
    // Tab Switching Logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });

    // ----------------------------------------------------
    // PREDICTOR MODE LOGIC
    // ----------------------------------------------------
    const massSlider = document.getElementById('massSlider');
    const massValue = document.getElementById('massValue');
    const predictForm = document.getElementById('prediction-form');
    
    if(massSlider) {
        massSlider.addEventListener('input', (e) => {
            massValue.textContent = parseFloat(e.target.value).toFixed(2);
        });
    }

    if(predictForm) {
        predictForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const mass = parseFloat(massSlider.value);
            const blend = document.getElementById('predBlend').value;
            const btn = document.getElementById('predictBtn');
            const btnText = btn.querySelector('.btn-text');
            const loader = btn.querySelector('.loader');
            
            btnText.style.display = 'none';
            loader.style.display = 'block';
            
            try {
                const response = await fetch('/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mass: mass, duration: 50, blend: blend })
                });
                const result = await response.json();
                if (result.success) {
                    updatePredictorDashboard(result.data);
                } else {
                    alert('Prediction Error: ' + result.error);
                }
            } catch (error) {
                console.error('Error fetching prediction:', error);
                alert('Connection to backend failed.');
            } finally {
                btnText.style.display = 'block';
                loader.style.display = 'none';
            }
        });
    }

    // ----------------------------------------------------
    // CALCULATOR MODE LOGIC
    // ----------------------------------------------------
    const calcForm = document.getElementById('calc-form');
    
    if(calcForm) {
        calcForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('calcBtn');
            const btnText = btn.querySelector('.btn-text');
            const loader = btn.querySelector('.loader');
            
            // Get inputs
            const time = document.getElementById('calcTime').value;
            const evap = document.getElementById('calcTL').value;
            const comp = document.getElementById('calcTH').value;
            const blend = document.getElementById('calcBlend').value;
            const mass = document.getElementById('calcMass').value;

            btnText.style.display = 'none';
            loader.style.display = 'block';

            try {
                const response = await fetch('/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        time: time,
                        evap_temp: evap,
                        comp_temp: comp,
                        blend: blend,
                        mass: mass
                    })
                });
                const result = await response.json();
                if (result.success) {
                    addCalcToTable(result.data);
                } else {
                    alert('Calculation Error: ' + result.error);
                }
            } catch (error) {
                console.error('Error calculating:', error);
                alert('Connection to backend failed.');
            } finally {
                btnText.style.display = 'block';
                loader.style.display = 'none';
            }
        });
    }
});

function addCalcToTable(row) {
    const tbody = document.querySelector('#calcTable tbody');
    const tr = document.createElement('tr');
    tr.style.animation = `fadeInDown 0.3s ease-out`;
    tr.innerHTML = `
        <td>${row.Blend}</td>
        <td>${row.Mass}</td>
        <td>${row.Time}</td>
        <td>${row.TL.toFixed(2)}</td>
        <td>${row.TH.toFixed(2)}</td>
        <td style="color:#3b82f6; font-weight:bold;">${row.COP.toFixed(4)}</td>
        <td>${row.Wcomp.toFixed(4)}</td>
        <td>${row.Exergy.toFixed(4)}</td>
        <td style="color:#10b981; font-weight:bold;">${row.ExergyMag.toFixed(4)}</td>
    `;
    // Insert at top
    tbody.insertBefore(tr, tbody.firstChild);
}

function updatePredictorDashboard(data) {
    if (!data || data.length === 0) return;
    
    const peakCop = Math.max(...data.map(d => d.COP)).toFixed(2);
    const minWcomp = Math.min(...data.map(d => d.Wcomp)).toFixed(2);
    const peakExergy = Math.max(...data.map(d => d.ExergyMag));
    
    animateValue("peakCop", 0, parseFloat(peakCop), 1000);
    animateValue("minWcomp", 0, parseFloat(minWcomp), 1000, '<span> kW</span>');
    animateValue("peakExergy", 0, peakExergy * 100, 1000, '<span>%</span>', (val) => val.toFixed(1));

    updateTable(data);
    updateChart(data);
}

function updateTable(data) {
    const tbody = document.querySelector('#dataTable tbody');
    tbody.innerHTML = '';
    
    data.forEach((row, index) => {
        const tr = document.createElement('tr');
        tr.style.animation = `fadeInUp 0.3s ease-out ${index * 0.05}s both`;
        
        tr.innerHTML = `
            <td>${row.Time}</td>
            <td>${row.TL}</td>
            <td>${row.TH}</td>
            <td>${row.COP.toFixed(2)}</td>
            <td>${row.Wcomp.toFixed(2)}</td>
            <td>${row.Exergy.toFixed(2)}</td>
            <td>${row.ExergyMag.toFixed(2)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updateChart(data) {
    const ctx = document.getElementById('performanceChart').getContext('2d');
    
    const labels = data.map(d => d.Time + 'm');
    const copData = data.map(d => d.COP);
    const exergyData = data.map(d => d.ExergyMag * 10); 
    
    if (performanceChart) {
        performanceChart.destroy();
    }
    
    Chart.defaults.color = 'rgba(255, 255, 255, 0.7)';
    Chart.defaults.font.family = 'Inter';
    
    performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'COP',
                    data: copData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: '|Exergy| x10',
                    data: exergyData,
                    borderColor: '#10b981',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(11, 15, 25, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#e2e8f0',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
                x: { grid: { color: 'rgba(255, 255, 255, 0.05)' } }
            }
        }
    });
}

function animateValue(id, start, end, duration, suffix = '', formatter = (val) => val.toFixed(2)) {
    const obj = document.getElementById(id);
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const currentVal = progress * (end - start) + start;
        
        obj.innerHTML = formatter(currentVal) + suffix;
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}
