import tkinter as tk
import serial
import threading
import time
import matplotlib
matplotlib.use("TkAgg")  # Safe for interactive GUI + Tkinter
import matplotlib.pyplot as plt
from collections import deque

# ==== CONFIG ====
SERIAL_PORT = '/dev/ttyUSB0'        # Or /dev/ttyACM0 on Linux/macOS
BAUD_RATE = 115200
UPDATE_INTERVAL = 100       # milliseconds
PLOT_ENABLED = True
# ================
latest_readings = {
    "NO2": 0.0,
    "C2H5CH": 0.0,
    "VOC": 0.0,
    "CO": 0.0
}

plot_data = {k: deque(maxlen=100) for k in latest_readings}

running = True  # Flag for stopping threads cleanly

# --- Serial Reading Thread ---
def serial_thread():
    global running
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            while running:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line and ',' in line and not line.lower().startswith("no2"):
                        no2, c2h5ch, voc, co = map(float, line.split(','))
                        latest_readings.update({
                            "NO2": no2,
                            "C2H5CH": c2h5ch,
                            "VOC": voc,
                            "CO": co
                        })
                        for key, val in latest_readings.items():
                            plot_data[key].append(val)
                except (UnicodeDecodeError, ValueError):
                    continue  # Skip malformed lines
    except serial.SerialException as e:
        print(f"[Serial Error] {e}")
    finally:
        print("Serial connection closed.")


# --- Tkinter GUI Thread ---
def start_tk_gui():
    root = tk.Tk()
    root.title("Gas Terminal")
    root.geometry("400x300")
    root.resizable(False, False)

    canvas = tk.Canvas(root, width=400, height=300, bg="black")
    canvas.pack()

    canvas.create_text(200, 20, text="Gas Terminal", fill="blue", font=("Helvetica", 18, "bold"))
    for i in range(5):
        canvas.create_line(0, 50 + i, 400, 50 + i, fill="green")

    sensor_boxes = {
        "NO2": (60, 100),
        "C2H5CH": (240, 100),
        "VOC": (60, 180),
        "CO": (240, 180)
    }

    text_values = {}
    for label, (x, y) in sensor_boxes.items():
        canvas.create_rectangle(x - 40, y, x + 40, y + 40, outline="white", width=2)
        canvas.create_text(x - 40, y - 10, text=f"{label}:", fill="white", anchor="nw", font=("Helvetica", 10, "bold"))
        text_values[label] = canvas.create_text(x - 35, y + 10, text="0.00", fill="white", anchor="nw", font=("Helvetica", 12, "bold"))

    def update_gui():
        for label, text_id in text_values.items():
            canvas.itemconfig(text_id, text=f"{latest_readings[label]:.3f}")
        if running:
            root.after(UPDATE_INTERVAL, update_gui)

    def on_close():
        global running
        running = False
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    update_gui()
    root.mainloop()

# --- Matplotlib Live Plot (MAIN THREAD!) ---
def live_plot():
    fig, axs = plt.subplots(2, 2, figsize=(8, 6))
    keys = list(plot_data.keys())
    titles = ["NO2", "C2H5CH", "VOC", "CO"]

    try:
        while running:
            for i, ax in enumerate(axs.flat):
                ax.clear()
                data = list(plot_data[keys[i]])
                if data:
                    ax.plot(range(len(data)), data)
                    ax.set_ylim(min(data) * 0.9, max(data) * 1.1)
                    ax.set_xlim(0, plot_data[keys[i]].maxlen)
                else:
                    ax.set_ylim(0, 1)
                    ax.set_xlim(0, plot_data[keys[i]].maxlen)
                ax.set_title(titles[i])
                ax.set_xlabel("Samples")
                ax.set_ylabel("ppm")
            plt.tight_layout()
            fig.canvas.draw()
            plt.pause(0.1)
    except KeyboardInterrupt:
        print("[Plot] Interrupted.")
    finally:
        plt.close(fig)


# --- Launch ---
if __name__ == "__main__":
    # Start serial + GUI in threads
    threading.Thread(target=serial_thread, daemon=True).start()
    threading.Thread(target=start_tk_gui, daemon=True).start()

    if PLOT_ENABLED:
        live_plot()  # MAIN THREAD
