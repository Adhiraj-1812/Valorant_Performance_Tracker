import psutil
import GPUtil
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetTemperature, nvmlShutdown, NVML_TEMPERATURE_GPU
import json
from datetime import datetime
import os

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
    gpus = GPUtil.getGPUs()
    if not gpus:
        return None
    usage_data = {gpu.name : f"{gpu.load*100}%" for gpu in gpus}
    return usage_data


def get_gpu_vram_usage():
    gpus = GPUtil.getGPUs()
    if not gpus:
        return None
    vram_data = {gpu.name : {"Used" : f"{gpu.memoryUsed} MB" , "Total" : f"{gpu.memoryTotal} MB"} for gpu in gpus}
    return vram_data


def get_gpu_temperature():
    try:
        nvmlInit()
        gpus = GPUtil.getGPUs()
        if not gpus:
            return None
        temp_data = {}
        for i, gpu in enumerate(gpus, start=1):
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
            temp_data[f"GPU {i} : {gpu.name}"] = f"{temp} °C"
        nvmlShutdown()
        return temp_data
    except Exception as e:
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

log_performance_data(cpu_usage, cpu_temp, gpu_usage, gpu_temp, vram_usage, ram_usage)