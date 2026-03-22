export function setInputBusyState({ input, button, isBusy }) {
  if (button) {
    button.disabled = isBusy;
  }
  if (input) {
    input.disabled = isBusy;
  }
}

export function bindTextInputSubmission({ input, button, onSubmit }) {
  if (button) {
    button.addEventListener("click", onSubmit);
  }

  if (input) {
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        onSubmit();
      }
    });
  }
}
