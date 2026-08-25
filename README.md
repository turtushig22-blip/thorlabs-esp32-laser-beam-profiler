# thorlabs-esp32-laser-beam-profiler

Automated, high-density knife-edge laser beam profiler, integrating Thorlabs sub-micron precision hardware with an ESP32 embedded DAQ via a high-precision 16-bit ADC and real-time TFT visualization engine.

This project uses the Thorlabs TST001, TCH002, and NRT100 devices integrated with the ESP32 microcontroller, ADS1115 analog-to-digital converter, and the ILI9341 TFT LCD to create a precise laser beam profiler. By taking advantage of the ability of the Thorlabs equipments of achieving a sub-micron precision and ESP32’s powerful Dual-core processing abilities at 240 Mhz that successfully executes numerical analysis, signal processing, and UI graphics, this project was able to increased the data density usually found in conventional forms of similar experiments by approximately a factor of x200, achieving a higher precision, lower error, and increased confidence in the beam waist and maximum intensity measurements.

## Setup
The laser beam is generated from a ....diode laser that is categorized as a Class III laser; therefore, it was necessary to complete the training to be allowed to operate on the laser. The laser beam is then blocked by the knife edge (which is a razor blade in our case). After the stepper motor moves the blade in steps of 0.5 - 5 microns depending on the specific run we were considering, the laser beam travels down the path reaching the power meter, which sends out an analog signal proportional to the amount of power the laser beam disposes in it. 
