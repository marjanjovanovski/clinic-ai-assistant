export function createBookingSummaryHistory({ template, messageContainer, labelForField }) {
  let pendingSummary = null;
  let lastAppendedSummaryKey = null;

  function bookingSummaryKey(summary) {
    if (!summary) {
      return null;
    }
    return JSON.stringify(summary);
  }

  function populateBookingSummaryElement(element, summary) {
    element.classList.add("visible");
    element.querySelector("#bookingSummaryTitle").textContent = summary.title || "Резиме на барањето";
    element.querySelector("#bookingSummarySubtitle").textContent = summary.subtitle || "";
    element.querySelector("#bookingSummaryBadge").textContent = summary.appointment_status || "Привремен термин";
    element.querySelector("#bookingSummaryService").textContent = summary.service_name || "Стоматолошка консултација";
    element.querySelector("#bookingSummaryAppointment").textContent = summary.appointment_display || "21 MAR 2026 во 14:00";

    const fieldsContainer = element.querySelector("#bookingSummaryFields");
    fieldsContainer.innerHTML = "";

    for (const item of summary.fields || []) {
      const fieldEl = document.createElement("div");
      fieldEl.className = "booking-summary-field";

      const labelEl = document.createElement("div");
      labelEl.className = "booking-summary-label";
      labelEl.textContent = labelForField(item.field) || item.label || "";

      const valueEl = document.createElement("div");
      valueEl.className = "booking-summary-value";
      valueEl.textContent = item.value || "";

      fieldEl.appendChild(labelEl);
      fieldEl.appendChild(valueEl);
      fieldsContainer.appendChild(fieldEl);
    }

    const noteContainer = element.querySelector("#bookingSummaryNote");
    const noteLabel = element.querySelector("#bookingSummaryNoteLabel");
    const noteValue = element.querySelector("#bookingSummaryNoteValue");
    const summaryNote = String(summary.patient_note || summary.note || summary.notes || "").trim();

    if (summaryNote) {
      noteContainer.hidden = false;
      noteContainer.classList.add("visible");
      noteLabel.textContent = summary.note_label || "Забелешка од пациентот";
      noteValue.textContent = summaryNote;
    } else {
      noteContainer.hidden = true;
      noteContainer.classList.remove("visible");
      noteLabel.textContent = "Забелешка од пациентот";
      noteValue.textContent = "";
    }

    element.removeAttribute("id");
    element.querySelectorAll("[id]").forEach((node) => node.removeAttribute("id"));
    element.dataset.summaryKey = bookingSummaryKey(summary) || "";
    return element;
  }

  function append(summary) {
    if (!summary) {
      return null;
    }
    const entry = populateBookingSummaryElement(template.cloneNode(true), summary);
    messageContainer.appendChild(entry);
    messageContainer.scrollTop = messageContainer.scrollHeight;
    lastAppendedSummaryKey = bookingSummaryKey(summary);
    return entry;
  }

  function queueIfNew(summary) {
    const currentSummaryKey = bookingSummaryKey(summary);
    if (!summary || !currentSummaryKey || currentSummaryKey === lastAppendedSummaryKey) {
      return false;
    }
    pendingSummary = summary;
    return true;
  }

  function flushPending() {
    if (!pendingSummary) {
      return null;
    }
    const flushedSummary = pendingSummary;
    pendingSummary = null;
    return append(flushedSummary);
  }

  function reset() {
    pendingSummary = null;
    lastAppendedSummaryKey = null;
  }

  function getLastAppendedKey() {
    return lastAppendedSummaryKey;
  }

  return {
    append,
    bookingSummaryKey,
    flushPending,
    getLastAppendedKey,
    queueIfNew,
    reset,
  };
}
