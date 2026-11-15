import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.special import erf

# Fits a single knife-edge scan (HeNe laser) to extract beam waist radius w0
# Reconstructs transverse beam intensity profile by differentiating transmitted power (dP/dx)

# load run data: displacement x (um) and background-subtracted voltage y (mV)
df = pd.read_csv("/Users/hongorchamdaa/Desktop/BeamWaistProject/BeamWaistData/beamscan_run_033.csv")
x = df["Rel_Pos_um"].values
y = df["Corrected_mV"].values

# outlier rejection: remove single-sample voltage spikes > 3 sigma from 15-pt rolling median
y_series = pd.Series(y)
median = y_series.rolling(window=15, center=True).median().bfill().ffill()
diff = np.abs(y_series - median)
mask = diff < (3 * diff.std())
x_clean = x[mask]
y_clean = y[mask]

# moving-average smoothing to reduce ADC quantization noise before taking numerical derivative
WINDOW_SIZE = 100
y_smooth = pd.Series(y_clean).rolling(window=WINDOW_SIZE, center=True).mean().bfill().ffill().values

# knife-edge power transmission model (falling edge): P(x) = y0 + (P0/2) * [1 - erf(sqrt(2)*(x-x0)/w0)]
def erf_model(x, y0, P0, x0, w0):
    return y0 + (P0 / 2.0) * (1.0 - erf(np.sqrt(2) * (x - x0) / w0))

# parameter initial guesses: baseline at minimum, total power from range, center at 50% power
y0_guess = np.min(y_clean)
P0_guess = np.max(y_clean) - np.min(y_clean)
mid_val = y0_guess + P0_guess / 2.0
x0_guess = x_clean[np.argmin(np.abs(y_clean - mid_val))]
w0_guess = (np.max(x_clean) - np.min(x_clean)) / 5.0 # initial beam width guess ~ 20% of scan range
p0 = [y0_guess, P0_guess, x0_guess, w0_guess]

# fit transmission curve and evaluate fitted model
popt, pcov = curve_fit(erf_model, x_clean, y_clean, p0=p0)
y0_fit, P0_fit, x0_fit, w0_fit = popt
y_erf_fit = erf_model(x_clean, *popt)

# compute derivatives (dP/dx): recovers 1D transverse intensity profile of the laser beam
dI_raw = np.gradient(y_clean, x_clean)
dI_smooth = np.gradient(y_smooth, x_clean)

# analytical derivative of the error function model for comparison
def erf_derivative(x, P0, x0, w0):
    return -np.sqrt(2 / np.pi) * (P0 / w0) * np.exp(-2 * ((x - x0) ** 2) / (w0**2))

dI_erf_fit = erf_derivative(x_clean, P0_fit, x0_fit, w0_fit)

perr = np.sqrt(np.diag(pcov))
print(f"Beam Center (x0): {x0_fit:.2f} ± {perr[2]:.2f} µm")
print(f"Beam Waist  (w0): {w0_fit:.2f} ± {perr[3]:.2f} µm")

# baseline vertical offset shift for display
offset_clean = np.max(y_clean) - np.min(y_clean)
offset_smooth = np.max(y_smooth) - np.min(y_smooth)
offset_erf_fit = np.max(y_erf_fit) - np.min(y_erf_fit)
y_clean = y_clean + offset_clean
y_smooth = y_smooth + offset_smooth
y_erf_fit = y_erf_fit + offset_erf_fit

# dual-panel plot: power S-curve (top) and derivative intensity profile (bottom)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# top panel: transmission data and fitted erf S-curve
ax1.plot(x_clean, y_clean, "k.", alpha=0.35, markersize=3, label="Raw Data (3σ clipped)")
ax1.plot(x_clean, y_smooth, color="green", lw=1.8, label=f"Smoothed ({WINDOW_SIZE}-pt MA)")
ax1.plot(x_clean, y_erf_fit, "r-", lw=2.5, label=f"ERFC Fit (w0 = {w0_fit:.2f} µm)")
ax1.set_xlabel("Displacement [µm]")
ax1.set_ylabel("Power Meter Signal [mV]")
ax1.set_title("Knife-Edge Profile Analysis")
ax1.legend(loc="upper right")
ax1.grid(True, linestyle="--", alpha=0.5)

# bottom panel: numerical and analytical derivatives showing beam intensity profile
ax2.plot(x_clean, dI_raw, color="gray", alpha=0.35, lw=0.8, label="Raw Derivative")
ax2.plot(x_clean, np.abs(dI_smooth * 1000), color="green", lw=0.8, alpha=0.85, label="Smoothed Derivative")
ax2.plot(x_clean, np.abs(dI_erf_fit * 1000), "r--", lw=2.5, label="ERFC Fit Derivative")
ax2.set_xlabel("Displacement [µm]")
ax2.set_ylabel("Intensity dP/dx [mV/µm]")
ax2.legend(loc="upper right")
ax2.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.show()
