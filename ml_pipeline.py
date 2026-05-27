import pandas as pd
import numpy as np
import re
import os
import joblib
from scipy.interpolate import interp1d
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor
import warnings
warnings.filterwarnings('ignore')

print("Starting Production ML Pipeline...")

def parse_blend_fractions(blend_str):
    if 'R407' in blend_str:
        return 23.0, 25.0, 0.0, 52.0
    if 'R507' in blend_str:
        return 0.0, 50.0, 0.0, 0.0
    match = re.search(r'\((\d+)/(\d+)/(\d+)\)', blend_str)
    if match:
        return float(match.group(1)), float(match.group(2)), float(match.group(3)), 0.0
    return 0.0, 0.0, 0.0, 0.0

def generate_time_features(df):
    df = df.copy()
    df['Time_Sq'] = df['Time'] ** 2
    df['Time_Sqrt'] = np.sqrt(df['Time'])
    df['Time_Log'] = np.log1p(df['Time'])
    return df

# 1. Prepare Data
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

df_list = []
if os.path.exists('all_readings_text.txt'):
    with open('all_readings_text.txt', 'r', encoding='utf-8') as f:
        text = f.read()
        
    blocks = re.split(r'Dated:\s*\d+/\d+/\d+', text)
    current_base = None
    if len(blocks) > 0 and 'BASE-R507' in blocks[0]:
        current_base = 'BASE-R507'
        
    for block in blocks[1:]:
        if 'BASE-R507' in block:
            current_base = 'BASE-R507'
        
        mass_match = re.search(r'of\s*([\d\.]+)\s*kg', block, re.I) or re.search(r'([\d\.]+)\s*KG', block, re.I)
        blend_match = re.search(r'=\s*(\d+\s*/\s*\d+\s*/\s*\d+)', block)
        
        if not mass_match:
            continue
        mass = float(mass_match.group(1))
        
        if blend_match:
            blend_raw = blend_match.group(1).replace(' ', '')
            blend = f"R32/R125/R152a ({blend_raw})"
        elif current_base == 'BASE-R507' or 'BASE-R507' in block:
            blend = "R507"
        else:
            continue
        
        for line in block.strip().split('\n'):
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
df_raw = pd.concat([df_r407, df_pdf], ignore_index=True)

interpolated_records = []
for (blend, mass), group in df_raw.groupby(['Blend', 'Mass']):
    group = group.sort_values('Time').drop_duplicates('Time')
    if len(group) < 3:
        continue
    f_tl = interp1d(group['Time'], group['TL'], kind='cubic', fill_value="extrapolate")
    f_th = interp1d(group['Time'], group['TH'], kind='cubic', fill_value="extrapolate")
    max_t = int(min(60, group['Time'].max()))
    t_new = np.arange(0, max_t + 1, 1)
    tl_new = f_tl(t_new)
    th_new = f_th(t_new)
    r32, r125, r152a, r134a = parse_blend_fractions(blend)
    for t, tl, th in zip(t_new, tl_new, th_new):
        if th <= tl: th = tl + 5.0
        interpolated_records.append({
            'Time': t, 'Mass': mass, 'Blend': blend,
            'R32': r32, 'R125': r125, 'R152a': r152a, 'R134a': r134a,
            'TL': tl, 'TH': th
        })
        
df_train = pd.DataFrame(interpolated_records)
df_train = generate_time_features(df_train)

feature_cols = ['Time', 'Time_Sq', 'Time_Sqrt', 'Time_Log', 'Mass', 'R32', 'R125', 'R152a', 'R134a']
X = df_train[feature_cols]
y = df_train[['TL', 'TH']]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.15, random_state=42)

print("\n--- Tuning Models ---")
# 1. XGBoost
xgb_params = {
    'estimator__n_estimators': [200, 500],
    'estimator__learning_rate': [0.03, 0.05],
    'estimator__max_depth': [5, 7]
}
xgb_model = MultiOutputRegressor(XGBRegressor(random_state=42))
xgb_grid = GridSearchCV(xgb_model, xgb_params, cv=3, scoring='neg_mean_squared_error', n_jobs=-1)
print("Evaluating XGBoost...")
xgb_grid.fit(X_train, y_train)

# 2. Random Forest
rf_params = {
    'estimator__n_estimators': [200, 500],
    'estimator__max_depth': [10, 15]
}
rf_model = MultiOutputRegressor(RandomForestRegressor(random_state=42))
rf_grid = GridSearchCV(rf_model, rf_params, cv=3, scoring='neg_mean_squared_error', n_jobs=-1)
print("Evaluating RandomForest...")
rf_grid.fit(X_train, y_train)

xgb_score = -xgb_grid.best_score_
rf_score = -rf_grid.best_score_
print(f"\nXGBoost Best MSE: {xgb_score:.4f}")
print(f"RandomForest Best MSE: {rf_score:.4f}")

if xgb_score < rf_score:
    print("Winner: XGBoost")
    best_model = xgb_grid.best_estimator_
else:
    print("Winner: RandomForest")
    best_model = rf_grid.best_estimator_

# Final Retrain on full data
best_model.fit(X_scaled, y)
preds = best_model.predict(X_scaled)
mse_tl = np.mean((y['TL'] - preds[:, 0])**2)
mse_th = np.mean((y['TH'] - preds[:, 1])**2)
print(f"Final Model MSE TL: {mse_tl:.4f}, MSE TH: {mse_th:.4f}")

# Save artifacts
joblib.dump(best_model, 'best_model.joblib')
joblib.dump(scaler, 'scaler.joblib')
print("\nPipeline Complete. Model and Scaler saved to disk.")
