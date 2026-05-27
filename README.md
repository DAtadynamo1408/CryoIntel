# CryoIntel - Refrigeration Intelligence Platform

CryoIntel is a production-ready, physics-informed machine learning application that predicts the performance metrics of refrigeration systems (COP, Compressor Work, Exergy Efficiency) over time across various refrigerant blends and masses.

## Architecture
- **Frontend**: Responsive UI built with HTML/CSS (Glassmorphism design) and Chart.js for real-time visualization.
- **Backend**: Python Flask API running on `waitress` (Production WSGI Server).
- **Database**: SQLite (`prediction_logs.db`) for logging and auditing all inference requests.
- **ML Pipeline**: Automated model training comparing XGBoost and RandomForest, utilizing GridSearch for hyperparameter optimization (`ml_pipeline.py`).
- **Hosting**: Cloudflare Tunnel for secure, rapid live public deployment.

## Key Files
- `ml_pipeline.py`: Runs automated data extraction, feature engineering, and hyperparameter tuning. Saves `best_model.joblib`.
- `ml_model.py`: The `PhysicsInformedModel` class that loads the trained model and performs strict thermodynamic calculations (e.g., $Exergy = Q_L(1 - T_o/T_L)/W_{comp}$).
- `server.py`: The main API server with SQLite integration.
- `start_prod.ps1`: Launch script for full deployment.

## Physics Integration
The machine learning model handles the highly non-linear interpolation of Time, Mass, and Blend ratios to predict Evaporator (TL) and Compressor (TH) temperatures.
The physics engine then ensures:
1. $TH > TL$ is strictly enforced.
2. The exact definitions from the provided scientific literature are applied:
   - $COP = T_L / (T_H - T_L)$
   - $W_{comp} = Q_L / COP$
   - $Exergy = Q_L(1 - T_o/T_L) / W_{comp}$ (where $T_o = 304.15 K$)

## API Endpoints
- `POST /predict`: Generate a performance forecast trajectory.
- `POST /calculate`: Perform a point-in-time calculation bypassing the ML time-series.

## Setup & Deployment
1. Ensure dependencies are installed: `pip install -r requirements.txt waitress flask-cors sqlalchemy`
2. Run the ML pipeline (only needed once or when new data is added): `python ml_pipeline.py`
3. Launch the platform: `./start_prod.ps1`
4. Access the generated `.trycloudflare.com` URL.
