import csv
import ctypes
import glob
import math
import os
import re
import time
import serial
from pylablib.devices import Thorlabs

# Automated knife-edge scan: steps Thorlabs translation stage, reads photodiode
# voltage via ESP32 ADC, and logs position vs signal to CSV.

DATA_DIRECTORY = "/Users/hongorchamdaa/Desktop/BeamWaistProject/BeamWaistData"

def get_next_filename(prefix="beamscan_run", ext="csv", directory=DATA_DIRECTORY):
    # auto-increment run filename (e.g. beamscan_run_001.csv) to avoid overwriting previous scans
    os.makedirs(directory, exist_ok=True)
    pattern = os.path.join(directory, f"{prefix}_*.{ext}")
    existing = glob.glob(pattern)
    max_num = -1
    for path in existing:
        match = re.search(rf"{prefix}_(\d+)\.{ext}$", os.path.basename(path))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return os.path.join(directory, f"{prefix}_{max_num + 1:03d}.{ext}")

# hardware and scan configuration
SERIAL_NO = "80840296"              # Thorlabs TST001 controller serial number
ESP32_PORT = "/dev/cu.usbserial-10" # ESP32 serial interface port
BAUDRATE = 115200
STEP_SIZE = 0.0005                  # stage step size in mm (0.5 um per step)
N_STEPS = 1000                      # 1000 steps * 0.5 um = 0.5 mm total travel
BACKGROUND_N_SAMPLES = 50           # baseline dark/ambient voltage samples to average
DWELL_TIME = 0.5                    # settling delay (s) after each step before ADC read
SERIAL_TIMEOUT = 3.0                # serial read timeout in seconds
POSITION_CHECK_INTERVAL = 100       # check hardware position against target every N steps
STAGE_MOVE_RETRIES = 3              # communication retry attempts per move
STAGE_RETRY_DELAY = 1.0             # pause (s) between move retries

# FTDI D2XX setup for Thorlabs USB communication
try:
    d2xx = ctypes.cdll.LoadLibrary("/usr/local/lib/libftd2xx.dylib")
    d2xx.FT_SetVIDPID(ctypes.c_ulong(0x0403), ctypes.c_ulong(0xFAF0))
except Exception as e:
    print(f"FTDI note: {e}")

def read_esp32_voltage(esp32, step_number=None):
    # query ESP32 over serial for latest photodiode voltage reading
    esp32.reset_input_buffer()
    esp32.write(b"READ\n")
    esp32.flush()
    line = esp32.readline().decode("utf-8", errors="replace").strip()
    if not line:
        if step_number is not None:
            raise TimeoutError(f"ESP32 timeout at step {step_number}")
        raise TimeoutError("ESP32 did not return a measurement")
    try:
        voltage = float(line)
    except ValueError:
        raise ValueError(f"Invalid ESP32 response: {line!r}")
    if not math.isfinite(voltage):
        raise ValueError(f"ESP32 returned non-finite voltage: {line!r}")
    return voltage

def reset_esp32(esp32):
    # clear serial buffers and reset ESP32 display state
    esp32.reset_input_buffer()
    esp32.reset_output_buffer()
    esp32.write(b"RESET\n")
    esp32.flush()
    response = esp32.readline().decode("utf-8", errors="replace").strip()
    if response != "OK":
        raise RuntimeError(f"Unexpected RESET response from ESP32: {response!r}")

