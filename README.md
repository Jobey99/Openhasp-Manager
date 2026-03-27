# openHASP Manager

A unified toolset for designing and managing openHASP touchscreen panels with Home Assistant.

## Why This Exists

Managing openHASP panels traditionally requires a high degree of "manual labor," involving thousands of lines of complex YAML configuration in Home Assistant just to keep track of basic hardware IDs (like `p1b2`). 

**openHASP Manager** was built to turn this into a modern, **Zero-Code** experience. It solves the "ID Translation" problem: instead of the user needing to remember that Page 1, Button 2 is the "Living Room Lamp," the integration simply asks the screen what its labels are and presents them to you in a standard, graphical interface.

### The "Point and Click" Philosophy
This project replaces the traditional YAML-first workflow with a unified GUI experience:
1. **Visual Design:** Use the web-based designer to create your screen layout (No JSON/JSONL knowledge required).
2. **Auto-Discovery:** Press a button on your physical panel, and it instantly appears in Home Assistant.
3. **Graphical Mapping:** Select a Home Assistant entity from a dropdown to map it to a button. No code, no templates, no manual MQTT subscriptions.

### Comparison with Official openHASP Integration
While an official `openhasp` custom component exists, it operates on a different philosophy:
- **Official Integration:** Focuses on granular control of every individual LVGL object property via heavy YAML and Jinja2 templates. It is powerful for developers but a high barrier for most users.
- **openHASP Manager (This Plugin):** Focuses on **Auto-Discovery** and **Zero-Code Mapping**. It is designed for users who want to design their screen visually and then "Point and Click" to connect buttons to lights, switches, or scenes without writing a single line of code.

## Home Assistant Installation

Click the button below to add the integration to your Home Assistant instance. Note that the custom component files must be present in your custom_components folder for the setup to complete.

[![Open your Home Assistant instance and start a set up flow of a specific integration.](https://my.home-assistant.io/badges/config_flow.svg)](https://my.home-assistant.io/redirect/config_flow/?domain=openhasp_manager)

### Manual Installation
1. Copy the `custom_components/openhasp_manager` directory to your Home Assistant `/config/custom_components/` folder.
2. Restart Home Assistant.
3. Navigate to Settings > Devices & Services > Add Integration and search for "openHASP Manager".

## From Scratch Setup Guide

### 1. Hardware Preparation
This guide is specifically tailored for the Elecrow CrowPanel 7.0" HMI (hardware version 3.0).
- Ensure the board is powered via the USB-C port.
- If using expanding modules (such as mmWave sensors), ensure they are not interfering with the I2C bus during the initial setup or touch screen calibration.

### 2. Firmware Installation
1. Connect the panel to your computer via USB.
2. Use the openHASP web installer or the ESP32 flash tool to install the latest openHASP firmware.
3. Connect the panel to your local Wi-Fi network via the internal access point (typically named `openhasp-xxxx`).
4. Configure the MQTT settings on the panel to point to your Home Assistant MQTT broker (e.g., Mosquitto). Set the Hostname to a recognizable ID, such as `plate`.

### 3. UI Design
1. Open `designer/index.html` in a web browser.
2. Design your interface using the drag-and-drop editor.
3. Set your labels (The designer handles the IDs automatically).
4. Copy the generated JSONL code from the text area.
5. In the openHASP web interface, navigate to the File Editor and paste the code into `pages.jsonl`.
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
