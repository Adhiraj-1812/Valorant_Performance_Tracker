import psutil
import GPUtil
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetTemperature, nvmlShutdown, NVML_TEMPERATURE_GPU
import json
from datetime import datetime
import os
import matplotlib.pyplot as plt
import matplotlib.animation as animation

def get_cpu_temperature():
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    temps = psutil.sensors_temperatures()
    if not temps:
        return None
    if "coretemp" in temps:
        cpu_temps = temps["coretemp"]
    elif "thermal_zone0" in temps:
        cpu_temps = temps["thermal_zone0"]
    else:
        return None
    temperature_data = {sensor.label if sensor.label else "CPU": f"{sensor.current} °C" for sensor in cpu_temps}
    return temperature_data


def get_ram_usage():
    ram = psutil.virtual_memory()
    ram_data = {
        "Total RAM": f"{ram.total / (1024 ** 2):.2f} MB",  # Convert bytes to MB
        "Used RAM": f"{ram.used / (1024 ** 2):.2f} MB",
        "Available RAM": f"{ram.available / (1024 ** 2):.2f} MB",
        "RAM Usage": f"{ram.percent}%"
    }
    return ram_data


def get_gpu_usage():
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return None
        usage_data = {gpu.name: float(gpu.load * 100) for gpu in gpus}  # Ensure float values
        return usage_data
    except Exception as e:
        print(f"Error getting GPU usage: {e}")
        return None


def get_gpu_vram_usage():
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return None
        vram_data = {gpu.name: {"Used": gpu.memoryUsed, "Total": gpu.memoryTotal} for gpu in gpus}  # Store as numbers
        return vram_data
    except Exception as e:
        print(f"Error getting VRAM usage: {e}")
        return None


def get_gpu_temperature():
    try:
        gpus = GPUtil.getGPUs()
        if not gpus:
            return None
        temp_data = {}
        for i, gpu in enumerate(gpus, start=1):
            try:
                if "NVIDIA" in gpu.name:
                    nvmlInit()
                    handle = nvmlDeviceGetHandleByIndex(i - 1)  
                    temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)  
                    nvmlShutdown()
                elif "AMD" in gpu.name:
                    temps = psutil.sensors_temperatures()
                    temp = temps.get("amdgpu", [{"current": None}])[0]["current"]
                else:
                    temp = None
                
                if temp is not None:
                    temp_data[f"GPU {i} : {gpu.name}"] = f"{temp} °C"
            except Exception as e:
                print(f"Error getting temperature for GPU {i}: {e}")
                continue
                
        return temp_data if temp_data else None
    except Exception as e:
        print(f"Error in GPU temperature monitoring: {e}")
        return None


def log_performance_data(cpu_usage, cpu_temp, gpu_usage, gpu_temp, vram_usage, ram_usage):
    data = {
        "Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "CPU Usage": f"{cpu_usage}%",
        "CPU Temperature": cpu_temp,
        "GPU Usage": gpu_usage,
        "GPU VRAM": vram_usage,
        "GPU Temperature": gpu_temp,
        "RAM Usage": ram_usage
    }
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(script_dir, "performance_log.json")
    with open(log_path, "a") as log_file:
        json.dump(data, log_file, indent=4)
        log_file.write("\n")


