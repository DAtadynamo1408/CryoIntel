# ❄️ AI/ML-Based Refrigerant Performance Prediction

> **Physics-Informed Machine Learning** for predicting thermodynamic performance of refrigerants (R-407C, R-32, R-134a, R-507 blends) in vapor-compression refrigeration systems.

---

## 🌐 Live Dashboard Preview

| Dashboard | URL (after running) | Description |
|---|---|---|
| 🧮 **CryoIntel Web App + Calculator** | `http://localhost:5000` | Full thermodynamic calculator + ML predictions |
| ❄️ **Streamlit Analytics Dashboard** | `http://localhost:8501` | Interactive charts, trajectory plots, data tables |

---

## 🧠 What This Project Does

This project builds a **physics-informed XGBoost ML model** trained on real experimental refrigeration data extracted from research PDFs. It can:

- ✅ **Predict** temperature trajectories (TL and TH) over a 0–60 minute window
- ✅ **Calculate** COP (Coefficient of Performance), Compressor Work, and Exergy Efficiency
- ✅ **Compare** different refrigerant blends and charge masses
- ✅ **Visualize** results in an interactive web dashboard
- ✅ **Log** all predictions to a SQLite database

---

## 📁 Project Structure

```
refrigeration_prediction/
│
├── server.py               # Flask backend (Web App + Calculator API)
├── streamlit_app.py        # Streamlit interactive dashboard
├── ml_model.py             # Core PhysicsInformedModel class (predict + calculate)
├── ml_pipeline.py          # Full training pipeline (runs GridSearchCV)
│
├── best_model.joblib       # Pre-trained XGBoost model (ready to use)
├── scaler.joblib           # StandardScaler for feature normalization
│
├── all_readings_text.txt   # Extracted experimental data (training source)
├── extracted_readings.csv  # Structured CSV of all experimental readings
│
├── templates/
│   └── index.html          # Frontend HTML for the web app
├── static/
│   ├── style.css           # CSS styling
│   └── app.js              # JavaScript for charts and API calls
│
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## ⚙️ Requirements

- **Python 3.9 or higher**
- **pip** (Python package manager)
- Internet connection (only for first-time package install)

---

## 🚀 Quick Start (Step-by-Step)

### Step 1 — Clone or Download the Project

**Option A: Clone with Git**
```bash
git clone https://github.com/aryansanyal08/aryan.git
cd aryan
```

**Option B: Download ZIP**
- Click the green **"Code"** button on GitHub → **"Download ZIP"**
- Extract the ZIP folder on your computer
- Open a terminal and navigate to the extracted folder:
```bash
cd path/to/refrigeration_prediction
```

---

### Step 2 — Install All Dependencies

Run this single command to install everything needed:

```bash
pip install -r requirements.txt
```

Also install the web dashboard libraries:
```bash
pip install streamlit plotly flask-cors sqlalchemy
```

> ⚠️ **Note:** If you get a permission error, try: `pip install --user -r requirements.txt`

---

### Step 3 — Launch the Web App (Calculator + Predictions)

```bash
python server.py
```

Then open your browser and go to: **http://localhost:5000**

---

### Step 4 — Launch the Streamlit Dashboard (Optional)

Open a **new terminal window** (keep server.py running) and run:

```bash
streamlit run streamlit_app.py
```

Then open your browser and go to: **http://localhost:8501**

---

## 🔁 Retrain the Model (Optional)

If you want to retrain the model on new data, run:

```bash
python ml_pipeline.py
```

This will:
1. Load and parse `all_readings_text.txt`
2. Interpolate data to 1-minute intervals
3. Train both **XGBoost** and **Random Forest** models using GridSearchCV
4. Automatically select the best model
5. Save `best_model.joblib` and `scaler.joblib` to disk

> ⏱️ Training takes approximately **1–3 minutes** depending on your hardware.

---

## 🧮 API Reference

The Flask server exposes these REST API endpoints:

### `POST /predict`
Predict temperature and performance over time.

**Request Body:**
```json
{
  "mass": 1.5,
  "blend": "R407",
  "duration": 60
}
```

**Response:**
```json
{
  "success": true,
  "data": [
    { "Time": 0, "TL": 36.0, "TH": 58.0, "COP": 8.72, "Wcomp": 0.81, "Exergy": -0.15 },
    ...
  ]
}
```

### `POST /calculate`
Directly calculate thermodynamic values from given temperatures.

**Request Body:**
```json
{
  "evap_temp": 273.15,
  "comp_temp": 333.15,
  "blend": "R407",
  "mass": 1.5
}
```

---

## 📊 Supported Refrigerant Blends

| Blend | Description |
|---|---|
| `R407` | R-407C (R32/R125/R134a — 23/25/52) |
| `R507` | R-507A (R125/R143a — 50/50) |
| `R32/R125/R152a (70/10/20)` | Custom ternary blend |
| `R32/R125/R152a (20/10/70)` | Custom ternary blend |
| `R32/R125/R152a (30/10/60)` | Custom ternary blend |
| `R32/R125/R152a (15/15/70)` | Custom ternary blend |

---

## 🔬 Physics & Thermodynamics

The model enforces real thermodynamic constraints:

| Parameter | Formula |
|---|---|
| **COP** | $COP = T_L / (T_H - T_L)$ |
| **Compressor Work** | $W_{comp} = Q_L / COP$ where $Q_L = 7.034\,kW$ |
| **Exergy Efficiency** | $\eta_{ex} = Q_L (1 - T_0/T_L) / W_{comp}$ |
| **Constraint** | $T_H > T_L$ always enforced |

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Run `pip install flask flask-cors` |
| `ModuleNotFoundError: No module named 'xgboost'` | Run `pip install xgboost` |
| `Port 5000 already in use` | Run `netstat -ano \| findstr :5000` then kill the process |
| `Port 8501 already in use` | Run `streamlit run streamlit_app.py --server.port 8502` |
| Model not loading error | Run `python ml_pipeline.py` to retrain and generate model files |
| Website not opening | Make sure `server.py` is still running in the terminal |

---

## 📚 Research Background

This project is based on the thesis:

> **"AI/ML-Based Predictive Modeling of Refrigerant Performance"**
> Aryan (Roll No: 21054003)
> Integrated Dual Degree (B.Tech. + M.Tech.) in Industrial Chemistry
> **IIT (BHU) Varanasi, 2026**
> Supervisor: Dr. Yogesh Chandra Sharma

---

## 📄 License

This project is for academic and research purposes. All rights reserved by the author and IIT (BHU) Varanasi.

---

## 📬 Contact

For questions, raise an issue on GitHub or contact via the IIT (BHU) Department of Chemistry.
