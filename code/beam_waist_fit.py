import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import least_squares

# Fits Gaussian beam propagation w(z)^2 = w0^2 + [M^2 * lambda * (z - z0) / (pi * w0)]^2
# Compares two models: exact axial positions z vs including ruler reading uncertainty (+/- 0.5 mm)

# measured data from erfc fits: axial position z (mm), beam waist squared w2 (um^2), and 1-sigma uncertainty
datasets = {
    "HeNe": {
        "wavelength_um": 0.633,
        "run": np.array([26, 27, 28, 35, 36, 29, 37, 33, 30, 31, 32]),
        "z": np.array([558, 553, 548, 545, 544, 543, 542, 540, 538, 533, 528], dtype=float),
        "w2": np.array([14016.19, 5656.54, 2715.45, 1493.82, 1514.77, 927.81, 957.28, 1202.70, 2229.73, 6026.42, 12488.06]),
        "sigma_w2": np.array([40.25, 63.18, 40.65, 6.18, 12.45, 21.32, 5.57, 5.55, 13.22, 34.16, 49.17]),
    },
    "Diode": {
        "wavelength_um": 0.780,
        "run": np.array([14, 15, 16, 17, 22, 24, 23, 25, 18, 19, 20, 21]),
        "z": np.array([350, 345, 340, 335, 334, 333, 332, 331, 330, 325, 320, 315], dtype=float),
        "w2": np.array([170957.44, 87001.40, 26817.34, 1348.36, 1425.82, 486.20, 289.34, 3070.27, 9904.23, 56539.33, 111429.12, 211443.63]),
        "sigma_w2": np.array([438.28, 212.37, 81.88, 4.41, 9.06, 3.97, 3.74, 9.97, 19.90, 180.71, 380.54, 735.73]),
    },
}

# ruler resolution: readings to nearest 1 mm gives uniform +/-0.5 mm error (sigma = 0.5 / sqrt(3))
READING_HALF_WIDTH_MM = 0.5
SIGMA_Z_MM = READING_HALF_WIDTH_MM / np.sqrt(3)

def beam_w2(z_mm, parameters, wavelength_um):
    # Gaussian beam propagation: returns w^2 (um^2) given [w0 (um), z0 (mm), M2]
    w0_um, z0_mm, M2 = parameters
    slope = 1000 * M2 * wavelength_um / (np.pi * w0_um) # 1000 converts mm to um
    return w0_um**2 + (slope * (z_mm - z0_mm))**2

def fit_beam(data, include_z_uncertainty):
    # fits w0, z0, M^2 by minimizing weighted chi-squared residuals
    # if include_z_uncertainty is True, fits per-point dz shifts with penalty (dz / sigma_z)
    z = data["z"]
    w2 = data["w2"]
    sigma_w2 = data["sigma_w2"]
    wavelength = data["wavelength_um"]
    n = len(z)

    # parameter bounds: w0 > 0, z0 within track limits, physical constraint M^2 >= 1
    lower = np.array([0.01, z.min() - 10, 1.0])
    upper = np.array([1000.0, z.max() + 10, 100.0])

    if include_z_uncertainty:
        lower = np.r_[lower, np.full(n, -np.inf)]
        upper = np.r_[upper, np.full(n, np.inf)]

    def residuals(parameters):
        physical_parameters = parameters[:3]
        dz = parameters[3:] if include_z_uncertainty else np.zeros(n)
        predicted = beam_w2(z + dz, physical_parameters, wavelength)
        vertical_residuals = (predicted - w2) / sigma_w2
        if include_z_uncertainty:
            # joint residuals: vertical discrepancy on w^2 and horizontal penalty on dz
            return np.r_[vertical_residuals, dz / SIGMA_Z_MM]
        return vertical_residuals

    # multi-start initialization across w0 values to prevent getting stuck in local minima
    solutions = []
    for initial_w0 in [10.0, 17.0, 25.0, 32.0]:
        initial = np.array([initial_w0, z[np.argmin(w2)], 1.2])
        if include_z_uncertainty:
            initial = np.r_[initial, np.zeros(n)]

        result = least_squares(
            residuals, initial, bounds=(lower, upper),
            x_scale="jac", max_nfev=10000,
            ftol=1e-11, xtol=1e-11, gtol=1e-11
        )
        if result.success:
            solutions.append(result)

    if not solutions:
        raise RuntimeError("Fit did not converge.")

    result = min(solutions, key=lambda r: np.sum(r.fun**2))
    chi2 = np.sum(result.fun**2)
    dof = n - 3 # 3 physical parameters fitted: w0, z0, M^2

    return {
        "parameters": result.x[:3],
        "dz": result.x[3:] if include_z_uncertainty else np.zeros(n),
        "reduced_chi2": chi2 / dof,
    }

