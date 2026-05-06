import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import re

# Load pdf2_text.txt
with open('pdf2_text.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# R407 Data
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

# Extract PDF data
df_list = []
blocks = re.split(r'Here, QL=.*\n1TR=.*\n', text)
for block in blocks[1:]:
    # First line usually has "R 32/ R125/ R152a of 1.7kg= 70/ 10 / 20"
    lines = block.strip().split('\n')
    header_line = lines[0]
    
    # Try to extract mass and blend
    mass_match = re.search(r'of\s*([\d\.]+)\s*kg', header_line, re.I)
    blend_match = re.search(r'=\s*(\d+\s*/\s*\d+\s*/\s*\d+)', header_line)
    
    if not mass_match or not blend_match:
        continue
        
    mass = float(mass_match.group(1))
    blend_raw = blend_match.group(1).replace(' ', '')
    blend = f"R32/R125/R152a ({blend_raw})"
    
    # Extract data lines
    # A data line starts with a number (time), then floats
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

# Train Model
print("Unique Blends Data Count:", df_all['Blend'].value_counts())

le = LabelEncoder()
df_all['Blend_Enc'] = le.fit_transform(df_all['Blend'])

X = df_all[['Time', 'Mass', 'Blend_Enc']]
y_TL = df_all['TL']
y_TH = df_all['TH']

from xgboost import XGBRegressor
rf_TL = XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42)
rf_TH = XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42)

rf_TL.fit(X, y_TL)
rf_TH.fit(X, y_TH)

score_TL = rf_TL.score(X, y_TL)
score_TH = rf_TH.score(X, y_TH)

print(f"R² for TL: {score_TL:.4f}")
print(f"R² for TH: {score_TH:.4f}")

# Example prediction
print("\nPrediction test:")
print(rf_TL.predict([[50, 1.5, le.transform(['R407'])[0]]]))
