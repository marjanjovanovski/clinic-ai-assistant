function hasStructuredLines(lines) {
  return lines.some((line) => {
    const trimmed = line.trim();
    return trimmed.startsWith("• ") || trimmed.startsWith("– ");
  });
}

export function renderMessageContent(text) {
  const value = String(text || "");
  const lines = value.split(/\r?\n/);

  if (!hasStructuredLines(lines)) {
    const textEl = document.createElement("div");
    textEl.className = "message-text";
    textEl.textContent = value;
    return textEl;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "message-structured";

  let currentGroup = null;
  let currentList = null;

  for (const rawLine of lines) {
    const trimmed = rawLine.trim();

    if (!trimmed) {
      currentList = null;
      continue;
    }

    if (trimmed.startsWith("• ")) {
      currentGroup = document.createElement("div");
      currentGroup.className = "structured-group";

      const titleEl = document.createElement("div");
      titleEl.className = "structured-title";
      titleEl.textContent = trimmed.slice(2).trim();

      currentGroup.appendChild(titleEl);
      wrapper.appendChild(currentGroup);
      currentList = null;
      continue;
    }

    if (trimmed.startsWith("– ")) {
      if (!currentGroup) {
        currentGroup = document.createElement("div");
        currentGroup.className = "structured-group";
        wrapper.appendChild(currentGroup);
      }

      if (!currentList) {
        currentList = document.createElement("ul");
        currentList.className = "structured-list";
        currentGroup.appendChild(currentList);
      }

      const itemEl = document.createElement("li");
      itemEl.textContent = trimmed.slice(2).trim();
      currentList.appendChild(itemEl);
      continue;
    }

    const textEl = document.createElement("div");
    textEl.className = "message-text";
    textEl.textContent = trimmed;
    wrapper.appendChild(textEl);
    currentGroup = null;
    currentList = null;
  }

  return wrapper;
}

export function createMessageElement(text, sender) {
  const messageEl = document.createElement("div");
  messageEl.classList.add("message", sender);
  messageEl.appendChild(renderMessageContent(text));
  return messageEl;
}

export function createChatTranscript(container, options = {}) {
  const { afterAppend = null } = options;

  function scrollToBottom() {
    container.scrollTop = container.scrollHeight;
  }

  function clear() {
    container.innerHTML = "";
  }

  function addMessage(text, sender) {
    const messageEl = createMessageElement(text, sender);
    container.appendChild(messageEl);
    if (typeof afterAppend === "function") {
      afterAppend({ sender, text, element: messageEl, container });
    }
    scrollToBottom();
    return messageEl;
  }

  return {
    addMessage,
    clear,
    scrollToBottom,
  };
}

export function resolveTenantFromPath(pathname, fallbackTenant = "generic") {
  const pathParts = String(pathname || "").split("/").filter(Boolean);
  return pathParts[0] === "agent" && pathParts[1] ? pathParts[1] : fallbackTenant;
}
