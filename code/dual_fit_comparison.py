import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.special import erf
from pathlib import Path

# Compares beam radius w extracted by two independent methods across all runs:
#   Method A: direct fit of complementary error function (erfc) to transmitted power S-curve
#   Method B: Gaussian fit to numerical derivative dP/dx (intensity profile) with adaptive smoothing

# run number to optical rail position z (mm) mapping
HENE_RUNS = {26: 558, 27: 553, 28: 548, 35: 545, 36: 544, 29: 543, 37: 542, 33: 540, 30: 538, 31: 533, 32: 528}
DIODE_RUNS = {14: 350, 15: 345, 16: 340, 17: 335, 22: 334, 24: 333, 23: 332, 25: 331, 18: 330, 19: 325, 20: 320, 21: 315}

DATA_DIR = Path("/Users/hongorchamdaa/Desktop/BeamWaistProject/BeamWaistData")
WINDOW_OUTLIER = 15     # window size for rolling-median outlier rejection
SIGMA_OUTLIER = 3       # threshold (multiples of residual std) to flag spike outliers
WINDOW_FIXED = 100      # fixed 100-point moving average window for baseline comparison
ADAPTIVE_FRACTION = 0.25 # adaptive window set to 25% of beam transition width (w_A / step)
MIN_WINDOW = 5          # minimum allowed window size in points

# analytical models for knife-edge transmission: power P(x) = y0 + (P0/2) * [1 +/- erf(sqrt(2)*(x-x0)/w)]
def erfc_model(x, y0, P0, x0, w):
    return y0 + (P0 / 2.0) * (1.0 - erf(np.sqrt(2) * (x - x0) / w))

def erfc_model_rising(x, y0, P0, x0, w):
    return y0 + (P0 / 2.0) * (1.0 + erf(np.sqrt(2) * (x - x0) / w))

# standard Gaussian model for derivative peak: w = 2*sigma
def gaussian_model(x, A, x0, sigma, offset):
    return A * np.exp(-0.5 * ((x - x0) / sigma) ** 2) + offset

def fit_run(run_number):
    csv = DATA_DIR / f"beamscan_run_{run_number:03d}.csv"
    if not csv.exists():
        return None

    df = pd.read_csv(csv)
    x = df["Rel_Pos_um"].values
    y = df["Corrected_mV"].values

    # filter high-frequency voltage spikes exceeding 3 std deviations from rolling median
    y_s = pd.Series(y)
    med = y_s.rolling(WINDOW_OUTLIER, center=True).median().bfill().ffill()
    diff = np.abs(y_s - med)
    mask = diff < SIGMA_OUTLIER * diff.std()
    x, y = x[mask], y[mask]

    # identify scan direction from overall signal trend (blade entering vs exiting beam)
    rising = (y[-1] > y[0])

    # Method A: estimate initial parameters and fit erfc directly to transmission curve
    y0g = np.min(y)
    P0g = np.max(y) - np.min(y)
    mid = y0g + P0g / 2.0
    x0g = x[np.argmin(np.abs(y - mid))]
    wg = (np.max(x) - np.min(x)) / 5.0

    model_A = erfc_model_rising if rising else erfc_model
    try:
        popt_A, pcov_A = curve_fit(model_A, x, y, p0=[y0g, P0g, x0g, wg], maxfev=10000)
        w_A = abs(popt_A[3])
        sigma_A = np.sqrt(pcov_A[3, 3])
    except RuntimeError:
        return None

    # calculate average step spacing in um
    step_um = float(np.median(np.diff(np.sort(x))))

    def smooth(arr, window):
        return pd.Series(arr).rolling(window, center=True).mean().bfill().ffill().values

    # Method B: calculate numerical derivative dP/dx and fit Gaussian to intensity profile
    # compare fixed window (inflates w near waist) vs adaptive window (scales with beam size)
    y_smooth_fixed = smooth(y, WINDOW_FIXED)
    adaptive_window = max(MIN_WINDOW, round(w_A * ADAPTIVE_FRACTION / step_um))
    y_smooth_adaptive = smooth(y, adaptive_window)

    def derivative_and_fit(y_smoothed):
        dydx = np.gradient(y_smoothed, x)
        dydx_pos = dydx if rising else -dydx # orient derivative as positive peak
        peak_idx = np.argmax(dydx_pos)
        half_range = (np.max(x) - np.min(x)) * 0.35
        centre_x = x[peak_idx]
        mask = np.abs(x - centre_x) < half_range # isolate central peak region
        xc, yc = x[mask], dydx_pos[mask]
        A_g = np.max(yc)
        sigma_g = w_A / 2.0
        try:
            popt, pcov = curve_fit(gaussian_model, xc, yc, p0=[A_g, centre_x, sigma_g, 0.0], maxfev=10000)
            w_fit = abs(2.0 * popt[2]) # relation for Gaussian profile: w = 2*sigma
            sigma_fit = 2.0 * np.sqrt(pcov[2, 2])
            return w_fit, sigma_fit, dydx_pos, popt
        except RuntimeError:
            return np.nan, np.nan, dydx_pos, None

    w_B_fixed, err_B_fixed, dydx_fixed, popt_B_fixed = derivative_and_fit(y_smooth_fixed)
    w_B_adaptive, err_B_adaptive, dydx_adaptive, popt_B_adaptive = derivative_and_fit(y_smooth_adaptive)
    w_B, sigma_B = w_B_adaptive, err_B_adaptive

    return {
        "run": run_number,
        "w_A": w_A,
        "err_A": sigma_A,
        "w_B": w_B,
        "err_B": sigma_B,
        "w_B_fixed": w_B_fixed,
        "err_B_fixed": err_B_fixed,
        "adaptive_window": adaptive_window,
        "step_um": step_um,
        "x": x,
        "y": y,
        "y_smooth_fixed": y_smooth_fixed,
        "y_smooth_adaptive": y_smooth_adaptive,
        "dydx_fixed": dydx_fixed,
        "dydx_adaptive": dydx_adaptive,
        "popt_A": popt_A,
        "popt_B_fixed": popt_B_fixed,
        "popt_B_adaptive": popt_B_adaptive,
        "rising": rising,
    }

