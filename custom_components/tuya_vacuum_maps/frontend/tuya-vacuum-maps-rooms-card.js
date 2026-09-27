// Dashboard card to pick rooms, set the cleaning passes and start cleaning.
//
//   type: custom:tuya-vacuum-maps-rooms-card
//   entity: button.robot_clean_rooms  # optional with a single vacuum
//   title: Clean rooms                # optional
//
// The room switches and passes slider are found from the button's device.

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
  },
  "zh-Hant": {
    title: "清掃房間",
    passes: "清掃次數",
    clean_one: "清掃 {count} 個房間",
    clean_other: "清掃 {count} 個房間",
    select_rooms: "請選擇要清掃的房間",
    no_button: "找不到 Tuya Vacuum Maps 的清掃按鈕，請將 `entity` 設為該按鈕。",
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

customElements.define("tuya-vacuum-maps-rooms-card", TuyaVacuumMapsRoomsCard);

// Shows in the browser console that the card was loaded
console.info("tuya-vacuum-maps-rooms-card loaded");

window.customCards = window.customCards || [];
window.customCards.push({
  type: "tuya-vacuum-maps-rooms-card",
  name: "Tuya Vacuum Maps Rooms",
  description: "Pick rooms, set the cleaning passes and start cleaning.",
});
