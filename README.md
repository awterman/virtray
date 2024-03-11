# Virtray

This utility provides a convenient system tray application for managing Virtual Machines (VMs) through libvirt with a focus on user-friendly interaction. Leveraging libvirt, the application allows users to start, stop, save, and restore VMs directly from the system tray, enhancing the efficiency of VM management.

## Features

- System Tray Integration: Quick access to manage VMs directly from the system tray.
- VM Management: Start, force shutdown, save, and restore VMs with simple menu options.
- Automatic VM Discovery: Automatically detects and lists all VMs configured in libvirt.
- Customizable VM Actions: Provides custom actions such as opening the VM console via virt-manager.
- Configuration via TOML: VMs and icons can be configured easily using a TOML configuration file.

## Prerequisites

To use this utility, ensure that you have the following installed:

- Python 3.6 or higher
- libvirt and its Python bindings
- PySide2 for the system tray application
- The wmctrl utility for window management actions
- TOML and Pydantic libraries for configuration management

## Installation

1. Clone this repository or download the source code.

2. Install the required Python dependencies:

```bash
pip install libvirt-python PySide2 toml pydantic
```

3. Ensure `virt-manager` and `wmctrl` are installed on your system.

## Configuration

Create a `config.toml` file in the root directory with the following structure to define the VMs you wish to manage and their associated icons:

```toml
[[items]]
icon = "path/to/icon1.png"
domain = "VM1_Name"

[[items]]
icon = "path/to/icon2.png"
domain = "VM2_Name"
```

- `icon`: Path to the icon displayed in the system tray for the VM.
- `domain`: The name of the VM as recognized by libvirt.

## Usage

Run the application with:

```bash
python path/to/virtray.py
```

Optionally, specify a custom configuration file:

```bash
python path/to/virtray.py custom_config.toml
```

Interact with the VMs through the system tray icon that appears. Right-click the icon to see the available actions for each configured VM.

## License

This project is open-source and available under the MIT License.