def update_plot(frame):
    global cpu_usage, gpu_usage, ram_usage, vram_usage, cpu_temp_data, gpu_temp_data, ram_usage_data, vram_usage_data
    try:
        cpu_usage = psutil.cpu_percent()
        gpu_usage = get_gpu_usage()
        ram_usage = get_ram_usage()
        vram_usage = get_gpu_vram_usage()
        gpu_temp = get_gpu_temperature()

        current_gpu = next(iter(gpu_usage.values())) if gpu_usage else 0
        ram_usage_value = float(ram_usage["RAM Usage"].strip('%')) if ram_usage else 0
        gpu_temp_value = float(next(iter(gpu_temp.values())).split()[0]) if gpu_temp else 0
        vram_stats = next(iter(vram_usage.values())) if vram_usage else {"Used": 0, "Total": 1}
        vram_percent = (vram_stats["Used"] / vram_stats["Total"]) * 100

        # Update data arrays in place (do not reassign!)
        gpu_temp_data.append(gpu_temp_value)
        ram_usage_data.append(ram_usage_value)
        vram_usage_data.append(vram_percent)
        if len(gpu_temp_data) > 50:
            del gpu_temp_data[0]
            del ram_usage_data[0]
            del vram_usage_data[0]

        # Remove all text objects from ax[0]
        for txt in ax[0].texts[:]:
            txt.remove()
        # Add new text objects
        ax[0].text(0.5, 0.8, f"CPU: {cpu_usage:.1f}%", ha='center', va='center', fontsize=20, fontweight='bold', color='#00BFFF', alpha=0.95)
        ax[0].text(0.5, 0.2, f"GPU: {current_gpu:.1f}%", ha='center', va='center', fontsize=20, fontweight='bold', color='#00FF99', alpha=0.95)

        # Update line data
        gpu_line.set_ydata(gpu_temp_data)
        ram_line.set_ydata(ram_usage_data)
        vram_line.set_ydata(vram_usage_data)
        gpu_line.set_xdata(range(len(gpu_temp_data)))
        ram_line.set_xdata(range(len(ram_usage_data)))
        vram_line.set_xdata(range(len(vram_usage_data)))

        # Update temperature range
        current_temp = gpu_temp_data[-1]
        min_temp = max(0, current_temp - 10)
        max_temp = min(100, min_temp + 20)
        if min_temp == 0:
            max_temp = 20
        elif max_temp == 100:
            min_temp = 80
        ax[1].set_ylim(min_temp, max_temp)
        ax[1].set_xlim(0, 50)

        # Update legends (force redraw)
        ax[1].legend([gpu_line], [f"GPU: {current_temp:.1f}°C"], loc='upper left')
        ax[2].legend([ram_line], [f"RAM: {ram_usage_value:.1f}%"], loc='upper left')
        ax[3].legend([vram_line], [f"VRAM: {vram_percent:.1f}%"], loc='upper left')

        # Update RAM memory range
        ram_highest = ram_usage_data[-1]
        ram_min = max(0, ram_highest - 12.5)
        ram_max = min(100, ram_min + 25)
        if ram_min == 0:
            ram_max = 25
        elif ram_max >= 100:
            ram_min = 75
            ram_max = 100
        ax[2].set_ylim(ram_min, ram_max)
        ax[2].set_xlim(0, 50)
        # Update VRAM memory range
        vram_highest = vram_usage_data[-1]
        vram_min = max(0, vram_highest - 12.5)
        vram_max = min(100, vram_min + 25)
        if vram_min == 0:
            vram_max = 25
        elif vram_max >= 100:
            vram_min = 75
            vram_max = 100
        ax[3].set_ylim(vram_min, vram_max)
        ax[3].set_xlim(0, 50)

        # Restore axis ticks, labels, and grid for all axes except ax[0]
        for i, axis in enumerate([ax[1], ax[2], ax[3]], start=1):
            axis.set_xticks(range(0, 51, 5))
            axis.set_xlabel("Time (seconds)", color='#B0B8C1')
            if i == 1:
                axis.set_ylabel("Temperature (°C)", color='#00FF99')
                axis.tick_params(axis='y', colors='#00FF99')
            elif i == 2:
                axis.set_ylabel("RAM Usage (%)", color='#3399FF')
                axis.yaxis.set_major_locator(plt.MultipleLocator(5))
                axis.tick_params(axis='y', colors='#3399FF')
            elif i == 3:
                axis.set_ylabel("VRAM Usage (%)", color='#B266FF')
                axis.yaxis.set_major_locator(plt.MultipleLocator(5))
                axis.tick_params(axis='y', colors='#B266FF')
            axis.grid(True, alpha=0.25, color='#444')
            axis.spines['bottom'].set_color('#888')
            axis.spines['top'].set_color('#888')
            axis.spines['left'].set_color('#888')
            axis.spines['right'].set_color('#888')
        return [ax[0], ax[1], ax[2], ax[3], gpu_line, ram_line, vram_line]
    except Exception as e:
        print(f"Error updating plot: {e}")
        return []

cpu_usage = psutil.cpu_percent(interval=0.5)
print(f"Cpu usage: {cpu_usage}%")

cpu_temp = get_cpu_temperature()
print(f"CPU temperature: {cpu_temp}")

gpu_usage = get_gpu_usage()
print (f"GPU usage: {gpu_usage}%")

gpu_temp = get_gpu_temperature()
print (f"GPU Temperature: {gpu_temp}")

vram_usage = get_gpu_vram_usage()
print (f"GPU VRAM Usage: {vram_usage}")

