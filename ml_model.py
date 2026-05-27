import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
import re
import os
import joblib
from scipy.interpolate import interp1d

class PhysicsInformedModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def parse_blend_fractions(self, blend_str):
        # R407 is approximately 23% R32, 25% R125, 52% R134a
        if 'R407' in blend_str:
            return 23.0, 25.0, 0.0, 52.0
            
        if 'R507' in blend_str:
            return 0.0, 50.0, 0.0, 0.0
            
        # Extract X/Y/Z from R32/R125/R152a (X/Y/Z)
        match = re.search(r'\((\d+)/(\d+)/(\d+)\)', blend_str)
        if match:
            return float(match.group(1)), float(match.group(2)), float(match.group(3)), 0.0
            
        return 0.0, 0.0, 0.0, 0.0

    def generate_time_features(self, df):
        df = df.copy()
        df['Time_Sq'] = df['Time'] ** 2
        df['Time_Sqrt'] = np.sqrt(df['Time'])
        df['Time_Log'] = np.log1p(df['Time'])
        return df

    def prepare_data(self):
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

        # 2. Extract given blend data from all_readings_text.txt
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

        # 3. Interpolate High-Resolution Data (1-minute intervals)
        interpolated_records = []
        for (blend, mass), group in df_raw.groupby(['Blend', 'Mass']):
            group = group.sort_values('Time').drop_duplicates('Time')
            if len(group) < 3:
                continue
            
            f_tl = interp1d(group['Time'], group['TL'], kind='cubic', fill_value="extrapolate")
            f_th = interp1d(group['Time'], group['TH'], kind='cubic', fill_value="extrapolate")
            
            # Predict up to max time available or 60 min
            max_t = int(min(60, group['Time'].max()))
            t_new = np.arange(0, max_t + 1, 1)
            
            tl_new = f_tl(t_new)
            th_new = f_th(t_new)
            
            # Extract gas fractions
            r32, r125, r152a, r134a = self.parse_blend_fractions(blend)
            
            for t, tl, th in zip(t_new, tl_new, th_new):
                # Physics constraint on interpolated data: TH must be > TL
                if th <= tl:
                    th = tl + 5.0
                interpolated_records.append({
                    'Time': t, 'Mass': mass, 'Blend': blend,
                    'R32': r32, 'R125': r125, 'R152a': r152a, 'R134a': r134a,
                    'TL': tl, 'TH': th
                })
                
        self.df_train = pd.DataFrame(interpolated_records)
        self.df_train = self.generate_time_features(self.df_train)
        return self.df_train

    def load_model(self):
        try:
            self.model = joblib.load('best_model.joblib')
            self.scaler = joblib.load('scaler.joblib')
            self.is_trained = True
            print("Production ML model and scaler loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.is_trained = False

    def calculate_physics(self, tl_k, th_k):
        # Physics constraints and calculations
        if th_k <= tl_k:
            th_k = tl_k + 5.0
            
        cop = tl_k / (th_k - tl_k)
        QL = 7.034
        wcomp = QL / cop
        
        To = 300.0
        n_exergy = QL * (1 - To / tl_k) / wcomp
        n_exergy_mag = abs(n_exergy)
        
        return cop, wcomp, n_exergy, n_exergy_mag

    def predict_trajectory(self, mass, blend, duration=60):
        if not self.is_trained:
            self.train()
            
        r32, r125, r152a, r134a = self.parse_blend_fractions(blend)
        
        times = np.arange(0, duration + 1, 1) # Per minute
        df_pred = pd.DataFrame({'Time': times})
        df_pred['Mass'] = mass
        df_pred['R32'] = r32
        df_pred['R125'] = r125
        df_pred['R152a'] = r152a
        df_pred['R134a'] = r134a
        
        df_pred = self.generate_time_features(df_pred)
        feature_cols = ['Time', 'Time_Sq', 'Time_Sqrt', 'Time_Log', 'Mass', 'R32', 'R125', 'R152a', 'R134a']
        
        X_scaled = self.scaler.transform(df_pred[feature_cols])
        preds = self.model.predict(X_scaled)
        
        results = []
        for i, t in enumerate(times):
            tl_k = float(preds[i, 0])
            th_k = float(preds[i, 1])
            
            # Apply physics calculations
            cop, wcomp, n_exergy, n_exergy_mag = self.calculate_physics(tl_k, th_k)
            
            results.append({
                'Time': int(t),
                'TL': round(tl_k - 273.15, 2), # Celsius
                'TH': round(th_k - 273.15, 2), # Celsius
                'COP': round(cop, 4),
                'Wcomp': round(wcomp, 4),
                'Exergy': round(n_exergy, 4),
                'ExergyMag': round(n_exergy_mag, 4)
            })
            
        return results

if __name__ == "__main__":
    pm = PhysicsInformedModel()
    pm.train()
    print("Test Prediction (Mass=1.5, R407, t=5):")
    res = pm.predict_trajectory(1.5, "R407", duration=5)
    print(res[-1])
