// Dashboard cards of Tuya Vacuum Maps, in one file so one resource loads both.
//
// Rooms card, to pick rooms, set the cleaning passes and start cleaning:
//
//   type: custom:tuya-vacuum-maps-rooms-card
//   entity: button.robot_clean_rooms  # optional with a single vacuum
//   title: Clean rooms                # optional
//
// The room switches and passes slider are found from the button's device.
//
// Map card, showing the whole map fitted in a box of a set size, to zoom with
// a pinch or the mouse wheel, drag around and follow the vacuum:
//
//   type: custom:tuya-vacuum-maps-map-card
//   entity: camera.robot_map  # optional with a single vacuum
//   title: Map                # optional
//   height: 400px             # optional, a CSS length or a number of pixels
//   width: 100%               # optional
//   follow_vacuum: true       # optional, start zoomed in on the vacuum
//   follow_zoom: 3            # optional, zoom while following, 1 to 10
//
// Double tap or double click the map to see all of it again.

const PLATFORM = "tuya_vacuum_maps";

// Card texts by language; {count} is replaced with a number
const TRANSLATIONS = {
  en: {
    title: "Clean rooms",
    passes: "Passes",
    clean_one: "Clean {count} room",
    clean_other: "Clean {count} rooms",
    select_rooms: "Select rooms to clean",
    no_button: "No Tuya Vacuum Maps clean button found. Set `entity` to one.",
    no_camera: "No Tuya Vacuum Maps camera found. Set `entity` to one.",
    no_map: "The map isn't available yet.",
    follow: "Follow the vacuum",
    fit: "Show the whole map",
  },
  "zh-Hant": {
    title: "清掃房間",
    passes: "清掃次數",
    clean_one: "清掃 {count} 個房間",
    clean_other: "清掃 {count} 個房間",
    select_rooms: "請選擇要清掃的房間",
    no_button: "找不到 Tuya Vacuum Maps 的清掃按鈕，請將 `entity` 設為該按鈕。",
    no_camera: "找不到 Tuya Vacuum Maps 的地圖攝影機，請將 `entity` 設為該攝影機。",
    no_map: "目前還沒有地圖。",
    follow: "跟隨掃地機",
    fit: "顯示整張地圖",
  },
};

// Traditional Chinese for Home Assistant's zh-Hant and zh-TW style codes,
// English otherwise
function language(hass) {
  const code = (hass.locale?.language || hass.language || "en").toLowerCase();
  return ["zh-hant", "zh-tw", "zh-hk", "zh-mo"].some((prefix) =>
    code.startsWith(prefix)
  )
    ? "zh-Hant"
    : "en";
}

function translate(hass, key, count) {
  const text = TRANSLATIONS[language(hass)][key] ?? TRANSLATIONS.en[key];
  return count === undefined ? text : text.replace("{count}", count);
}

// Entities of this integration in a domain, optionally on one device
function integrationEntities(hass, domain, deviceId) {
  return Object.values(hass.entities || {}).filter(
    (entity) =>
      entity.platform === PLATFORM &&
      entity.entity_id.startsWith(`${domain}.`) &&
      (deviceId === undefined || entity.device_id === deviceId)
  );
}

class TuyaVacuumMapsRoomsCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._renderKey = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    const parts = this._findEntities();
    // Only re-render when something shown changed, so a slider being
    // dragged isn't replaced by every unrelated state update
    const key = JSON.stringify([
      language(hass),
      parts && [
        parts.button,
        parts.passes && hass.states[parts.passes]?.state,
        parts.rooms.map((id) => [
          id,
          hass.states[id]?.state,
          hass.states[id]?.attributes,
        ]),
      ],
    ]);
    if (key !== this._renderKey) {
      this._renderKey = key;
      this._render(parts);
    }
  }

  getCardSize() {
    return 3 + Math.ceil((this._parts?.rooms.length || 0) / 2);
  }

  static getStubConfig(hass) {
    const [button] = integrationEntities(hass, "button");
    return button ? { entity: button.entity_id } : {};
  }

  // The button, passes slider and room switches of the configured vacuum
  _findEntities() {
    const hass = this._hass;
    const buttonId =
      this._config.entity ||
      integrationEntities(hass, "button")[0]?.entity_id;
    const button = buttonId && hass.entities?.[buttonId];
    if (!button) return undefined;

    const deviceId = button.device_id;
    const rooms = integrationEntities(hass, "switch", deviceId)
      .map((entity) => entity.entity_id)
      .filter((id) => hass.states[id]?.attributes.room_id !== undefined)
      // As on the map, top left to bottom right; rooms not drawn on it last
      .sort(
        (a, b) =>
          (hass.states[a].attributes.map_order ?? Infinity) -
            (hass.states[b].attributes.map_order ?? Infinity) ||
          hass.states[a].attributes.room_id - hass.states[b].attributes.room_id
      );
    const passes = integrationEntities(hass, "number", deviceId)[0]?.entity_id;
    return { button: buttonId, passes, rooms };
  }

  _render(parts) {
    this._parts = parts;
    const hass = this._hass;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const root = this.shadowRoot;
    root.innerHTML = `<style>${TuyaVacuumMapsRoomsCard.styles}</style>`;

    const card = document.createElement("ha-card");
    card.header = this._config.title || translate(hass, "title");
    root.appendChild(card);
    const content = document.createElement("div");
    content.className = "content";
    card.appendChild(content);

    if (!parts) {
      content.textContent = translate(hass, "no_button");
      return;
    }

    // Room toggles, showing each selected room's place in the order
    const grid = document.createElement("div");
    grid.className = "rooms";
    for (const id of parts.rooms) {
      const state = hass.states[id];
      const on = state.state === "on";
      const room = document.createElement("button");
      room.className = `room${on ? " on" : ""}`;
      room.disabled = state.state === "unavailable";
      const order = document.createElement("span");
      order.className = "order";
      order.textContent = on ? state.attributes.order : "";
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = state.attributes.room_name ?? state.entity_id;
      room.append(order, name);
      room.addEventListener("click", () =>
        this._call("switch", "toggle", { entity_id: id })
      );
      grid.appendChild(room);
    }
    content.appendChild(grid);

    // Cleaning passes
    if (parts.passes && hass.states[parts.passes]) {
      const passes = hass.states[parts.passes];
      const row = document.createElement("label");
      row.className = "passes";
      const label = document.createElement("span");
      label.textContent = translate(hass, "passes");
      const slider = document.createElement("input");
      slider.type = "range";
      slider.min = passes.attributes.min;
      slider.max = passes.attributes.max;
      slider.step = passes.attributes.step;
      slider.value = passes.state;
      const value = document.createElement("span");
      value.className = "value";
      value.textContent = Number(passes.state);
      slider.addEventListener("input", () => {
        value.textContent = slider.value;
      });
      slider.addEventListener("change", () =>
        this._call("number", "set_value", {
          entity_id: parts.passes,
          value: Number(slider.value),
        })
      );
      row.append(label, slider, value);
      content.appendChild(row);
    }

    // Clean button, only enabled with rooms selected
    const selected = parts.rooms.filter((id) => hass.states[id].state === "on");
    const clean = document.createElement("button");
    clean.className = "clean";
    clean.disabled = selected.length === 0;
    clean.textContent = selected.length
      ? translate(
          hass,
          selected.length === 1 ? "clean_one" : "clean_other",
          selected.length
        )
      : translate(hass, "select_rooms");
    clean.addEventListener("click", () =>
      this._call("button", "press", { entity_id: parts.button })
    );
    content.appendChild(clean);

    this._error = document.createElement("div");
    this._error.className = "error";
    content.appendChild(this._error);
  }

  async _call(domain, service, data) {
    try {
      await this._hass.callService(domain, service, data);
      if (this._error) this._error.textContent = "";
    } catch (err) {
      if (this._error) this._error.textContent = err.message || String(err);
    }
  }
}

