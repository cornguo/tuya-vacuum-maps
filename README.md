# Tuya Vacuum Maps

🏠 View Real-Time Vacuum Maps In Home Assistant.<br>
This component adds a new camera which polls the Tuya Cloud API for the latest realtime map data.<br>
This project is primarily focused on Lefant vacuums, but aims to support all Tuya vacuums.

## Changes in This Fork

This is a fork of [jaidenlabelle/tuya-vacuum-maps](https://github.com/jaidenlabelle/tuya-vacuum-maps) with the following changes:

**New features**
- **Singapore data center**: `https://openapi-sg.iotbing.com` can be selected as the server.
- **Tuya Local setup**: if [Tuya Local](https://github.com/make-all/tuya-local) is installed, setup can pick one of its devices to fill in the device ID and name.
- **Room labels**: each room is labelled on the map with its name and ID, e.g. `客廳 (ID: 0)`. Non-ASCII names (such as Chinese) are drawn with Noto Sans TC, downloaded once on first use into `config/.cache/tuya_vacuum_maps/`.

**Fixes**
- **Maps with several rooms failed to render**: the room parser in `tuya-vacuum` didn't skip each room's outline points, so every room after the first was read from the wrong place (`UnicodeDecodeError`).
- **"Unknown map type: 3" warning**: no longer logged for map types 2 (incremental path) and 3 (planning path), which Tuya documents but aren't needed for the map.
- **Blocking calls in the event loop**: fetching and rendering the map now run outside Home Assistant's event loop, fixing the "Detected blocking call ... inside the event loop" warning.
- **No unique ID**: the map camera now has a unique ID and a device, so it can be managed from the UI. If the vacuum is set up in Tuya Local, the camera appears on that device's page.

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cornguo&repository=tuya-vacuum-maps&category=integration)

## Installation

### Installing Manually

To install this integration manually, add the contents of `custom_components` to your Home Assistants `custom_components` folder and reboot.

### Installing using HACS

1. [Install HACS](https://www.hacs.xyz/docs/use/) if its not already installed.
1. Click the **Add to HACS** button above, or add this repository to HACS by following this guide: [HACS: Add Custom Repository](https://www.hacs.xyz/docs/faq/custom_repositories/).
3. Search for this integration using the HACS browser inside Home Assistant, and install.

## Compatibility List

This is a list of tested devices.

| Device                                                | Support                           |
| ----------------------------------------------------- | --------------------------------- |
| Lefant M1 | Supported |
| Lefant M2 Pro | Supported |
| Lefant N3 | Supported |
| Lebluelu SL60D | Supported |
| Lebluelu SL68 | Supported |
| Neatsvor X600 Pro | Supported |

## Development Environment

It's recommended to set up a development environment if you want to make changes to this component.

### Prerequisites

- [A Visual Studio Code + devcontainer development environment](https://developers.home-assistant.io/docs/development_environment)

### Getting Started

1. Once the devcontainer is created, fork this repository.
2. Go to the folder containing the `homeassistant-core` folder, it should be called `workspaces`.
3. Once your fork is created, make sure your terminal path is set to `/workspaces` and run `git clone <url>`.
4. To make testing easier, create a symlink to the component in your Home Assistant devcontainer.
   - Example: `ln -s /workspaces/tuya-vacuum-maps/custom_components/tuya_vacuum_maps /workspaces/homeassistant-core/config/custom_components`
5. For development, it's recommended you use a virtual environment.
   1. Create a new virtual environment (Run in the root `/tuya-vacuum-maps` folder):
      - `python -m venv venv`
   2. Activate the virtual environment:
      - `source ./venv/bin/activate`

## Special Thanks

- [Tuya Cloud Vacuum Map Extractor](https://github.com/oven-lab/tuya_cloud_map_extractor) by [@oven-lab](https://github.com/oven-lab)
