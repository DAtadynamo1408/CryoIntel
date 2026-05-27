import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ml_model import PhysicsInformedModel
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Initialize Database
Base = declarative_base()

class PredictionLog(Base):
    __tablename__ = 'predictions'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    blend = Column(String(50))
    mass = Column(Float)
    duration = Column(Integer)
    status = Column(String(20))
    error_msg = Column(String(200))

engine = create_engine('sqlite:///prediction_logs.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# Load the production physics-informed model on boot
print("Loading Production Physics-Informed ML Model...")
pm = PhysicsInformedModel()
pm.load_model()
if pm.is_trained:
    print("Model loaded successfully.")
else:
    print("WARNING: Model failed to load. Please ensure ml_pipeline.py has been run.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    session = Session()
    try:
        content = request.json
        if not content:
            return jsonify({"success": False, "error": "No JSON body provided"}), 400
            
        mass = float(content.get('mass', 1.5))
        duration = int(content.get('duration', 50))
        blend = content.get('blend', 'R407')
        
        # Log request
        log = PredictionLog(blend=blend, mass=mass, duration=duration, status='PENDING')
        session.add(log)
        session.commit()
        
        # Make predictions
        predictions = pm.predict_trajectory(mass, blend, duration=duration)
        
        log.status = 'SUCCESS'
        session.commit()
        
        return jsonify({"success": True, "data": predictions})
    except Exception as e:
        print("Exception at prediction API: ", e)
        if 'log' in locals():
            log.status = 'ERROR'
            log.error_msg = str(e)[:200]
            session.commit()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        session.close()

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        content = request.json
        time = float(content.get('time', 0))
        tl_k = float(content.get('evap_temp', 300.15)) 
        th_k = float(content.get('comp_temp', 343.15)) 
        blend = content.get('blend', 'R32/R125/R152a')
        mass = float(content.get('mass', 1.5))
        
        if th_k <= tl_k:
            return jsonify({"success": False, "error": "Compressor Temp must be strictly greater than Evaporator Temp"}), 400
            
        cop, wcomp, n_exergy, n_exergy_mag = pm.calculate_physics(tl_k, th_k)
        
        result = {
            'Time': time,
            'Blend': blend,
            'Mass': mass,
            'TL': round(tl_k, 2),
            'TH': round(th_k, 2),
            'COP': round(cop, 4),
            'Wcomp': round(wcomp, 4),
            'Exergy': round(n_exergy, 4),
            'ExergyMag': round(n_exergy_mag, 4)
        }
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # When run directly, we use waitress for production
    from waitress import serve
    print("Starting Waitress production server on port 5000...")
    serve(app, host='0.0.0.0', port=5000)
