"""Validate ML predictions against PDF reference data."""
from ml_model import PhysicsInformedModel

pm = PhysicsInformedModel()
pm.load_model()

# PDF Reference: 70/10/20 blend, 1.5kg
# t=0:  TL=300.15K(27C) TH=343.15K(70C) COP=6.9802 Wcomp=1.0077 Exergy=-0.0930
# t=5:  TL=296.15K(23C) TH=350.15K(77C) COP=5.4843 Wcomp=1.2826 Exergy=-0.1481
# t=10: TL=292.15K(19C) TH=354.15K(81C) COP=4.7121 Wcomp=1.4928 Exergy=-0.1935

print("=" * 80)
print("VALIDATION: ML Predictions vs PDF Reference Data")
print("=" * 80)

# Test 1: 70/10/20 blend, 1.5kg
print("\n--- Blend: 70/10/20, Mass: 1.5 kg ---")
r = pm.predict_trajectory(1.5, "R32/R125/R152a (70/10/20)", duration=10)

pdf_ref = {
    0:  {"TL": 27.0,  "TH": 70.0,  "COP": 6.9802, "Wcomp": 1.0077, "ExergyMag": 0.0930},
    5:  {"TL": 23.0,  "TH": 77.0,  "COP": 5.4843, "Wcomp": 1.2826, "ExergyMag": 0.1481},
    10: {"TL": 19.0,  "TH": 81.0,  "COP": 4.7121, "Wcomp": 1.4928, "ExergyMag": 0.1935},
}

print(f"{'Time':>5} | {'TL_pred':>8} {'TL_ref':>8} {'TL_err%':>8} | {'TH_pred':>8} {'TH_ref':>8} {'TH_err%':>8} | {'COP_pred':>9} {'COP_ref':>9} {'COP_err%':>9} | {'Wcomp_pred':>10} {'Wcomp_ref':>10}")
for d in r:
    t = d["Time"]
    if t in pdf_ref:
        ref = pdf_ref[t]
        tl_err = abs(d["TL"] - ref["TL"]) / max(abs(ref["TL"]), 0.01) * 100
        th_err = abs(d["TH"] - ref["TH"]) / max(abs(ref["TH"]), 0.01) * 100
        cop_err = abs(d["COP"] - ref["COP"]) / ref["COP"] * 100
        print(f"{t:>5} | {d['TL']:>8.2f} {ref['TL']:>8.2f} {tl_err:>7.2f}% | {d['TH']:>8.2f} {ref['TH']:>8.2f} {th_err:>7.2f}% | {d['COP']:>9.4f} {ref['COP']:>9.4f} {cop_err:>8.2f}% | {d['Wcomp']:>10.4f} {ref['Wcomp']:>10.4f}")

# Test 2: Manual physics calculation check
print("\n--- Manual Physics Verification ---")
print("Formula: COP = TL / (TH - TL),  Wcomp = QL / COP,  Exergy = QL*(1 - To/TL)/Wcomp")
tl_k, th_k = 300.15, 343.15
cop = tl_k / (th_k - tl_k)
ql = 7.034
wcomp = ql / cop
to = 304.15
exergy = ql * (1 - to / tl_k) / wcomp
print(f"TL=300.15K, TH=343.15K => COP={cop:.10f}, Wcomp={wcomp:.10f}, Exergy={exergy:.10f}")
print(f"PDF Reference:           => COP=6.9802325580, Wcomp=1.0077028150, Exergy=-0.0930232560")
print(f"Match: COP={'YES' if abs(cop - 6.980232558) < 0.001 else 'NO'}, Wcomp={'YES' if abs(wcomp - 1.007702815) < 0.001 else 'NO'}, Exergy={'YES' if abs(exergy - (-0.093023256)) < 0.001 else 'NO'}")

# Test 3: 20/10/70 blend, 1.5kg
print("\n--- Blend: 20/10/70, Mass: 1.5 kg ---")
r2 = pm.predict_trajectory(1.5, "R32/R125/R152a (20/10/70)", duration=10)
pdf_ref2 = {
    0:  {"TL": 25.0,  "TH": 52.0,  "COP": 11.0426},
    5:  {"TL": 17.0,  "TH": 58.0,  "COP": 7.0768},
    10: {"TL": 13.0,  "TH": 57.0,  "COP": 6.5034},
}
for d in r2:
    t = d["Time"]
    if t in pdf_ref2:
        ref = pdf_ref2[t]
        cop_err = abs(d["COP"] - ref["COP"]) / ref["COP"] * 100
        print(f"t={t:>2}: Pred TL={d['TL']:>6.2f} TH={d['TH']:>6.2f} COP={d['COP']:>8.4f} | Ref TL={ref['TL']:>6.2f} TH={ref['TH']:>6.2f} COP={ref['COP']:>8.4f} | COP err={cop_err:.2f}%")

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)
