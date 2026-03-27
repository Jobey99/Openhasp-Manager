openHASP Manager

A simple, all-in-one way to design and manage openHASP touchscreen panels with Home Assistant.

Why This Exists

If you’ve ever set up an openHASP panel the traditional way, you’ll know it can get messy fast. You end up dealing with loads of YAML, trying to keep track of things like p1b2, and writing way more config than should be necessary just to control a light.

openHASP Manager was built to get rid of that headache. Instead of remembering IDs and digging through config files, it talks directly to your panel, reads what’s on the screen, and shows everything in a clean, easy-to-use interface. What used to be confusing and manual becomes straightforward and visual.

The “Point and Click” Approach

This project is all about replacing the YAML-heavy workflow with something much more intuitive:

Visual Design – Build your screen layout in a web-based designer. No need to touch JSON or JSONL.
Auto-Discovery – Press a button on your panel and it instantly shows up in Home Assistant.
Easy Mapping – Pick a Home Assistant entity from a dropdown and link it to a button. No code, no templates, no messing with MQTT.
How It Compares to the Official Integration

There is an official openHASP integration, but it’s built with a different type of user in mind:

Official Integration – Gives you very detailed control over every LVGL object using YAML and Jinja2. It’s powerful, but can be overwhelming unless you’re comfortable with that level of config.
openHASP Manager (This Plugin) – Focuses on simplicity. You design your UI visually, then just point and click to connect buttons to lights, switches, or scenes—no coding required.

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

### 2. Firmware Installation
1. Connect the panel to your computer via USB.
2. Use the openHASP web installer or the ESP32 flash tool to install the latest openHASP firmware.
3. Connect the panel to your local Wi-Fi network via the internal access point (typically named `openhasp-xxxx`).
4. Configure the MQTT settings on the panel to point to your Home Assistant MQTT broker (e.g., Mosquitto). Set the Hostname to a recognizable ID, such as `plate`.

### 3. UI Design
1. Open `designer/index.html` in a web browser.
2. Design your interface using the drag-and-drop editor.
3. Configure your buttons and pages.
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
