# openHASP Manager

A unified toolset for designing and managing openHASP touchscreen panels with Home Assistant.

## Why This Exists

Managing openHASP panels traditionally requires significant manual effort, involving complex YAML configurations in Home Assistant and keeping track of hardware IDs (like `p1b2`). 

This project was built to solve the "ID Translation" problem: instead of the user needing to remember that Page 1, Button 2 is the "Living Room Lamp", the integration simply asks the screen what its labels are and presents them in a standard mapping UI.

### Comparison with Official openHASP Integration
While an official `openhasp` custom component exists, it operates on a different philosophy:
- **Official Integration:** Focuses on granular control of every LVGL property via YAML and Home Assistant templates. It is powerful but requires a high level of configuration manual labor.
- **openHASP Manager (This Plugin):** Focuses on **Auto-Discovery** and **UI-driven mapping**. It is designed for users who want to design their screen visually and then "Point and Click" to connect buttons to lights, switches, or scenes without touching a single line of YAML code.

## Key Challenges Overcome
1. **The ID Gap:** Hardware IDs (e.g., `p1b2`) are hard for humans to manage. This plugin bridged the gap by querying the panel for text labels via MQTT.
2. **State Synchronization Logic:** Keeping a physical button's visual state (on/off) in sync with a Home Assistant entity (which might be changed by voice, app, or automation) is complex. This plugin handles those MQTT subscriptions and state-logic updates automatically.
3. **Template Boilerplate:** Eliminated the need for "On Click" and "On State Change" automation boilerplate for every individual button.

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
3. Set your button IDs (e.g., p1b2 for Page 1, Button 2) and labels.
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
