export function createBookingProgressWidget({
  root,
  titleElement,
  statusElement,
  stepsElement,
  resetButton,
  onEditField,
  labelForField,
  summaryHistory,
}) {
  function progressTitleForPercent(percent) {
    if (!percent) {
      return "Закажување во тек - Податоци за пациент";
    }
    return `Закажување во тек - Податоци за пациент - ${percent}%`;
  }

  function displayValueForField(item) {
    if (!item || !item.value) {
      return labelForField(item?.field);
    }
    return item.value;
  }

  function reset() {
    root.classList.remove("visible");
    stepsElement.innerHTML = "";
    titleElement.textContent = progressTitleForPercent(0);
    statusElement.textContent = "0 / 3";
    resetButton.hidden = true;
  }

  function update(progress) {
    if (!progress || !progress.visible) {
      reset();
      return;
    }

    root.classList.add("visible");
    titleElement.textContent = progressTitleForPercent(progress.progress_percent || 0);
    statusElement.textContent = `${progress.collection_status} / ${progress.collection_total}`;
    resetButton.hidden = false;
    stepsElement.innerHTML = "";

    if (progress.reservation_status === "complete" && progress.summary) {
      summaryHistory.queueIfNew(progress.summary);
    }

    for (const item of progress.fields || []) {
      const stepEl = document.createElement("div");
      stepEl.className = "booking-step";

      if (item.done) {
        stepEl.classList.add("done", "editable");
        stepEl.addEventListener("click", () => onEditField(item.field));
      } else if (progress.next_field === item.field && progress.reservation_status !== "complete") {
        stepEl.classList.add("active");
      }

      stepEl.textContent = displayValueForField(item);
      stepsElement.appendChild(stepEl);
    }
  }

  return {
    reset,
    update,
  };
}
