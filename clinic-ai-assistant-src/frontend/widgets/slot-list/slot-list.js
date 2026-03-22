function defaultSlotLabel(slot) {
  return slot?.display_label || slot?.start_at || "";
}

export function createSlotListWidget({
  title = "Select a time slot:",
  slots = [],
  onSelect,
  getSlotLabel = defaultSlotLabel,
}) {
  const root = document.createElement("div");
  root.className = "slot-list-widget";

  const titleEl = document.createElement("div");
  titleEl.className = "slot-list-title";
  titleEl.textContent = title;
  root.appendChild(titleEl);

  const actionsEl = document.createElement("div");
  actionsEl.className = "slot-list-actions";
  root.appendChild(actionsEl);

  const api = {
    root,
    actionsElement: actionsEl,
    disableAll,
    enableAll,
    getButtons,
  };

  for (const slot of slots) {
    const buttonEl = document.createElement("button");
    buttonEl.type = "button";
    buttonEl.className = "slot-list-button";
    buttonEl.textContent = getSlotLabel(slot);
    buttonEl.addEventListener("click", () => {
      if (typeof onSelect === "function") {
        onSelect(slot, api);
      }
    });
    actionsEl.appendChild(buttonEl);
  }

  return api;

  function getButtons() {
    return Array.from(actionsEl.querySelectorAll("button"));
  }

  function disableAll() {
    for (const button of getButtons()) {
      button.disabled = true;
    }
  }

  function enableAll() {
    for (const button of getButtons()) {
      button.disabled = false;
    }
  }
}
