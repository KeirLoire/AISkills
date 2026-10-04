---
name: tapo-device-control
description: Control TP-Link Tapo smart home devices (plugs, bulbs, chimes) using automatic local network discovery.
---

# Tapo Device Control

This skill enables the control of TP-Link Tapo smart home devices (smart plugs, light bulbs, power strips, etc.) using automatic local network discovery.

## Purpose

To dynamically locate and control smart plugs and bulbs on the local Wi-Fi network by their friendly names (aliases) without requiring static IP addresses.

---

## Inputs

1. **Credentials**: `TAPO_USERNAME` and `TAPO_PASSWORD` set in the local `.env` file (these are your Tapo cloud account details).
2. **Device Name (Alias)**: The friendly name of the device as named in the Tapo app (e.g., "living-room-plug").
3. **Action**: One of the following:
   - `on`: Turn the device on.
   - `off`: Turn the device off.
   - `toggle`: Toggle the power state.
   - `status`: Retrieve detailed device info, state, and real-time power metrics (if supported).

---

## Detailed Steps

1. **Set Up the Environment**:
   - Ensure a Python virtual environment is activated and dependencies from `requirements.txt` are installed.
   - Ensure the `.env` file contains valid credentials.
2. **Scan/Control**:
   - Run the script with the device alias and the action.
   - The script will first try to connect directly using a cached IP from `tapo_cache.json`.
   - If the device is not at that IP, the script will automatically run a network-wide active IP port scan, locate the device, update the IP cache, and perform the action.
3. **List Devices (Optional)**:
   - Run the script without arguments to discover all Tapo devices on the local network and print a status table.

---

## Script Commands

All commands are run from the project directory:
`skills/home/tapo/scripts/`

- **Scan Network and List Devices**:
  ```powershell
  python tapo_control.py
  ```
- **Turn On a Device**:
  ```powershell
  python tapo_control.py "Living Room Plug" on
  ```
- **Turn Off a Device**:
  ```powershell
  python tapo_control.py "Living Room Plug" off
  ```
- **Toggle Power State**:
  ```powershell
  python tapo_control.py "Living Room Plug" toggle
  ```
- **Get Current Device Status and Power Draw**:
  ```powershell
  python tapo_control.py "Living Room Plug" status
  ```

---

## Edge Cases & Constraints

- **Local Network Dependency**: The control machine must be connected to the *same local subnet/Wi-Fi network* as the Tapo devices.
- **Dynamic IPs**: The script uses a local IP cache to execute commands instantly (<100ms). If a device's IP changes, the first attempt will fail, triggering a full subnet scan which takes 1–2 seconds to complete and update the cache.
- **Third-Party Compatibility**: Tapo cloud credentials are required. You **must enable 'Third-Party Compatibility'** for each device in the Tapo app (Me > Third-Party Services) to allow local control.

---

## Checklist

- [ ] Are `TAPO_USERNAME` and `TAPO_PASSWORD` set correctly in the `.env` file?
- [ ] Is the computer on the same local network as the smart devices?
- [ ] Does `python tapo_control.py` successfully list all active devices?
- [ ] Can you control devices by their exact name?
