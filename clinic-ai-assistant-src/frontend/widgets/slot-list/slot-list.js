function defaultSlotLabel(slot) {
  return slot?.display_label || slot?.start_at || "";
}

function dayKeyForSlot(slot) {
  const startAt = String(slot?.start_at || "").trim();
  return startAt.slice(0, 10) || "unknown-day";
}

const MACEDONIAN_WEEKDAYS = ["Недела", "Понеделник", "Вторник", "Среда", "Четврток", "Петок", "Сабота"];
const MACEDONIAN_MONTHS = ["Јан", "Фев", "Мар", "Апр", "Мај", "Јун", "Јул", "Авг", "Сеп", "Окт", "Ное", "Дек"];

function formatDayLabel(slot) {
  const startAt = String(slot?.start_at || "").trim();
  if (!startAt) {
    return {
      primary: "Достапен ден",
      secondary: "",
    };
  }

  const parsed = new Date(startAt);
  if (Number.isNaN(parsed.getTime())) {
    return {
      primary: startAt,
      secondary: "",
    };
  }

  const weekday = MACEDONIAN_WEEKDAYS[parsed.getDay()] || "";
  const day = String(parsed.getDate()).padStart(2, "0");
  const month = MACEDONIAN_MONTHS[parsed.getMonth()] || "";
  const year = parsed.getFullYear();
  return {
    primary: `${day} ${month} ${year}`,
    secondary: weekday,
  };
}

function formatTimeLabel(slot) {
  const startAt = String(slot?.start_at || "").trim();
  if (!startAt) {
    return defaultSlotLabel(slot);
  }

  const parsed = new Date(startAt);
  if (Number.isNaN(parsed.getTime())) {
    return defaultSlotLabel(slot);
  }

  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsed);
}

function groupSlotsByDay(slots) {
  const grouped = new Map();

  for (const slot of slots) {
    const dayKey = dayKeyForSlot(slot);
    if (!grouped.has(dayKey)) {
      grouped.set(dayKey, []);
    }
    grouped.get(dayKey).push(slot);
  }

  return Array.from(grouped.entries()).map(([dayKey, daySlots]) => ({
    dayKey,
    dayLabel: formatDayLabel(daySlots[0]),
    slots: daySlots,
  }));
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

  const daysEl = document.createElement("div");
  daysEl.className = "slot-list-days";
  root.appendChild(daysEl);

  const dayGroups = groupSlotsByDay(slots);
  root.classList.toggle("slot-list-widget--single-day", dayGroups.length === 1);
  root.classList.toggle("slot-list-widget--two-days", dayGroups.length === 2);

  const api = {
    root,
    daysElement: daysEl,
    disableAll,
    enableAll,
    getButtons,
  };

  for (const dayGroup of dayGroups) {
    const dayCardEl = document.createElement("section");
    dayCardEl.className = "slot-day-card";

    const dayHeaderEl = document.createElement("div");
    dayHeaderEl.className = "slot-day-header";

    const dayTopRowEl = document.createElement("div");
    dayTopRowEl.className = "slot-day-top-row";

    const dayTitleEl = document.createElement("div");
    dayTitleEl.className = "slot-day-title";
    dayTitleEl.textContent = dayGroup.dayLabel.primary;
    dayTopRowEl.appendChild(dayTitleEl);

    const dayWeekdayEl = document.createElement("div");
    dayWeekdayEl.className = "slot-day-weekday";
    dayWeekdayEl.textContent = dayGroup.dayLabel.secondary || "";
    dayTopRowEl.appendChild(dayWeekdayEl);

    dayHeaderEl.appendChild(dayTopRowEl);

    dayCardEl.appendChild(dayHeaderEl);

    const actionsEl = document.createElement("div");
    actionsEl.className = "slot-list-actions";
    dayCardEl.appendChild(actionsEl);

    for (const slot of dayGroup.slots) {
      const buttonEl = document.createElement("button");
      buttonEl.type = "button";
      buttonEl.className = "slot-list-button";
      buttonEl.textContent = formatTimeLabel(slot);
      buttonEl.title = getSlotLabel(slot);
      buttonEl.addEventListener("click", () => {
        markSelected(buttonEl);
        if (typeof onSelect === "function") {
          onSelect(slot, api);
        }
      });
      actionsEl.appendChild(buttonEl);
    }

    daysEl.appendChild(dayCardEl);
  }

  return api;

  function getButtons() {
    return Array.from(daysEl.querySelectorAll("button"));
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

  function markSelected(selectedButton) {
    for (const button of getButtons()) {
      button.classList.toggle("selected", button === selectedButton);
    }
  }
}