def move_stage_safely(stage, target, retries=STAGE_MOVE_RETRIES):
    # command stage move with retry handling in case of USB communication glitches
    for attempt in range(1, retries + 1):
        try:
            stage.move_to(target)
            stage.wait_move()
            return True
        except Exception as e:
            print(f"\nStage error at {target:.6f} mm (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(STAGE_RETRY_DELAY)
    return False

# connect to Thorlabs motorized actuator (25600 microsteps/mm)
print(f"Connecting to stage (S/N: {SERIAL_NO})...")
stage = Thorlabs.KinesisMotor(SERIAL_NO, scale=25600.0)
time.sleep(0.2)
print("Stage connected, scale:", stage.get_scale())

# connect to ESP32: disable DTR/RTS so board doesn't reset into bootloader
print(f"Connecting to ESP32 on {ESP32_PORT}...")
esp32 = serial.Serial(ESP32_PORT, baudrate=BAUDRATE, timeout=SERIAL_TIMEOUT, rtscts=False, dsrdtr=False)
esp32.dtr = False
esp32.rts = False
time.sleep(2.0)
esp32.reset_input_buffer()
esp32.reset_output_buffer()
print("ESP32 connected.")

reset_esp32(esp32)
time.sleep(0.1)

# record initial stage position
start_mm = stage.get_position()
start_raw = stage.get_position(scale=False)
print(f"Start pos: {start_mm:.6f} mm (raw: {start_raw})")

# measure ambient light / dark voltage to subtract from scan data
print(f"Measuring background ({BACKGROUND_N_SAMPLES} samples)...")
background_sum = 0.0
background_count = 0
background_failures = 0

for i in range(BACKGROUND_N_SAMPLES):
    try:
        v_bg = read_esp32_voltage(esp32, step_number=f"bg_{i + 1}")
        background_sum += v_bg
        background_count += 1
    except Exception as e:
        background_failures += 1
        print(f"Background read error {i + 1}: {e}")
    time.sleep(0.05)

avg_background = background_sum / background_count if background_count > 0 else float("nan")
print(f"Background: {avg_background * 1000.0:.4f} mV ({background_count}/{BACKGROUND_N_SAMPLES} samples)")
if not math.isfinite(avg_background):
    raise RuntimeError("Could not obtain a valid background measurement.")

reset_esp32(esp32)
time.sleep(0.1)

print("-" * 65)
print(f"{'Step':>6} {'Target(mm)':>14} {'Actual(mm)':>14} {'Raw':>10} {'Voltage(mV)':>14}")
print("-" * 65)

data_log = []
failed_steps = []
scan_stopped = False

# main scan loop: step across beam and log transmission profile
try:
    for step in range(N_STEPS):
        target = start_mm + (step + 1) * STEP_SIZE
        if not move_stage_safely(stage, target):
            print(f"\nStage communication failed at step {step + 1}.")
            scan_stopped = True
            break

        time.sleep(DWELL_TIME)

        # read photodiode signal and subtract background
        try:
            voltage = read_esp32_voltage(esp32, step_number=step + 1)
            corrected_V = voltage - avg_background
        except Exception as e:
            print(f"\nESP32 error at step {step + 1}: {e}")
            voltage = float("nan")
            corrected_V = float("nan")
            failed_steps.append(step + 1)

        current_mm = target
        current_raw = round((current_mm - start_mm) * 25600.0)

        # check physical encoder position periodically to catch missed steps
        if step == 0 or (step + 1) % POSITION_CHECK_INTERVAL == 0:
            try:
                actual_mm = stage.get_position()
                pos_err_um = (actual_mm - target) * 1000.0
                if abs(pos_err_um) > 2.0:
                    print(f"\nWarning: stage error = {pos_err_um:.2f} um")
            except Exception as e:
                print(f"\nPosition check error at step {step + 1}: {e}")

        rel_pos_um = (current_mm - start_mm) * 1000.0
        v_disp = corrected_V * 1000.0 if math.isfinite(corrected_V) else float("nan")
        print(f"{step + 1:6d} {target:14.6f} {current_mm:14.6f} {current_raw:10d} {v_disp:14.2f}")

        if math.isfinite(voltage):
            data_log.append([
                step + 1, target, current_mm, rel_pos_um, current_raw,
                voltage * 1000.0, avg_background * 1000.0, corrected_V * 1000.0
            ])

except KeyboardInterrupt:
    print("\nScan interrupted by user.")
    scan_stopped = True
except Exception as e:
    print(f"\nScan error: {e}")
    scan_stopped = True
finally:
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    try:
        end_mm = stage.get_position()
        end_raw = stage.get_position(scale=False)
        print(f"Start:  {start_mm:.6f} mm (raw {start_raw})")
        print(f"End:    {end_mm:.6f} mm (raw {end_raw})")
        print(f"Travel: {end_mm - start_mm:.6f} mm")
    except Exception as e:
        print(f"Could not read final stage position: {e}")

    print(f"Valid points: {len(data_log)}/{N_STEPS}")
    print(f"Failed reads: {len(failed_steps)}")

    # save acquired data to CSV
    try:
        csv_filename = get_next_filename()
        with open(csv_filename, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Step", "Target_mm", "Actual_mm", "Rel_Pos_um", "Raw_Steps", "Voltage_mV", "Background_mV", "Corrected_mV"])
            writer.writerows(data_log)
        print(f"Data saved to: {csv_filename}")
    except Exception as e:
        print(f"Could not save CSV: {e}")

    # return stage to starting position
    print("Returning stage to start position...")
    if move_stage_safely(stage, start_mm):
        print("Stage returned.")
    else:
        print("Warning: stage could not be returned automatically.")

    # clean up hardware connections
    try:
        stage.close()
    except Exception:
        pass
    try:
        esp32.close()
    except Exception:
        pass
    print("Done.")