# run dual fits across all dataset scans
print("Fitting runs...")
hene_results = []
diode_results = []

for run, z in HENE_RUNS.items():
    r = fit_run(run)
    if r:
        r["z"] = z
        hene_results.append(r)
        print(f"  HeNe run {run:3d}  z={z} mm  w_erfc={r['w_A']:7.2f}  w_gauss(fixed)={r['w_B_fixed']:7.2f}  w_gauss(adp,N={r['adaptive_window']})={r['w_B']:7.2f} um")

for run, z in DIODE_RUNS.items():
    r = fit_run(run)
    if r:
        r["z"] = z
        diode_results.append(r)
        print(f"  Diode run {run:3d}  z={z} mm  w_erfc={r['w_A']:7.2f}  w_gauss(fixed)={r['w_B_fixed']:7.2f}  w_gauss(adp,N={r['adaptive_window']})={r['w_B']:7.2f} um")

def plot_laser(results, name, color):
    if not results:
        return

    zs = np.array([r["z"] for r in results])
    w_A = np.array([r["w_A"] for r in results])
    err_A = np.array([r["err_A"] for r in results])
    w_B = np.array([r["w_B"] for r in results])
    err_B = np.array([r["err_B"] for r in results])
    w_B_fixed = np.array([r["w_B_fixed"] for r in results])
    runs = [r["run"] for r in results]
    win_labels = [f"N={r['adaptive_window']}" for r in results]

    frac_fixed = (w_B_fixed - w_A) / w_A * 100
    frac_adaptive = (w_B - w_A) / w_A * 100

    fig, axes = plt.subplots(4, 1, figsize=(11, 16), constrained_layout=True)

    # panel 1: beam radius w(z) extracted from Method A, Method B (fixed), and Method B (adaptive)
    ax = axes[0]
    ax.errorbar(zs, w_A, yerr=err_A, fmt="o-", color="tab:red", capsize=4, zorder=4, label="Method A — erfc fit")
    ax.errorbar(zs, w_B_fixed, fmt="x:", color="tab:gray", capsize=3, zorder=2, label=f"Method B — Gauss (fixed N={WINDOW_FIXED})")
    ax.errorbar(zs, w_B, yerr=err_B, fmt="s--", color="tab:blue", capsize=4, zorder=3, label="Method B — Gauss (adaptive N)")
    for zi, wa, run in zip(zs, w_A, runs):
        ax.annotate(str(run), (zi, wa), xytext=(3, 5), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Axial position z (mm)")
    ax.set_ylabel("Beam radius w (µm)")
    ax.set_title(f"{name}: Beam radius comparison")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # panel 2: percent discrepancy showing fixed window broadening near the beam waist
    ax = axes[1]
    ax.axhline(0, color="black", linewidth=1)
    ax.axhspan(-5, 5, color="gray", alpha=0.10, label="±5% band")
    ax.plot(zs, frac_fixed, "x:", color="tab:gray", label=f"Fixed N={WINDOW_FIXED}")
    ax.plot(zs, frac_adaptive, "s--", color="tab:blue", label="Adaptive N")
    ax.scatter(zs, frac_fixed, color="tab:gray", zorder=3)
    ax.scatter(zs, frac_adaptive, color="tab:blue", zorder=4)
    for zi, fa, fw, run, wl in zip(zs, frac_adaptive, frac_fixed, runs, win_labels):
        ax.annotate(f"{run}\n({wl})", (zi, fa), xytext=(3, 5), textcoords="offset points", fontsize=7, color="tab:blue")
    ax.set_xlabel("Axial position z (mm)")
    ax.set_ylabel("(w_B − w_A) / w_A (%)")
    ax.set_title("Fractional discrepancy: fixed vs adaptive smoothing")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # panels 3 & 4: sample S-curves and derivative profiles near waist (small beam) and in far field (large beam)
    valid = [r for r in results if not np.isnan(r["w_B"])]
    near = min(valid, key=lambda r: r["w_A"])
    far = max(valid, key=lambda r: r["w_A"])

    for ax, ex, label in zip(axes[2:], [near, far], ["near waist", "far field"]):
        x, y = ex["x"], ex["y"]
        x_fine = np.linspace(x.min(), x.max(), 800)
        model_fn = erfc_model_rising if ex["rising"] else erfc_model
        y_A_fit = model_fn(x_fine, *ex["popt_A"])

        ax2 = ax.twinx()
        ax.plot(x, y, "k.", alpha=0.2, markersize=2, label="Raw data")
        ax.plot(x_fine, y_A_fit, color="tab:red", lw=2, label=f"erfc w={ex['w_A']:.1f} µm")
        ax.set_xlabel("Knife-edge position (µm)")
        ax.set_ylabel("Power (mV)")

        dy_fixed = ex["dydx_fixed"]
        dy_adaptive = ex["dydx_adaptive"]
        ax2.plot(x, dy_fixed, color="tab:gray", lw=0.8, alpha=0.6, label=f"dP/dx fixed N={WINDOW_FIXED}")
        ax2.plot(x, dy_adaptive, color="steelblue", lw=1.2, alpha=0.8, label=f"dP/dx adaptive N={ex['adaptive_window']}")

        if ex["popt_B_fixed"] is not None:
            gf = gaussian_model(x_fine, *ex["popt_B_fixed"])
            ax2.plot(x_fine, gf, ":", color="tab:gray", lw=2, label=f"Gauss(fixed) w={ex['w_B_fixed']:.1f} µm")
        if ex["popt_B_adaptive"] is not None:
            ga = gaussian_model(x_fine, *ex["popt_B_adaptive"])
            ax2.plot(x_fine, ga, "--", color="tab:blue", lw=2, label=f"Gauss(adaptive) w={ex['w_B']:.1f} µm")

        ax2.set_ylabel("dP/dx (mV/µm)", color="steelblue")
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper left")
        ax.set_title(f"Run {ex['run']} (z={ex['z']} mm) — {label}")
        ax.grid(alpha=0.3)

    fig.suptitle(f"{name} — Dual-Method Beam Radius Comparison", fontsize=13)
    out = f"dual_fit_{name.lower()}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved {out}")
    plt.show()

plot_laser(hene_results, "HeNe", "tab:red")
plot_laser(diode_results, "Diode", "tab:blue")

# print summary table
print("\n" + "=" * 80)
print(f"{'Laser':>5} {'z':>5}  {'w_erfc':>8}  {'w_B(fix)':>10} {'Δfix%':>7}  {'N_adp':>6} {'w_B(adp)':>10} {'Δadp%':>7}")
print("=" * 80)

for name, results in [("HeNe", hene_results), ("Diode", diode_results)]:
    print(f"\n{name}")
    for r in sorted(results, key=lambda x: x["z"], reverse=True):
        d_fix = (r["w_B_fixed"] - r["w_A"]) / r["w_A"] * 100
        d_adp = (r["w_B"] - r["w_A"]) / r["w_A"] * 100
        print(f"  run {r['run']:>3d}  z={r['z']:>4d}  w_A={r['w_A']:>8.2f}  w_fix={r['w_B_fixed']:>8.2f}  {d_fix:>+6.1f}%  N={r['adaptive_window']:>3d}  w_adp={r['w_B']:>8.2f}  {d_adp:>+6.1f}%")