# 2x2 comparison plot: top row = propagation curves, bottom row = fitted position shifts
fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)

for column, (name, data) in enumerate(datasets.items()):
    exact = fit_beam(data, include_z_uncertainty=False)
    uncertain = fit_beam(data, include_z_uncertainty=True)

    z = data["z"]
    w = np.sqrt(data["w2"])
    sigma_w = data["sigma_w2"] / (2 * w) # propagate error from w^2 to w
    z_curve = np.linspace(z.min() - 1, z.max() + 1, 800)

    # top panel: data points and fitted hyperbolas
    ax = axes[0, column]
    ax.errorbar(
        z, w, xerr=SIGMA_Z_MM, yerr=sigma_w, fmt="o", color="black",
        ecolor="gray", capsize=3, markersize=5, label="Recorded data"
    )

    for result, color, linestyle, label in [
        (exact, "tab:red", "--", "Fit (z exact)"),
        (uncertain, "tab:blue", "-", "Fit (with ruler uncertainty)"),
    ]:
        fitted_w = np.sqrt(beam_w2(z_curve, result["parameters"], data["wavelength_um"]))
        ax.plot(z_curve, fitted_w, color=color, linestyle=linestyle, linewidth=2, label=label)

    for run, zi, wi in zip(data["run"], z, w):
        ax.annotate(str(run), (zi, wi), xytext=(4, 5), textcoords="offset points", fontsize=8)

    ax.set_title(f"{name}\nReduced χ²: {exact['reduced_chi2']:.2f} → {uncertain['reduced_chi2']:.2f}")
    ax.set_xlabel("Axial position z (mm)")
    ax.set_ylabel("Radius w (µm)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    # bottom panel: fitted axial position shift dz per run compared to ruler uncertainty
    ax = axes[1, column]
    ax.axhspan(-READING_HALF_WIDTH_MM, READING_HALF_WIDTH_MM, color="gray", alpha=0.15, label="Ruler bounds (±0.5 mm)")
    ax.axhline(0, color="black", linewidth=1)
    ax.axhline(READING_HALF_WIDTH_MM, color="gray", linestyle="--")
    ax.axhline(-READING_HALF_WIDTH_MM, color="gray", linestyle="--")

    dz = uncertain["dz"]
    ax.vlines(z, 0, dz, color="tab:blue", alpha=0.6)
    ax.scatter(z, dz, color="tab:blue")

    for run, zi, shift in zip(data["run"], z, dz):
        ax.annotate(str(run), (zi, shift), xytext=(4, 5), textcoords="offset points", fontsize=8)

    ax.set_title("Position adjustments from fit")
    ax.set_xlabel("Axial position z (mm)")
    ax.set_ylabel("Fitted position − recorded position (mm)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)

    # numerical summary
    print(f"\n{name}")
    print("-" * 50)
    for label, result in [("z exact", exact), ("With z uncertainty", uncertain)]:
        w0, z0, M2 = result["parameters"]
        boundary = " [AT LOWER BOUND]" if M2 <= 1.00001 else ""
        print(f"  {label}: w0 = {w0:.3f} µm, z0 = {z0:.3f} mm, M² = {M2:.4f}{boundary}, reduced χ² = {result['reduced_chi2']:.3f}")

    # flag data points requiring axial shift larger than ruler resolution
    outside = data["run"][np.abs(dz) > READING_HALF_WIDTH_MM]
    print("Runs requiring shifts beyond ±0.5 mm:", outside.tolist())

fig.suptitle(f"Effect of ruler uncertainty: σz = {SIGMA_Z_MM:.3f} mm", fontsize=14)
plt.show()