TuyaVacuumMapsRoomsCard.styles = `
  .content { padding: 0 16px 16px; display: flex; flex-direction: column; gap: 12px; }
  .rooms { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px; }
  .room {
    display: flex; align-items: center; gap: 6px; min-height: 40px; padding: 6px 10px;
    border: 1px solid var(--divider-color); border-radius: 10px; cursor: pointer;
    background: var(--card-background-color); color: var(--primary-text-color);
    font: inherit; text-align: left;
  }
  .room.on { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color); }
  .room:disabled { opacity: 0.4; cursor: default; }
  .order {
    min-width: 20px; height: 20px; border-radius: 10px; font-size: 12px; font-weight: 600;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .room.on .order { background: var(--text-primary-color); color: var(--primary-color); }
  .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .passes { display: flex; align-items: center; gap: 12px; }
  .passes input { flex: 1; accent-color: var(--primary-color); }
  .value { min-width: 1.5em; text-align: right; font-weight: 600; }
  .clean {
    min-height: 40px; border: none; border-radius: 10px; cursor: pointer; font: inherit; font-weight: 600;
    background: var(--primary-color); color: var(--text-primary-color);
  }
  .clean:disabled { background: var(--disabled-color, #bdbdbd); cursor: default; }
  .error { color: var(--error-color); font-size: 14px; }
  .error:empty { display: none; }
`;

// Highest zoom, as a multiple of the map fitted in the card
const MAX_ZOOM = 10;
const DEFAULT_FOLLOW_ZOOM = 3;
const DEFAULT_HEIGHT = "400px";
// A pointer moving less than this, in pixels, taps instead of dragging
const TAP_DISTANCE = 6;
// Two taps within this many milliseconds are a double tap
const DOUBLE_TAP_MS = 300;

const clampZoom = (zoom) => Math.min(MAX_ZOOM, Math.max(1, zoom));

// A CSS length from the configuration, where a number is in pixels
function cssLength(value, fallback) {
  if (value === undefined || value === null || value === "") return fallback;
  return typeof value === "number" ? `${value}px` : String(value);
}

class TuyaVacuumMapsMapCard extends HTMLElement {
  constructor() {
    super();
    // Sizes in pixels of the map image, and of the box it's shown in
    this._image = undefined;
    this._box = { width: 0, height: 0 };
    // The view: zoom over the fitted map, and the image's offset in the box
    this._zoom = 1;
    this._x = 0;
    this._y = 0;
    this._pointers = new Map();
    this._resizeObserver = new ResizeObserver(() => this._measure());
  }

