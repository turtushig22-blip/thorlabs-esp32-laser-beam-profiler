# Automated High-Density Knife-Edge Laser Beam Profiler

> **Sub-Micron Characterisation of HeNe and Diode Laser Beam Waists Using Thorlabs Motion Control, ESP32 Embedded DAQ, and Custom Signal Conditioning PCB**

[![EDA: KiCad 9.0](https://img.shields.io/badge/EDA-KiCad%209.0-orange.svg)](#)
[![Optics: Thorlabs](https://img.shields.io/badge/Optics-Thorlabs%20NRT100-yellow.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](#)

---

## Repository Organization & Environments

> **Note on Project Code & Hardware Files:**
> * **Python & Analysis Tools:** To inspect the complete runtime environment and execution pipeline, please see the [`code/`](#) folder (where `master_python.py`, fitting routines, and analysis tools are stored).
> * **Hardware & PCB Design:** For the custom printed circuit board schematics, layout, and fabrication gerbers, please see the [`KiCad/`](#) directory.

---
<img width="70%" height="1010" alt="image" src="https://github.com/user-attachments/assets/58edcdba-c4f6-4166-9a3a-a5a5446ed7d4" />

## Overview

Characterizing laser beam characteristics, beam waists (w<sub>0</sub>), and propagation quality ($M^2$) at micron-level scales requires dense spatial sampling and low-noise instrumentation. Manual knife-edge profiling suffers from coarse positioning, slow acquisition rates, and human parallax errors.

This project delivers an automated knife-edge laser beam profiler:
1. **Sub-Micron Actuation:** A **Thorlabs NRT100** linear translation stage driven by a **TST001** stepper motor controller via a **TCH002** hub, stepping a precision commercial razor blade in increments as fine as **$0.5\mu\text{m}$** (with step support down to $0.1\mu\text{m}$).
2. **Custom Signal Processing & Embedded DAQ:** Optical power is acquired via a **Thorlabs PM100A** optical power meter. The analog output is filtered through a hardware 1st-order RC low-pass filter ($f_c \approx 15.92\,\text{Hz}$), digitized by a 16-bit **ADS1115** ADC, and managed by an **ESP32** microcontroller running custom firmware with real-time S-curve rendering on an **ILI9341** 2.8" SPI TFT display.
3. **Automated Host Organization:** A Python-based host (`master_python.py`) synchronizes stage translation, introduces settling dwells ($0.5\text{s}$), acquires dark-background-corrected voltages, performs real-time encoder verification, and logs structured scan datasets.
4. **Statistical & Optical Modeling:** Implements non-linear error function ($\mathrm{erfc}$) S-curve fits, rolling-median $3\sigma$ outlier rejection, adaptive-window derivative comparisons (Power distribution S-curve fit vs. Intensity Gaussian curve fit), and Tikhonov-regularized non-linear least-squares propagation modeling to account for millimeter-ruler positioning uncertainty ($\sigma_z \approx 0.289\text{mm}$).

---

## Experimental Setup

```
 Laser Source            Keplerian Expander                Focusing Lens         Knife-Edge Plane          Power Sensor
[ HeNe / Diode ] ---> [ L1 (f=75mm) + L2 (f=160mm) ] ---> [ L3 (f=75mm) ] ---> [ Razor on NRT100 ] ---> [ Thorlabs PM100A ]
                            (M_exp ≈ 2.13x)                                       (0.5 µm steps)                |
                                                                                                                v
                                                                                                     Analog Out (0.0-2.0 V)
                                                                                                                |
                                                                                                                v
                                                                                                     [ RC Low-Pass Filter ]
                                                                                                        (fc ≈ 15.92 Hz)
                                                                                                                |
                                                                                                                v
                                                                                                     [ ADS1115 16-bit ADC ]
                                                                                                                |
                                                                                                                v
                                             [ Host PC / master_python.py ] <==== USB Serial <==== [ ESP32 Microcontroller ] ====> [ ILI9341 2.8" TFT ]
                                                           |                                                                        (Real-Time S-Curve)
                                                           v (FTDI D2XX / pylablib)
                                              [ Thorlabs TST001 / NRT100 ]
```

<img width="90%" height="613" alt="image" src="https://github.com/user-attachments/assets/2fd9b9e9-1c45-42c6-b046-227357c5e7b5" />

### Optical Specifications
* **Lasers Used:**
  * HeNe Laser: $\lambda = 632.8\text{nm}$, TEM$_{00}$ fundamental mode.
  * TeachSpin DLI-A Diode Laser: Nominal $780\text{nm}$, experimentally calibrated at $\lambda = 780.9\,\text{nm}$ (instrument-limited linewidth $\Delta\lambda \lesssim 3\text{nm}$).
* **Expander:** Keplerian telescope composed of plano-convex lenses $L_1$ ($f_1 = 7.5\text{cm}$) and $L_2$ ($f_2 = 16.0\text{cm}$) giving a magnification $M_\text{exp} of \approx 2.13$.
* **Focusing Optic:** Plano-convex singlet $L_3$ ($f_3 = 7.5\text{cm}$), establishing a tight waist at the knife-edge plane.
* **Actuation Stage:** Thorlabs NRT100 with internal optical encoder ($25{,}600\,\text{microsteps/mm}$), scanning $1000$ steps ($0.5\,\text{mm}$ travel) per axial $z$-position.

---

## Hardware & Custom PCB (`KiCad/`)

The analog signal conditioning and digitization circuit is designed as a dedicated PCB in KiCad 9.0, located in the [`KiCad/`](#) folder:

* **Schematic & Layout:** [`KiCad/BeamWaist.kicad_sch`](#) and [`KiCad/BeamWaist.kicad_pcb`](#)
* **Fabrication Files:** Production Gerber archives in [`KiCad/Gerbers/`](#)
<img width="60%" height="593" alt="image" src="https://github.com/user-attachments/assets/94913329-12db-4093-8bdf-21442174d811" />

### Key Circuit Features
1. **Low-Pass Anti-Aliasing Filter:** First-order RC filter with $R = 10\,\text{k}\Omega$ and $C = 1\,\mu\text{F}$ ($f_c = \frac{1}{2\pi RC} \approx 15.92\,\text{Hz}$), eliminating high-frequency mechanical vibrations, laser ripple, and $60\,\text{Hz}$ ambient illumination pickup before sampling.
2. **Analog-to-Digital Converter (ADS1115):**
   * Interface: $\text{I}^2\text{C}$ bus at addresses `0x48`.
   * Data rate: $860\,\text{SPS}$.
   * Programmable Gain Amplifier (PGA): Set to $16\times$ ($\pm 0.256\,\text{V}$ dynamic scale), providing sub-$10\,\mu\text{V}$ voltage resolution ($\approx 7.81\,\mu\text{V}/\text{LSB}$).
3. **Microcontroller & User Feedback:**
   * ESP32 dual-core SoC running at $240\,\text{MHz}$.
   * High-speed SPI interface driving an ILI9341 320x240 TFT LCD displaying live S-curve telemetry and transmission saturation warnings.
   * USB-to-UART bridging communicating bidirectionally with the host Python controller.

---

## Embedded Firmware (`ESP32_sketch.cpp/`)

Located in [`ESP32_sketch.cpp/sketch_aug21b/sketch_aug21b.ino`](#):
* **Hardware Averaging:** Performs 64-sample burst averaging on each query ($N = 64$ at $860\,\text{SPS} \approx 18\,\text{ms}$ sampling duration) to eliminate broadband noise without adding scan latency.
* **Serial Command Protocol:**
  * `READ`: Triggers the ADC burst, updates the on-screen coordinate trace, and transmits the 6-decimal floating-point voltage (in volts) over USB serial.
  * `RESET`: Clears the screen buffer and re-initializes plot grid boundaries for the next axial scan.

---

## Software Suite & Useful Scripts (`code/`)

All data acquisition, reduction, fitting, and visualization code is housed in [`code/`](#). Below is a complete reference of the primary scripts:

### 1. `master_python.py` (Master DAQ Host Controller)
* **Role:** Primary automation coordinator interfacing the physical experiment.
* **Functionality:**
  * Establishes low-level FTDI communication (`libftd2xx.dylib`, `pylablib`) to command the Thorlabs TST001 controller.
  * Handles stage motion, waiting routines, and dwell settling times ($0.5\,\text{s}$).
  * Communicates with ESP32 via USB-Serial (`pyserial`).
  * Executes automated dark-background measurement ($N_\text{bg} = 50\text{--}100$ samples) and subtraction.
  * Performs active closed-loop encoder monitoring (flags position discrepancy if error exceeds $2\,\mu\text{m}$).
  * Auto-increments and saves run metadata to CSV files (`beamscan_run_NNN.csv`).

### 2. `beam_waist_fit.py` (Caustic Propagation & Ruler Uncertainty Fitter)
* **Role:** Evaluates beam waist radius $w_0$, waist axial position $z_0$, and beam quality factor $M^2$.
* **Key Innovations:**
  * Solves the Gaussian beam propagation equation:
    $$w^2(z) = w_0^2 + \left[\frac{M^2 \lambda}{\pi w_0}(z - z_0)\right]^2$$
  * Features a **Tikhonov-regularized dual-residual objective**:
    $$\mathbf{r}(\boldsymbol{\theta}, \boldsymbol{\delta z}) = \begin{pmatrix} \frac{w^2(z_i + \delta z_i; \boldsymbol{\theta}) - w_i^2}{\sigma_{w^2, i}} \\ \frac{\delta z_i}{\sigma_z} \end{pmatrix}$$
    where $\sigma_z = \frac{0.5\,\text{mm}}{\sqrt{3}} \approx 0.289\,\text{mm}$ captures reading uncertainty on the millimeter bench ruler.
  * Compares unregularized ("$z$ exact") vs. regularized ("$z$ uncertain") models, producing comparative plots and nuisance shift diagnostics ($\delta z_i$).

### 3. `dual_fit_comparison.py` (Method A vs. Method B Benchmark)
* **Role:** Systematic cross-validation of beam extraction techniques:
  * **Method A:** Non-linear least-squares fit directly to the integrated power S-curve ($\mathrm{erfc}$ model).
  * **Method B:** Numerical differentiation of the S-curve ($\mathrm{d}P/\mathrm{d}x$) followed by a Gaussian fit ($\sigma = w/2$).
* **Adaptive Smoothing Analysis:** Demonstrates how static rolling averages ($N = 100$) artifically broaden derivative peaks near tight waists (up to $+55\%$ on HeNe and $+129\%$ on Diode), and implements an adaptive window:
  $$N_\text{adaptive} = \max\left(N_\text{min}, \mathrm{round}\left(\frac{\alpha w_A}{\Delta x_\text{step}}\right)\right)$$
  proving why direct $\mathrm{erfc}$ fitting (Method A) is superior.

### 4. `erfc_fitter.py` & `erfc_fitter_hene.py` (Single-Run S-Curve Extractors)
* **Role:** Detailed profiling and analysis of individual scan CSV files.
* **Features:**
  * $3\sigma$ outlier filtering against a 15-point rolling median.
  * Automatic deterministic initial parameter guessing ($y_0, P_0, x_0, w_0$).
  * Non-linear Levenberg-Marquardt / Trust-Region fitting using `scipy.optimize.curve_fit`.
  * Rigorous extraction of parameter covariance and variance $\sigma_{w^2} = 2w\sigma_w$.

### 5. `plot_spectrometer.py` (Diode Laser Spectral Analysis)
* **Role:** Ingests raw spectral output (`spectrometer_data.csv`) from the Ocean Optics / USB fiber spectrometer.
* **Features:**
  * Full spectrum survey ($750\text{--}820\,\text{nm}$) and high-resolution zoomed window ($778\text{--}786\,\text{nm}$).
  * Gaussian fitting demonstrating center emission at $\lambda = 780.9\,\text{nm}$.
  * Resolves instrument-limited FWHM ($\Delta\lambda \lesssim 3\,\text{nm}$) consistent with single-longitudinal-mode operation.

### 6. `error_correction_test.py` & `test_diagnostic.py` (Diagnostics & Validation)
* **Role:** Hardware sanity checks and simulation testbenches verifying serial timing, stage communication handshakes, and optimization convergence.

---

## Summary of Experimental Results

From the comprehensive lab report draft ([`report_draft.tex`](#)):

| Parameter | HeNe Laser ($\lambda = 632.8\,\text{nm}$) | Diode Laser ($\lambda = 780.9\,\text{nm}$) |
| :--- | :---: | :---: |
| **Beam Waist ($w_0$)** | **$30.80\,\mu\text{m}$** | **$9.81\,\mu\text{m}$** |
| **Waist Location ($z_0$)** | $542.4\,\text{mm}$ | $333.4\,\text{mm}$ |
| **Beam Quality Factor ($M^2$)** | **$1.13$** (Near-ideal TEM$_{00}$) | **$1.00^\dagger$** (Astigmatic limit) |
| **Rayleigh Range ($z_R$)** | $\approx 4.16\,\text{mm}$ | $\approx 0.39\,\text{mm}$ |
| **Nominal Reduced $\chi^2$ ($z$-exact)** | $314.7$ | $12{,}886$ |
| **Nominal Reduced $\chi^2$ ($z$-uncertain)** | **$7.65$** | **$4.14$** |

$^\dagger$ *Note on Diode $M^2$: The optimization parameter converged to its physical lower bound ($M^2 = 1.0$), resulting from semiconductor laser astigmatism (asymmetric fast vs. slow divergence axes creating shifted caustics across orthogonal transverse planes).*

---

## Getting Started & Environment Setup

### 1. Prerequisites
* **Operating System:** macOS (Apple Silicon / Intel) or Linux.
* **Python:** 3.10 or higher.
* **Hardware Drivers:** FTDI D2XX driver installed (`libftd2xx.dylib` on macOS or `libftd2xx.so` on Linux).

### 2. Python Environment Setup
Navigate to the project root and create a virtual environment:

```bash
# Clone repository
git clone https://github.com/placeholder-user/placeholder-repo.git
cd BeamWaistProject

# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required dependencies
pip install numpy scipy matplotlib pandas pyserial pylablib
```

### 3. ESP32 Firmware Flashing
1. Open [`ESP32_sketch.cpp/sketch_aug21b/sketch_aug21b.ino`](#) in Arduino IDE or PlatformIO.
2. Ensure the following libraries are installed:
   * `Adafruit_GFX`
   * `Adafruit_ILI9341`
   * `Adafruit_ADS1X15`
3. Connect the ESP32 via USB and flash the board (Baud rate: `115200`).

### 4. Running a Data Acquisition Run
Connect the Thorlabs TST001 controller and ESP32 board, verify serial ports, and run:

```bash
python code/master_python.py
```

### 5. Running Beam Fitting & Analysis

```bash
# Run caustic propagation fitting (with axial ruler uncertainty propagation)
python code/beam_waist_fit.py

# Compare Method A (ERFC) vs Method B (Adaptive Derivative)
python code/dual_fit_comparison.py

# Plot spectrometer spectral emission
python code/plot_spectrometer.py
```

---

## Repository Structure

```
.
├── README.md                      # Comprehensive project documentation
├── BeamWaist_report.tex           # Complete LaTeX report
├── code/                          # Unified Python codebase
│   ├── master_python.py           # Automated DAQ ecosystem (Thorlabs + ESP32)
│   ├── beam_waist_fit.py          # Caustic propagation fitting & regularized LSQ
│   ├── dual_fit_comparison.py     # Method A (Power curve erfc fit) vs Method B (Intensity curve Gaussian fit) comparison
│   ├── erfc_fitter.py             # Single-scan S-curve filter & erfc fitting (Diode)
│   ├── erfc_fitter_hene.py        # Single-scan S-curve filter & erfc fitting (HeNe)
│   ├── plot_spectrometer.py       # Diode spectrometer analysis & Gaussian peak fitting
│   ├── error_correction_test.py   # Position correction & residual validation
│   └── test_diagnostic.py         # Hardware & serial communication diagnostics
├── KiCad/                         # Hardware electronics & custom DAQ PCB
│   ├── BeamWaist.kicad_pro        # KiCad project file
│   ├── BeamWaist.kicad_sch        # Circuit schematic (ADS1115, RC filter, ESP32)
│   ├── BeamWaist.kicad_pcb        # PCB board layout & routing
│   └── Gerbers/                   # Production-ready Gerber and drill files
├── ESP32_sketch.cpp/              # Embedded firmware
│   └── sketch_aug21b/
│       └── sketch_aug21b.ino      # ESP32 firmware (ADC oversampling & TFT S-curve display)
├── BeamWaistData/                 # Raw experimental scan datasets (CSV)
│   ├── beamscan_run_014.csv
│   └── ...
└── figures/                       # Rendered plots and optical diagrams
    ├── beam_diagram.pdf           # Schematic of optical train
    ├── dual_fit_hene.png          # HeNe dual-method fitting comparison
    ├── dual_fit_diode.png         # Diode dual-method fitting comparison
    └── spectrometer_plot.png      # Measured diode laser spectrum
```

---

## Authors & Context

* **Author:** Turtushig Dashjav 
* **Supervisor:** Eric Wells, Ph.D.
* **Affiliation:** Department of Physics, Augustana University, Sioux Falls, SD, USA

---

## References
* **Key Literature:**
  * A. E. Siegman, *Lasers*, University Science Books (1986).
  * ISO 11146-1:2005, *Lasers and laser-related equipment — Test methods for laser beam widths, divergence angles and beam propagation ratios*.
  * F. M. Dickey & T. E. Holswade, *Laser Beam Shaping: Theory and Techniques*, Marcel Dekker (2000).
  * W. H. Press et al., *Numerical Recipes: The Art of Scientific Computing*, 3rd ed., Cambridge University Press (2007).
