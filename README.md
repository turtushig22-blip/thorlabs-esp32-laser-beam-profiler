# thorlabs-esp32-laser-beam-profiler

An automated, high-density knife-edge laser beam profiler integrating Thorlabs sub-micron precision motion control with an ESP32 embedded DAQ system via an external 16-bit ADC, featuring real-time on-display TFT visualization and rigorous non-linear least-squares beam waist fitting.

<img width="60%" height="644" alt="image" src="https://github.com/user-attachments/assets/77cfafc6-b08f-47fa-b724-69fcdccde026" /> 

## Overview
This project uses the Thorlabs TST001 stepper motor controller, TCH002 controller hub and power supply unit, and NRT100 linear actuator to translate a razor blade across the laser profile, paired with a Thorlabs PM100A optical power meter to measure the transmitted power. The analog detector output is digitized and processed using an ESP32 microcontroller, an ADS1115 analog-to-digital converter, and an ILI9341 SPI TFT LCD display.By leveraging the sub-micron mechanical positioning of Thorlabs optomechanics alongside the ESP32’s dual-core 240 MHz architecture to coordinate synchronized sampling, signal conditioning, and graphical feedback, this system increases the spatial data density of conventional manual knife-edge profiling by a factor of approximately $\times 200$. This achieves sub-micron spatial resolution, reduced systematic errors, and elevated statistical confidence in extracted beam waists ($w_0$) and optical intensity distributions.

## Optical & Mechanical Setup

[ TeachSpin DLI-A Laser ] <br>
       &emsp;&emsp; &emsp;&emsp;&nbsp;  │ <br>
       &emsp;&emsp;  &emsp;&emsp; ▼ <br>
   [ Beam Expander ] ────> (L1: f = 7.5 cm, L2: f = 16.0 cm, Keplerian M ≈ 2.13) <br>
      &emsp;&emsp; &emsp;&emsp;&nbsp; │ <br>
      &emsp;&emsp; &emsp;&emsp;    ▼ <br>
   [ Focusing Optic ] ───> (L3: f = 7.5 cm plano-convex singlet) <br>
      &emsp;&emsp; &emsp;&emsp;&nbsp;  │ <br>
      &emsp;&emsp; &emsp;&emsp;    ▼ <br>
 [ Knife-Edge (Razor) ] ── [ Thorlabs NRT100 + TST001 Stepper Stage ] <br>
      &emsp;&emsp; &emsp;&emsp;&nbsp;  │ <br>
      &emsp;&emsp; &emsp;&emsp;    ▼ <br>
 [ Thorlabs PM100A Sensor ] <br>
       &emsp;&emsp; &emsp;&emsp;&nbsp;  │ (Analog Output: 0–2 V scaled) <br>
      &emsp;&emsp; &emsp;&emsp;    ▼ <br>
    [ RC Low-Pass Filter ] <br>
      &emsp;&emsp; &emsp;&emsp;&nbsp;   │ <br>
      &emsp;&emsp; &emsp;&emsp;    ▼ <br>
  [ ADS1115 16-Bit ADC ] ── (I2C: 860 SPS, PGA = 16x) <br>
      &emsp;&emsp; &emsp;&emsp;&nbsp;   │ <br>
      &emsp;&emsp; &emsp;&emsp;    ▼ <br>
   [ ESP32 MCU + ILI9341 TFT ] ── (SPI Real-Time S-Curve Display) <br>
      &emsp;&emsp; &emsp;&emsp;&nbsp;   │ <br>
      &emsp;&emsp; &emsp;&emsp;    ▼ (USB-Serial Handshake) <br>
   [ Host Python DAQ ] ───> Non-Linear ERFC Least-Squares Fitting <br>


**Laser Source:** TeachSpin DLI-A diode laser (Class IIIb coherent source; operated under standard laser safety protocols). <br>
**Collimation & Focusing Train:** A two-lens Keplerian beam expander ($f_1 = 7.5\text{ cm}$, $f_2 = 16.0\text{ cm}$, magnification $M \approx 2.13$) expands the raw beam before it enters a short focal length focusing optic ($f_3 = 7.5\text{ cm}$). This maximizes the effective numerical aperture to compress the focused beam waist down toward the diffraction limit. <br>
**Spatial Scanning:** A clean razor blade is mounted perpendicular to the optical axis on a Thorlabs NRT100 translation stage driven by a TST001 stepper driver ($25{,}600\text{ microsteps/mm}$ encoder resolution). Scanning step sizes range from $0.5\text{ µm}$ to $2.5\text{ µm}$ across travel lengths of $0.6\text{ mm}$ to $3.0\text{ mm}$. <br>
**Optical Detection:** The transmitted power is collected by a Thorlabs PM100A optical power meter console, outputting a calibrated continuous analog voltage proportional to the unblocked optical power. <br>