  setConfig(config) {
    this._config = config || {};
    this._follow = Boolean(this._config.follow_vacuum);
    this._zoom = this._follow ? this._followZoom() : 1;
    this._build();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  connectedCallback() {
    if (this._viewport) this._resizeObserver.observe(this._viewport);
  }

  disconnectedCallback() {
    this._resizeObserver.disconnect();
  }

  getCardSize() {
    const height = parseFloat(cssLength(this._config?.height, DEFAULT_HEIGHT));
    return Math.max(3, Math.ceil((Number.isFinite(height) ? height : 400) / 50));
  }

  static getStubConfig(hass) {
    const [camera] = integrationEntities(hass, "camera");
    return camera ? { entity: camera.entity_id } : {};
  }

  // Settings shown in the dashboard's card editor
  static getConfigForm() {
    const labels = {
      entity: "Map camera",
      title: "Title",
      height: "Height (e.g. 400px)",
      width: "Width (e.g. 100%)",
      follow_vacuum: "Follow the vacuum",
      follow_zoom: "Zoom while following",
    };
    return {
      schema: [
        {
          name: "entity",
          selector: { entity: { domain: "camera", integration: PLATFORM } },
        },
        { name: "title", selector: { text: {} } },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "height", selector: { text: {} } },
            { name: "width", selector: { text: {} } },
          ],
        },
        { name: "follow_vacuum", selector: { boolean: {} } },
        {
          name: "follow_zoom",
          selector: {
            number: { min: 1, max: MAX_ZOOM, step: 0.5, mode: "slider" },
          },
        },
      ],
      computeLabel: (schema) => labels[schema.name],
    };
  }

  _followZoom() {
    return clampZoom(Number(this._config.follow_zoom) || DEFAULT_FOLLOW_ZOOM);
  }

  _cameraId() {
    return (
      this._config.entity ||
      integrationEntities(this._hass, "camera")[0]?.entity_id
    );
  }

  _build() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const root = this.shadowRoot;
    root.innerHTML = `<style>${TuyaVacuumMapsMapCard.styles}</style>`;
    this._resizeObserver.disconnect();

    const card = document.createElement("ha-card");
    if (this._config.title) card.header = this._config.title;
    root.appendChild(card);

    const viewport = document.createElement("div");
    viewport.className = "viewport";
    viewport.style.height = cssLength(this._config.height, DEFAULT_HEIGHT);
    viewport.style.width = cssLength(this._config.width, "100%");
    card.appendChild(viewport);
    this._viewport = viewport;

    const map = document.createElement("img");
    map.className = "map";
    map.alt = "";
    map.draggable = false;
    viewport.appendChild(map);
    this._map = map;

    const message = document.createElement("div");
    message.className = "message";
    viewport.appendChild(message);
    this._message = message;

    const controls = document.createElement("div");
    controls.className = "controls";
    // Taps on the buttons don't drag the map
    controls.addEventListener("pointerdown", (event) => event.stopPropagation());
    this._followButton = this._button("mdi:crosshairs-gps", () =>
      this._setFollow(!this._follow)
    );
    this._fitButton = this._button("mdi:fit-to-screen-outline", () =>
      this._fit()
    );
    controls.append(this._followButton, this._fitButton);
    viewport.appendChild(controls);

    viewport.addEventListener("pointerdown", (event) => this._pointerDown(event));
    viewport.addEventListener("pointermove", (event) => this._pointerMove(event));
    for (const type of ["pointerup", "pointercancel"]) {
      viewport.addEventListener(type, (event) => this._pointerUp(event));
    }
    viewport.addEventListener("wheel", (event) => this._wheel(event), {
      passive: false,
    });

    if (this.isConnected) this._resizeObserver.observe(viewport);
    this._src = undefined;
    this._image = undefined;
    this._update();
  }

  _button(icon, onClick) {
    const button = document.createElement("button");
    const iconElement = document.createElement("ha-icon");
    iconElement.icon = icon;
    button.appendChild(iconElement);
    button.addEventListener("click", onClick);
    return button;
  }

  _update() {
    const hass = this._hass;
    if (!hass || !this._viewport) return;
    this._followButton.title = translate(hass, "follow");
    this._fitButton.title = translate(hass, "fit");
    this._followButton.classList.toggle("on", this._follow);

    const cameraId = this._cameraId();
    const state = cameraId && hass.states[cameraId];
    const picture = state?.attributes.entity_picture;
    if (!picture) {
      // The last map stays while the camera is unavailable
      if (!this._image) {
        this._message.textContent = translate(
          hass,
          cameraId ? "no_map" : "no_camera"
        );
      }
      return;
    }
    this._message.textContent = "";
    this._vacuum = state.attributes.vacuum_position;

    // The image id changes with the map, so the browser loads the new one
    const separator = picture.includes("?") ? "&" : "?";
    const src = hass.hassUrl(
      `${picture}${separator}v=${state.attributes.image_id ?? ""}`
    );
    if (src === this._src) {
      if (this._follow) this._centerOnVacuum(true);
      return;
    }
    this._src = src;
    // Loaded aside first, so the old map stays until the new one is ready
    const loader = new Image();
    loader.onload = () => {
      if (this._src !== src) return;
      this._map.src = src;
      const size = { width: loader.naturalWidth, height: loader.naturalHeight };
      const resized =
        size.width !== this._image?.width || size.height !== this._image?.height;
      this._image = size;
      this._map.style.width = `${size.width}px`;
      this._map.style.height = `${size.height}px`;
      if (resized) this._layout(false);
      else if (this._follow) this._centerOnVacuum(true);
    };
    loader.src = src;
  }

  _measure() {
    const rect = this._viewport.getBoundingClientRect();
    if (rect.width === this._box.width && rect.height === this._box.height) {
      return;
    }
    this._box = { width: rect.width, height: rect.height };
    this._layout(false);
  }

  // Place the map after the box or the image changed size
  _layout(animate) {
    if (this._follow) this._centerOnVacuum(animate);
    else this._show(animate);
  }

  _fitScale() {
    if (!this._image || !this._box.width) return 1;
    return Math.min(
      this._box.width / this._image.width,
      this._box.height / this._image.height
    );
  }

  // Centre the whole map; zoomed in, let any point of it reach the centre of
  // the box, e.g. the vacuum near the map's edge, but no further
  _clamp() {
    const scale = this._fitScale() * this._zoom;
    const clampAxis = (offset, box, size) =>
      this._zoom === 1
        ? (box - size * scale) / 2
        : Math.min(box / 2, Math.max(box / 2 - size * scale, offset));
    this._x = clampAxis(this._x, this._box.width, this._image.width);
    this._y = clampAxis(this._y, this._box.height, this._image.height);
  }

  _show(animate) {
    if (!this._image || !this._box.width) return;
    this._clamp();
    const scale = this._fitScale() * this._zoom;
    this._map.style.transition = animate ? "transform 0.4s ease" : "none";
    this._map.style.transform = `translate(${this._x}px, ${this._y}px) scale(${scale})`;
    this._map.classList.add("shown");
  }

  _centerOnVacuum(animate) {
    if (this._image && Array.isArray(this._vacuum)) {
      const scale = this._fitScale() * this._zoom;
      this._x = this._box.width / 2 - this._vacuum[0] * this._image.width * scale;
      this._y =
        this._box.height / 2 - this._vacuum[1] * this._image.height * scale;
    }
    this._show(animate);
  }

  _setFollow(follow) {
    this._follow = follow;
    this._followButton.classList.toggle("on", follow);
    if (follow) {
      this._zoom = this._followZoom();
      this._centerOnVacuum(true);
    }
  }

  _fit() {
    this._setFollow(false);
    this._zoom = 1;
    this._show(true);
  }

  // Zoom keeping the point (x, y) of the box still, or the vacuum centred
  _zoomAt(x, y, zoom) {
    zoom = clampZoom(zoom);
    if (this._follow) {
      this._zoom = zoom;
      this._centerOnVacuum(false);
      return;
    }
    const ratio = zoom / this._zoom;
    this._x = x - (x - this._x) * ratio;
    this._y = y - (y - this._y) * ratio;
    this._zoom = zoom;
    this._show(false);
  }

  // Position of a pointer in the box
  _point(event) {
    const rect = this._viewport.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  // Distance between and midpoint of the two pointers of a pinch
  _pinch() {
    const [a, b] = [...this._pointers.values()];
    return {
      distance: Math.hypot(a.x - b.x, a.y - b.y),
      x: (a.x + b.x) / 2,
      y: (a.y + b.y) / 2,
    };
  }

  _pointerDown(event) {
    try {
      // Keeps the gesture going when a finger leaves the card
      this._viewport.setPointerCapture(event.pointerId);
    } catch {
      // The pointer is already gone
    }
    this._pointers.set(event.pointerId, this._point(event));
    if (this._pointers.size === 1) {
      this._start = this._point(event);
      this._moved = false;
    } else {
      // A pinch isn't a tap
      this._moved = true;
      this._lastPinch = this._pointers.size === 2 ? this._pinch() : undefined;
    }
  }

  _pointerMove(event) {
    const last = this._pointers.get(event.pointerId);
    if (!last) return;
    const point = this._point(event);
    this._pointers.set(event.pointerId, point);

    if (this._pointers.size === 1) {
      if (
        !this._moved &&
        Math.hypot(point.x - this._start.x, point.y - this._start.y) >
          TAP_DISTANCE
      ) {
        this._moved = true;
        // Dragging the map stops following the vacuum
        if (this._follow) this._setFollow(false);
      }
      if (this._moved) {
        this._x += point.x - last.x;
        this._y += point.y - last.y;
        this._show(false);
      }
    } else if (this._pointers.size === 2 && this._lastPinch) {
      const pinch = this._pinch();
      if (!this._follow) {
        this._x += pinch.x - this._lastPinch.x;
        this._y += pinch.y - this._lastPinch.y;
      }
      this._zoomAt(
        pinch.x,
        pinch.y,
        this._zoom * (pinch.distance / (this._lastPinch.distance || 1))
      );
      this._lastPinch = pinch;
    }
  }

  _pointerUp(event) {
    if (!this._pointers.delete(event.pointerId)) return;
    this._lastPinch = this._pointers.size === 2 ? this._pinch() : undefined;
    if (this._pointers.size > 0 || this._moved) return;

    // A double tap shows the whole map
    const now = Date.now();
    if (now - (this._lastTap || 0) < DOUBLE_TAP_MS) {
      this._lastTap = 0;
      this._fit();
    } else {
      this._lastTap = now;
    }
  }

  _wheel(event) {
    event.preventDefault();
    const point = this._point(event);
    this._zoomAt(point.x, point.y, this._zoom * Math.exp(-event.deltaY * 0.002));
  }
}

