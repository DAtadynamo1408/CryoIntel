from flask import Flask, request, jsonify, render_template
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import re
import os

app = Flask(__name__)

# Train ML Models on Boot
# 1. Provide original R407 data
r407_data = [
    (0, 1.5, 36+273.15, 33+273.15), (5, 1.5, 26+273.15, 59+273.15), (10, 1.5, 22+273.15, 60+273.15), (15, 1.5, 19+273.15, 59+273.15), 
    (20, 1.5, 16+273.15, 59+273.15), (25, 1.5, 13+273.15, 59+273.15), (30, 1.5, 11+273.15, 58+273.15), (35, 1.5, 9+273.15, 56+273.15), 
    (40, 1.5, 7+273.15, 57+273.15), (45, 1.5, 5+273.15, 55+273.15),
    (0, 1.6, 33+273.15, 34+273.15), (5, 1.6, 25+273.15, 56+273.15), (10, 1.6, 21+273.15, 58+273.15), (15, 1.6, 21+273.15, 58+273.15), 
    (20, 1.6, 14+273.15, 58+273.15), (25, 1.6, 12+273.15, 58+273.15), (30, 1.6, 8+273.15, 57+273.15), (35, 1.6, 7+273.15, 55+273.15), 
    (40, 1.6, 5+273.15, 56+273.15), (45, 1.6, 3+273.15, 56+273.15),
    (0, 1.75, 30+273.15, 56+273.15), (5, 1.75, 24+273.15, 53+273.15), (10, 1.75, 20+273.15, 61+273.15), (15, 1.75, 16+273.15, 60+273.15), 
    (20, 1.75, 15+273.15, 59+273.15), (25, 1.75, 10+273.15, 58+273.15), (30, 1.75, 8+273.15, 57+273.15), (35, 1.75, 4+273.15, 56+273.15), 
    (40, 1.75, 3+273.15, 56+273.15),
    (0, 1.8, 35+273.15, 43+273.15), (5, 1.8, 24+273.15, 58+273.15), (10, 1.8, 19+273.15, 59+273.15), (15, 1.8, 17+273.15, 59+273.15), 
    (20, 1.8, 13+273.15, 59+273.15), (25, 1.8, 10+273.15, 58+273.15), (30, 1.8, 7+273.15, 57+273.15), (35, 1.8, 5+273.15, 57+273.15), 
    (40, 1.8, 3+273.15, 57+273.15)
]
df_r407 = pd.DataFrame(r407_data, columns=['Time', 'Mass', 'TL', 'TH'])
df_r407['Blend'] = 'R407'

# 2. Extract given blend data from pdf2_text.txt
df_list = []
if os.path.exists('pdf2_text.txt'):
    with open('pdf2_text.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    blocks = re.split(r'Here, QL=.*\n1TR=.*\n', text)
    for block in blocks[1:]:
        lines = block.strip().split('\n')
        header_line = lines[0]
        
        mass_match = re.search(r'of\s*([\d\.]+)\s*kg', header_line, re.I)
        blend_match = re.search(r'=\s*(\d+\s*/\s*\d+\s*/\s*\d+)', header_line)
        
        if not mass_match or not blend_match:
            continue
            
        mass = float(mass_match.group(1))
        blend_raw = blend_match.group(1).replace(' ', '')
        blend = f"R32/R125/R152a ({blend_raw})"
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 7:
                try:
                    time = float(parts[0])
                    tl = float(parts[1])
                    th = float(parts[2])
                    df_list.append({'Time': time, 'Mass': mass, 'TL': tl, 'TH': th, 'Blend': blend})
                except ValueError:
                    pass

df_pdf = pd.DataFrame(df_list)
df_all = pd.concat([df_r407, df_pdf], ignore_index=True)

print(f"Data parsed successfully: {len(df_all)} data rows.")

# 3. Fit ML Model
from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor

le = LabelEncoder()
df_all['Blend_Enc'] = le.fit_transform(df_all['Blend'])

X = df_all[['Time', 'Mass', 'Blend_Enc']]
y_TL = df_all['TL']
y_TH = df_all['TH']

rf_TL = XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42)
rf_TH = XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42)

rf_TL.fit(X, y_TL)
rf_TH.fit(X, y_TH)

print(f"Server Ready: XGBoost Trained. TL Accuracy: {rf_TL.score(X, y_TL):.4f}, TH Accuracy: {rf_TH.score(X, y_TH):.4f}")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        content = request.json
        mass = float(content.get('mass', 1.5))
        duration = int(content.get('duration', 50))
        blend = content.get('blend', 'R407')
        
        # Handle unseen blends explicitly just in case
        if blend not in le.classes_:
            print(f"Warning: unknown blend {blend}, falling back to default.")
            blend_enc = le.transform([le.classes_[0]])[0]
        else:
            blend_enc = le.transform([blend])[0]

        predictions = []
        for time_step in range(0, duration + 1, 5):
            features = np.array([[time_step, mass, blend_enc]])
            
            # Predict
            pred_tl_k = rf_TL.predict(features)[0]
            pred_th_k = rf_TH.predict(features)[0]
            
            # Constraints
            if pred_th_k <= pred_tl_k:
                pred_th_k = pred_tl_k + 5 

            # Efficiencies Calculations
            cop = (pred_tl_k / (pred_th_k - pred_tl_k)) / 2
            QL = 7.034
            wcomp = (QL / cop) * 2
            
            To = 300.0
            n_exergy = QL * (1 - To / pred_tl_k) / wcomp
            n_exergy_mag = abs(n_exergy)

            # Outputs array requires display format
            # Using celsius for trajectory readability if needed or matched to PDF format.
            # But the PDF outputs match Kelvin format. Our chart previously used Celsius for UI readability.
            # Convert to C:
            pred_tl_c = pred_tl_k - 273.15
            pred_th_c = pred_th_k - 273.15
            
            predictions.append({
                'Time': time_step,
                'TL': round(pred_tl_c, 2),
                'TH': round(pred_th_c, 2),
                'COP': round(cop, 4),
                'Wcomp': round(wcomp, 4),
                'Exergy': round(n_exergy, 4),
                'ExergyMag': round(n_exergy_mag, 4)
            })
            
        return jsonify({"success": True, "data": predictions})
    except Exception as e:
        print("Exception exactly at prediction API: ", e)
        return jsonify({"success": False, "error": str(e)})

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        content = request.json
        time = float(content.get('time', 0))
        tl_k = float(content.get('evap_temp', 300.15)) 
        th_k = float(content.get('comp_temp', 343.15)) 
        blend = content.get('blend', 'R32/R125/R152a')
        mass = float(content.get('mass', 1.5))
        
        QL = 7.034
        To = 300.0
        
        if th_k <= tl_k:
            return jsonify({"success": False, "error": "Compressor Temp must be strictly greater than Evaporator Temp"})
            
        cop = (tl_k / (th_k - tl_k)) / 2
        wcomp = (QL / cop) * 2
        n_exergy = QL * (1 - To / tl_k) / wcomp
        n_exergy_mag = abs(n_exergy)
        
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
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
