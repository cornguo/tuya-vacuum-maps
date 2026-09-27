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
- **Current room sensor**: `sensor.<vacuum>_current_room` shows the room the vacuum is in, from the end of its path on the map (the nearest room within 25 cm when it's on a wall, e.g. docked), with the room's ID as an attribute. It's as current as the map.
- **Virtual walls and no-go zones**: drawn on the map in 50% transparent red, as lines and blocks. They're read from the vacuum's reports, which takes one more Tuya Cloud request per map update.
- **Thinner cleaning path**: the path is drawn 3 px wide instead of 8, so it no longer covers the room colours and labels.
- **Room cleaning**: a switch per room, a clean passes slider (1–3) and a "Clean selected rooms" button start cleaning the chosen rooms, in the order they were selected. See [Cleaning Rooms](#cleaning-rooms).
- **Rooms dashboard card**: a built-in card with a toggle per room, laid out as the rooms appear on the map and numbered in cleaning order, plus the passes slider and clean button. See [Dashboard Card](#dashboard-card).
- **Translations**: the setup flow, entity names, error messages and the rooms card are in English and Traditional Chinese (繁體中文).

**Fixes**
- **Maps with several rooms failed to render**: the room parser in `tuya-vacuum` didn't skip each room's outline points, so every room after the first was read from the wrong place (`UnicodeDecodeError`).
- **"Unknown map type: 3" warning**: no longer logged for map types 2 (incremental path) and 3 (planning path), which Tuya documents but aren't needed for the map.
- **Blocking calls in the event loop**: fetching and rendering the map now run outside Home Assistant's event loop, fixing the "Detected blocking call ... inside the event loop" warning.
- **No unique ID**: the map camera now has a unique ID and a device, so it can be managed from the UI. If the vacuum is set up in Tuya Local, the camera appears on that device's page.
- **Entity ID got a `_2` suffix**: "Recreate entity ID" no longer adds `_2`. When the vacuum is set up in Tuya Local, the camera's entity ID is based on the vacuum's, e.g. `vacuum.robot` → `camera.robot_map`.
- **Fewer Tuya Cloud requests**: the access token is reused until it expires instead of being fetched before every request, halving the Tuya Cloud API calls per map update (from 4 to 2), and the unused planning-path file is no longer downloaded.
- **Tuya Local's connection used when available**: if the vacuum is set up in Tuya Local, its status and no-go zones are read from Tuya Local, and room cleaning commands are sent through it, so each map update needs one Tuya Cloud request (the map itself) and cleaning doesn't need the cloud. The map is only available from the cloud: the vacuum doesn't send it over the local network. Without Tuya Local, or if using it fails, the Tuya Cloud API is used.
- **Slower updates while docked**: the map is fetched every 60 s while the vacuum is charging, charged, on standby or asleep, and every 10 s otherwise; starting a room clean updates it right away.
- **No re-rendering of unchanged maps**: when the map files, no-go zones and font haven't changed, the last image is reused instead of being drawn again (about 150 ms of CPU each time). No-go zones are blended only where they are, not across the whole image.
- **Rooms card stopped working with the map**: when a map update failed, the room switches, passes slider and clean button became unavailable with the camera. They now keep working with the last known rooms; only the camera and current room sensor show the failed update.
- **Map stopped updating**: the vacuum only uploads its map to the Tuya Cloud when asked, e.g. by its app while showing the map, so the map froze with the app closed. After each update the integration now asks it to upload a fresh map for the next one (through Tuya Local's connection when available).
- **Dock drawn in the wrong place**: the dock marker was drawn at the map's origin; it's now drawn where the vacuum reports the dock, so a parked vacuum shows on it.

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cornguo&repository=tuya-vacuum-maps&category=integration)

## Installation

### Installing Manually

To install this integration manually, add the contents of `custom_components` to your Home Assistants `custom_components` folder and reboot.

### Installing using HACS

1. [Install HACS](https://www.hacs.xyz/docs/use/) if its not already installed.
1. Click the **Add to HACS** button above, or add this repository to HACS by following this guide: [HACS: Add Custom Repository](https://www.hacs.xyz/docs/faq/custom_repositories/).
3. Search for this integration using the HACS browser inside Home Assistant, and install.

## Cleaning Rooms

For vacuums whose map has rooms, the integration adds:

- **A switch per room** (`switch.<vacuum>_room_<id>`), named after the room in the vacuum's app. Rooms are cleaned in the order their switches were turned on, shown in each switch's `order` attribute.
- **Clean passes** (`number.<vacuum>_clean_passes`): how many times each room is cleaned, 1–3.
- **Clean selected rooms** (`button.<vacuum>_clean_rooms`): starts cleaning the selected rooms.

`<vacuum>` is the Tuya Local vacuum's entity ID (e.g. `robot` for `vacuum.robot`), or the integration entry's name otherwise.

The command is sent through Tuya Local's connection when the vacuum is set up there, and through the Tuya Cloud API otherwise. It has been tested on a Hitachi RV-X20DPA, which uses protocol version 0 of Tuya's laser robot vacuum protocol; other vacuums may use another version.

### Dashboard Card

The integration adds a **Tuya Vacuum Maps Rooms** card to the dashboard card picker. It shows a toggle per room with its place in the cleaning order, the passes slider and the clean button, and picks up new rooms by itself:

```yaml
type: custom:tuya-vacuum-maps-rooms-card
entity: button.robot_clean_rooms  # optional with a single vacuum
title: Clean rooms                # optional
```

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
| Hitachi RV-X20DPA | Supported |

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