TuyaVacuumMapsMapCard.styles = `
  ha-card { overflow: hidden; }
  .viewport {
    position: relative; overflow: hidden; margin: 0 auto; max-width: 100%;
    touch-action: none; user-select: none; -webkit-user-select: none; cursor: grab;
  }
  .viewport:active { cursor: grabbing; }
  .map {
    position: absolute; top: 0; left: 0; max-width: none; transform-origin: 0 0;
    pointer-events: none; visibility: hidden;
  }
  .map.shown { visibility: visible; }
  .message {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    padding: 16px; text-align: center; color: var(--secondary-text-color);
  }
  .message:empty { display: none; }
  .controls { position: absolute; top: 8px; right: 8px; display: flex; flex-direction: column; gap: 6px; }
  .controls button {
    width: 36px; height: 36px; padding: 0; border: none; border-radius: 18px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    background: var(--card-background-color); color: var(--primary-text-color);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3); --mdc-icon-size: 20px;
  }
  .controls button.on { background: var(--primary-color); color: var(--text-primary-color); }
`;

const CARDS = [
  {
    type: "tuya-vacuum-maps-rooms-card",
    element: TuyaVacuumMapsRoomsCard,
    name: "Tuya Vacuum Maps Rooms",
    description: "Pick rooms, set the cleaning passes and start cleaning.",
  },
  {
    type: "tuya-vacuum-maps-map-card",
    element: TuyaVacuumMapsMapCard,
    name: "Tuya Vacuum Maps Map",
    description: "The vacuum map, to zoom, drag around and follow the vacuum.",
  },
];

// The cards may be loaded twice, e.g. as a dashboard resource and with the page
for (const { type, element, name, description } of CARDS) {
  if (customElements.get(type)) continue;
  customElements.define(type, element);

  // Shows in the browser console that the card was loaded
  console.info(`${type} loaded`);

  window.customCards = window.customCards || [];
  window.customCards.push({ type, name, description });
}
