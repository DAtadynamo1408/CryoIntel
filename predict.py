import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

# Data: Time, Mass, TL, TH
data = [
    (0, 1.5, 36, 33), (5, 1.5, 26, 59), (10, 1.5, 22, 60), (15, 1.5, 19, 59), 
    (20, 1.5, 16, 59), (25, 1.5, 13, 59), (30, 1.5, 11, 58), (35, 1.5, 9, 56), 
    (40, 1.5, 7, 57), (45, 1.5, 5, 55),
    (0, 1.6, 33, 34), (5, 1.6, 25, 56), (10, 1.6, 21, 58), (15, 1.6, 21, 58), 
    (20, 1.6, 14, 58), (25, 1.6, 12, 58), (30, 1.6, 8, 57), (35, 1.6, 7, 55), 
    (40, 1.6, 5, 56), (45, 1.6, 3, 56),
    (0, 1.75, 30, 56), (5, 1.75, 24, 53), (10, 1.75, 20, 61), (15, 1.75, 16, 60), 
    (20, 1.75, 15, 59), (25, 1.75, 10, 58), (30, 1.75, 8, 57), (35, 1.75, 4, 56), 
    (40, 1.75, 3, 56),
    (0, 1.8, 35, 43), (5, 1.8, 24, 58), (10, 1.8, 19, 59), (15, 1.8, 17, 59), 
    (20, 1.8, 13, 59), (25, 1.8, 10, 58), (30, 1.8, 7, 57), (35, 1.8, 5, 57), 
    (40, 1.8, 3, 57)
]

df = pd.DataFrame(data, columns=['Time', 'Mass', 'TL', 'TH'])

# We only predict for t >= 5. The starting point t=0 has anomalous TH (compressor not fully running).
# We exclude t=0 for better trend line in TH and TL
df_train = df[df['Time'] > 0]

X = df_train[['Time', 'Mass']]
y_TL = df_train['TL']
y_TH = df_train['TH']

# Polynomial regression (degree 2)
poly = PolynomialFeatures(degree=2)
X_poly = poly.fit_transform(X)

model_TL = LinearRegression().fit(X_poly, y_TL)
model_TH = LinearRegression().fit(X_poly, y_TH)

# Predict next 10 values for Mass = 1.5 kg, from Time = 50 to 95
next_times = np.arange(50, 100, 5)
X_pred = pd.DataFrame({'Time': next_times, 'Mass': 1.5})
X_pred_poly = poly.transform(X_pred)

TL_pred = model_TL.predict(X_pred_poly)
TH_pred = model_TH.predict(X_pred_poly)

# Calculations
QL = 7.034
To = 300

results = []
for t, tl, th in zip(next_times, TL_pred, TH_pred):
    # Enforce constraints just in case regression extrapolates weirdly
    if th <= tl:
        th = tl + 5
    
    tl_k = tl + 273.15
    th_k = th + 273.15
    
    cop = (tl_k / (th_k - tl_k)) / 2
    wcomp = (QL / cop) * 2
    n_exergy = QL * (1 - To / tl_k) / wcomp
    n_exergy_mag = abs(n_exergy)
    
    results.append({
        'Time': int(t),
        'TL (C)': round(tl, 2),
        'TH (C)': round(th, 2),
        'COP': round(cop, 4),
        'Wcomp (kW)': round(wcomp, 4),
        'n_exergy': round(n_exergy, 4),
        '|n_exergy|': round(n_exergy_mag, 4)
    })

res_df = pd.DataFrame(results)

print("| Time | TL (C) | TH (C) | COP | Wcomp (kW) | n_exergy | |n_exergy| |")
print("|------|---------|---------|-----|------------|----------|------------|")
for idx, row in res_df.iterrows():
    print(f"| {int(row['Time'])} | {row['TL (C)']} | {row['TH (C)']} | {row['COP']} | {row['Wcomp (kW)']} | {row['n_exergy']} | {row['|n_exergy|']} |")