ram_usage = get_ram_usage()
print(f"RAM usage: {ram_usage}")

# Initialize global variables for storing data
cpu_temp_data = []
gpu_temp_data = []
ram_usage_data = []
vram_usage_data = []

def cleanup():
    """Clean up resources before exit"""
    try:
        nvmlShutdown()
    except:
        pass
    plt.close('all')

try:
    # Create figure and subplots with dynamic layout
    fig = plt.figure(figsize=(11, 7.5))  # Slightly smaller figure
    gs = plt.GridSpec(4, 1, height_ratios=[0.5, 1, 1, 1])
    ax = [plt.subplot(gs[i]) for i in range(4)]
    plt.style.use('dark_background')
    fig.patch.set_facecolor((0.08, 0.08, 0.12, 0.85))  # Translucent dark grey RGBA
    for a in ax:
        a.set_facecolor((0.12, 0.12, 0.16, 0.85))  # Slightly lighter translucent dark grey

    # Set up initial data
    initial_data = [0] * 50  # Start with 50 zero points
    
    # Initialize plot lines
    ax[0].axis("off")
    ax[0].set_title("System Usage", pad=10, fontsize=12, color='#B0B8C1')
    
    # GPU Temperature plot
    gpu_line, = ax[1].plot(initial_data, color='#00FF99', label="GPU Temp (°C)", linewidth=2)
    ax[1].set_ylabel("Temperature (°C)", color='#00FF99', fontsize=11)
    ax[1].set_ylim(0, 20)  # Initial range
    ax[1].tick_params(axis='y', colors='#00FF99', labelsize=10)
    ax[1].grid(True, alpha=0.25, color='#444')
    ax[1].set_title("GPU Temperature", pad=10, color='#B0B8C1', fontsize=13)
    ax[1].legend(loc='upper left', facecolor='#222', edgecolor='#444', labelcolor='#00FF99', fontsize=10)
    
    # Memory Usage plot (RAM)
    ram_line, = ax[2].plot(initial_data, color='#3399FF', label="RAM Usage (%)", linewidth=2)
    ax[2].set_ylabel("RAM Usage (%)", color='#3399FF', fontsize=11)
    ax[2].set_ylim(0, 25)  # Initial range
    ax[2].grid(True, alpha=0.25, color='#444')
    ax[2].set_title("RAM Usage", pad=10, color='#B0B8C1', fontsize=13)
    ax[2].yaxis.set_major_locator(plt.MultipleLocator(5))
    ax[2].legend(loc='upper left', facecolor='#222', edgecolor='#444', labelcolor='#3399FF', fontsize=10)

    # VRAM Usage plot (separate)
    vram_line, = ax[3].plot(initial_data, color='#B266FF', label="VRAM Usage (%)", linewidth=2)
    ax[3].set_ylabel("VRAM Usage (%)", color='#B266FF', fontsize=11)
    ax[3].set_ylim(0, 25)  # Initial range
    ax[3].grid(True, alpha=0.25, color='#444')
    ax[3].set_title("VRAM Usage", pad=10, color='#B0B8C1', fontsize=13)
    ax[3].yaxis.set_major_locator(plt.MultipleLocator(5))
    ax[3].legend(loc='upper left', facecolor='#222', edgecolor='#444', labelcolor='#B266FF', fontsize=10)

    # Set up x-axis for all plots except ax[0]
    for axis in [ax[1], ax[2], ax[3]]:
        axis.set_xlim(0, 50)
        axis.set_xticks(range(0, 51, 5))
        axis.set_xticklabels([str(i) for i in range(0, 51, 5)], color='#B0B8C1', fontsize=10)
        axis.set_xlabel("Time (seconds)", color='#B0B8C1', fontsize=11)
        axis.spines['bottom'].set_color('#888')
        axis.spines['top'].set_color('#888')
        axis.spines['left'].set_color('#888')
        axis.spines['right'].set_color('#888')

    # Setup animation
    ani = animation.FuncAnimation(
        fig,
        update_plot,
        interval=1000,  # Update every second
        blit=False,  # Set blit to False to ensure axes, ticks, and grid update
        cache_frame_data=False
    )
    
    plt.subplots_adjust(hspace=0.75, top=0.92, bottom=0.07)  # Further increase vertical spacing and adjust margins
    plt.show()

except Exception as e:
    print(f"Error running performance tracker: {e}")
finally:
    cleanup()
