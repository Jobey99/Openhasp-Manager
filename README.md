# openHASP Manager

A simple, all-in-one way to design and manage openHASP touchscreen panels with Home Assistant.

## Why This Exists

If you’ve ever set up an openHASP panel the traditional way, you’ll know it can get messy fast. You end up dealing with loads of YAML, trying to keep track of hardware IDs like `p1b2`, and writing way more config than should be necessary just to control a light.

**openHASP Manager** was built to get rid of that headache. Instead of remembering IDs and digging through config files, it talks directly to your panel, reads what’s on the screen, and shows everything in a clean, easy-to-use interface. What used to be confusing and manual becomes straightforward and visual.

### The “Point and Click” Approach
This project is all about replacing the YAML-heavy workflow with something much more intuitive:
- **Zero-Code Mapping:** Press a button/gauge on your screen, and it instantly appears in Home Assistant. Just pick the entity you want to control or display (now including Sensors and Thermostats!).
- **Visual UI Designer:** A drag-and-drop editor that generates the necessary JSONL code for your panel.
- **Smart Data Sync:** 
  - **Sensors:** Map a temperature sensor to a Gauge or Label; the integration handles the math and units automatically.
  - **Thermostats:** Map a climate entity to a label or buttons; use `+`/`-` buttons on the panel to change setpoints without any YAML.

### How It Compares to the Official Integration
There is an official openHASP integration, but it’s built with a different type of user in mind:
- **Official Integration** – Gives you very detailed control over every LVGL object using YAML and Jinja2. It’s powerful, but can be overwhelming unless you’re comfortable with that level of config.
- **openHASP Manager (This Plugin)** – Focuses on simplicity. You design your UI visually, then just point and click to connect buttons to lights, switches, or scenes—no coding required.

## Home Assistant Installation

### 🚀 Recommended: Automatic Install via HACS
The easiest way to install and keep this integration updated is through [HACS](https://hacs.xyz/):

1. Open **HACS** in Home Assistant.
2. Click the three dots (⋮) top right and select **Custom repositories**.
3. Paste: `https://github.com/Jobey99/Openhasp-Manager`
4. Select **Integration** and click **Add**.
5. Once added, click the button below or search for "openHASP Manager" in HACS to install.

[![Open your Home Assistant instance and open the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=Openhasp-Manager&owner=Jobey99&category=integration)



## From Scratch Setup Guide

### 1. Hardware Preparation
This guide is specifically tailored for the Elecrow CrowPanel 7.0" HMI (hardware version 3.0).
- Ensure the board is powered via the USB-C port.
- If using expanding modules (such as mmWave sensors), ensure they are not interfering with the I2C bus during setup.

### 2. Firmware Installation
1. Connect the panel to your computer via USB.
2. Use the openHASP web installer or the ESP32 flash tool to install the latest openHASP firmware.
3. Connect the panel to your local Wi-Fi network via the internal access point (typically named `openhasp-xxxx`).
4. Configure the MQTT settings on the panel to point to your Home Assistant MQTT broker (e.g., Mosquitto). Set the Hostname to a recognizable ID, such as `plate`.

### 3. V2 Premium UI Designer
1. Open the UI Designer (or go to your GitHub Pages URL).
2. Design your interface using the drag-and-drop editor:
   - **Advanced Widgets:** Add Sliders (dimming/volume), Arcs, Dropdowns, and Color Wheels!
   - **Layers Panel:** Use the right-sidebar to track all elements, select hidden ones, and reorder them (Bring Forward / Send Backward).
   - **Global Theme Editor:** Change the panel's primary background and accent colors instantly. Click "Export Theme" to generate a `theme.jsonl` file alongside your pages!
   - **Interactive Preview:** Click the 👁 Preview button to interact with your designed buttons and sliders exactly as they will feel on the hardware.
3. Configure your buttons and pages.
4. Copy the generated `pages.jsonl` (and `theme.jsonl`) to your openHASP device!
6. Restart the panel to apply the new UI.

### 4. Integration Configuration
1. Once the Home Assistant integration is installed and the panel is online:
2. Go to the openHASP Manager integration in Home Assistant.
3. Enter the MQTT topic prefix used by your panel (default: `hasp/plate`).
4. On your physical panel, press every button once. The integration will automatically discover these buttons and query their labels.
5. Go to the Integration Options/Configure menu in Home Assistant.
6. Use the entity selectors to map each discovered button to a light, switch, or script.

## Features

### Visual Designer
- Multi-resolution support: presets for common panels (2.4", 3.5", 7", 10.1") and custom dimension support.
- WYSIWYG editor matching the resolution of your specific device.
- Multi-select resizing and alignment tools.
- Integrated Material Design Icon library.
- Export for 16-bit color (RGB565) compatibility.
- Bi-directional JSONL import/export.

### Home Assistant Integration
- Automatic discovery of buttons via MQTT.
- Automatic label retrieval from the panel to ensure buttons are easily identifiable.
- Two-way state synchronization between physical buttons and Home Assistant entities.
- Support for light, switch, fan, script, and scene domains.

## License
MIT
