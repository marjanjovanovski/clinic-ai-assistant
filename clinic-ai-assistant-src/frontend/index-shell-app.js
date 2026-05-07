import { resolveTenantFromPath } from "/frontend/chat/chat-shell.js";
import { bindTextInputSubmission, setInputBusyState } from "/frontend/chat/chat-input.js";
import { createBookingSummaryHistory } from "/frontend/widgets/booking-summary/booking-summary.js";
import {
  addSlotListConversationWidget,
  createConversationWidgetDispatcher,
  createConversationWidgetRegistry,
  registerDefaultConversationWidgets,
} from "/frontend/widgets/widget-registry.js";

const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const statusText = document.getElementById("statusText");
const chatHeader = document.getElementById("chatHeader");
const flowEntryButtons = Array.from(document.querySelectorAll("[data-flow-entry]"));
const bookingProgress = document.getElementById("bookingProgress");
const bookingProgressTitle = document.getElementById("bookingProgressTitle");
const bookingProgressStatus = document.getElementById("bookingProgressStatus");
const bookingProgressSteps = document.getElementById("bookingProgressSteps");
const bookingResetButton = document.getElementById("bookingResetButton");
const bookingSummary = document.getElementById("bookingSummary");
const bookingSummaryTemplate = bookingSummary.cloneNode(true);
bookingSummary.remove();

const tenant = resolveTenantFromPath(window.location.pathname, "generic");
const sessionStorageKey = `clinic-ai-session:${tenant}`;
let sessionId = window.localStorage.getItem(sessionStorageKey) || null;
let isSending = false;
let tenantConfig = null;

const API_URL = `/chat?tenant=${encodeURIComponent(tenant)}`;
const FLOW_ACTION_URL = `/chat/action?tenant=${encodeURIComponent(tenant)}`;
const CONFIG_URL = `/config/${encodeURIComponent(tenant)}`;
const SELECT_SLOT_URL = `/scheduling/select-slot?tenant=${encodeURIComponent(tenant)}`;
const FLOW_ENTRY_COPY = {
  mk: {
    catalog: {
      label: "Каталог",
    },
    availability: {
      label: "Слободни термини",
    },
    booking: {
      label: "Закажи",
    },
  },
  en: {
    catalog: {
      label: "Catalog",
    },
    availability: {
      label: "Available slots",
    },
    booking: {
      label: "Book now",
    },
  },
};

const widgetRegistry = registerDefaultConversationWidgets(
  createConversationWidgetRegistry(),
  {
    bookingSummaryTemplate,
    labelForField,
  }
);

const conversationDispatcher = createConversationWidgetDispatcher({
  container: chatMessages,
  registry: widgetRegistry,
  afterAppend({ kind, sender }) {
    if (kind === "message" && sender === "bot") {
      bookingSummaryHistory.flushPending();
    }
  }
});

const bookingSummaryHistory = createBookingSummaryHistory({
  template: bookingSummaryTemplate,
  labelForField,
  appendSummary(summary) {
    return conversationDispatcher.addWidget(
      "booking-summary",
      { summary },
      {
        template: bookingSummaryTemplate,
        labelForField,
      }
    ).element;
  },
});

const bookingProgressWidget = widgetRegistry.mount("booking-progress", {
  root: bookingProgress,
  titleElement: bookingProgressTitle,
  statusElement: bookingProgressStatus,
  stepsElement: bookingProgressSteps,
  resetButton: bookingResetButton,
  onEditField: beginBookingFieldEdit,
  labelForField,
  summaryHistory: bookingSummaryHistory,
}).widget;

function addMessage(text, sender) {
  return conversationDispatcher.addTextMessage(text, sender);
}

function isSlotListWidgetPayload(widgetPayload) {
  return Boolean(
    widgetPayload &&
    widgetPayload.type === "slot-list" &&
    Array.isArray(widgetPayload.slots) &&
    widgetPayload.slots.length
  );
}

function getPrimaryReplyText(replyText, widgetPayload) {
  if (typeof replyText !== "string" || !replyText.trim()) {
    return "";
  }

  if (!isSlotListWidgetPayload(widgetPayload)) {
    return replyText.trim();
  }

  const [primaryReply] = replyText.split(/\n\s*\n/, 1);
  return String(primaryReply || "").trim();
}

function syncSessionId(nextSessionId) {
  if (!nextSessionId) {
    return;
  }

  sessionId = nextSessionId;
  window.localStorage.setItem(sessionStorageKey, sessionId);
}

function updateStatusFromSessionStatus(nextSessionStatus, fallbackText = "Ready") {
  statusText.textContent = nextSessionStatus === "completed"
    ? "Request completed."
    : nextSessionStatus === "collecting_contact"
      ? "Collecting contact details."
      : fallbackText;
}

function flowEntryLanguage(config = null) {
  const language = String(config?.business?.language || "").trim().toLowerCase();
  return language.startsWith("mk") ? "mk" : "en";
}

function flowEntryConfig(key, config = null) {
  const language = flowEntryLanguage(config);
  const localizedConfig = FLOW_ENTRY_COPY[language] || FLOW_ENTRY_COPY.en;
  return localizedConfig[key] || null;
}

function syncFlowEntryButtonCopy(config = null) {
  for (const button of flowEntryButtons) {
    const entryKey = button.dataset.flowEntry;
    const entryConfig = flowEntryConfig(entryKey, config);
    if (!entryConfig) {
      continue;
    }
    button.textContent = entryConfig.label;
    button.setAttribute("aria-label", entryConfig.label);
  }
}

function setActiveFlowEntryButton(activeKey = "") {
  for (const button of flowEntryButtons) {
    button.classList.toggle("is-active", Boolean(activeKey) && button.dataset.flowEntry === activeKey);
  }
}

function applyBackendConversationUpdate(data, options = {}) {
  const {
    fallbackReply = "No response from server.",
    fallbackStatus = "Ready",
    includeWidget = false,
    includeSelectedSlot = false,
  } = options;

  syncSessionId(data.session_id);
  updateBookingProgress(data.booking_progress);

  const primaryReplyText = getPrimaryReplyText(data.reply, includeWidget ? data.widget_payload : null);
  addMessage(primaryReplyText || fallbackReply, "bot");

  if (includeWidget) {
    addResponseWidget(data.widget_payload, { hideTitle: Boolean(primaryReplyText) });
  }
  if (includeSelectedSlot) {
    addSelectedSlotWidget(data.selected_slot);
  }

  updateStatusFromSessionStatus(data.session_status, fallbackStatus);
}

async function handleSlotSelection(slot, widgetPayload, slotListWidget) {
  if (!sessionId) {
    addMessage("No active chat session is available for slot selection.", "bot");
    statusText.textContent = "Session not available.";
    slotListWidget.enableAll();
    return;
  }

  slotListWidget.disableAll();
  addMessage(`Selecting this slot: ${slot.display_label}`, "user");
  statusText.textContent = "Sending selected slot...";

  try {
    const response = await fetch(SELECT_SLOT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        session_id: sessionId,
        service_id: widgetPayload.service_id,
        slot_id: slot.slot_id
      })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP error: ${response.status}`);
    }

    applyBackendConversationUpdate(data, {
      fallbackReply: "The selected slot has been applied.",
      fallbackStatus: "Slot selected.",
      includeWidget: true,
      includeSelectedSlot: true,
    });
  } catch (error) {
    addMessage(`Slot selection failed. ${error.message}`, "bot");
    statusText.textContent = `Error: ${error.message}`;
    slotListWidget.enableAll();
  }
}

function addResponseWidget(widgetPayload, options = {}) {
  if (!widgetPayload || widgetPayload.type !== "slot-list") {
    return null;
  }

  const slots = Array.isArray(widgetPayload.slots) ? widgetPayload.slots : [];
  if (!slots.length) {
    return null;
  }

  const { hideTitle = false, readOnly = false } = options;

  return addSlotListConversationWidget(conversationDispatcher, {
    title: hideTitle ? null : (widgetPayload.title || "Choose a slot:"),
    slots,
    onSelect: (slotValue, currentSlotListWidget) => handleSlotSelection(slotValue, widgetPayload, currentSlotListWidget),
    readOnly,
  }, { sender: "bot" });
}

function buildSelectedSlotWidgetPayload(selectedSlot) {
  if (!selectedSlot || typeof selectedSlot !== "object") {
    return null;
  }

  return {
    type: "slot-list",
    title: null,
    slots: [selectedSlot],
  };
}

function addSelectedSlotWidget(selectedSlot) {
  const widgetPayload = buildSelectedSlotWidgetPayload(selectedSlot);
  if (!widgetPayload) {
    return null;
  }

  return addResponseWidget(widgetPayload, {
    hideTitle: true,
    readOnly: true,
  });
}

async function performSend(userMessage, options = {}) {
  const { showUserMessage = true, activeFlowEntry = "" } = options;

  if (isSending) {
    return;
  }

  const trimmedMessage = String(userMessage || "").trim();
  if (!trimmedMessage) {
    return;
  }

  isSending = true;
  setActiveFlowEntryButton(activeFlowEntry);
  if (showUserMessage) {
    addMessage(trimmedMessage, "user");
  }
  messageInput.value = "";
  setInputBusyState({ input: messageInput, button: sendButton, isBusy: true });
  statusText.textContent = "Sending...";

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        message: trimmedMessage,
        session_id: sessionId
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }

    const data = await response.json();
    applyBackendConversationUpdate(data, {
      fallbackReply: "No response from server.",
      fallbackStatus: "Ready",
      includeWidget: true,
    });
  } catch (error) {
    addMessage("A connection error occurred while reaching the system.", "bot");
    statusText.textContent = `Error: ${error.message}`;
  } finally {
    isSending = false;
    setActiveFlowEntryButton("");
    setInputBusyState({ input: messageInput, button: sendButton, isBusy: false });
    messageInput.focus();
  }
}

function handleFlowEntryClick(entryKey) {
  if (isSending) {
    return;
  }

  const entryConfig = flowEntryConfig(entryKey, tenantConfig);
  if (!entryConfig) {
    return;
  }

  performFlowEntryAction(entryKey);
}

async function performFlowEntryAction(action) {
  if (isSending) {
    return;
  }

  isSending = true;
  setActiveFlowEntryButton(action);
  setInputBusyState({ input: messageInput, button: sendButton, isBusy: true });
  statusText.textContent = "Opening flow...";

  try {
    const response = await fetch(FLOW_ACTION_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        action,
        session_id: sessionId,
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }

    const data = await response.json();
    applyBackendConversationUpdate(data, {
      fallbackReply: "No response from server.",
      fallbackStatus: "Ready",
      includeWidget: true,
    });
  } catch (error) {
    addMessage("A connection error occurred while opening the selected flow.", "bot");
    statusText.textContent = `Error: ${error.message}`;
  } finally {
    isSending = false;
    setActiveFlowEntryButton("");
    setInputBusyState({ input: messageInput, button: sendButton, isBusy: false });
    messageInput.focus();
  }
}

function beginBookingFieldEdit(fieldName) {
  if (!sessionId || !fieldName) {
    return;
  }
  performSend(`__booking_edit__:${fieldName}`, { showUserMessage: false });
}

async function resetConversation() {
  if (isSending) {
    return;
  }

  sessionId = null;
  window.localStorage.removeItem(sessionStorageKey);
  bookingSummaryHistory.reset();
  bookingProgressWidget.reset();
  statusText.textContent = "Ready";
  messageInput.value = "";
  await loadTenantConfig();
  messageInput.focus();
}

function labelForField(fieldName) {
  if (fieldName === "name") return "Name";
  if (fieldName === "phone") return "Phone";
  if (fieldName === "email") return "Email";
  return fieldName;
}

function updateBookingProgress(progress) {
  bookingProgressWidget.update(progress);
}

async function loadTenantConfig() {
  try {
    const response = await fetch(CONFIG_URL);

    if (!response.ok) {
      throw new Error(`HTTP error: ${response.status}`);
    }

    const config = await response.json();
    tenantConfig = config;
    const businessName = config.business?.name || config.assistant?.name || "Assistant";
    const greeting = config.conversation?.greeting || "Hello! How can I help you today?";
    syncFlowEntryButtonCopy(config);

    chatHeader.textContent = businessName;
    document.title = businessName;

    conversationDispatcher.clear();
    bookingSummaryHistory.reset();
    bookingProgressWidget.reset();
    addMessage(greeting, "bot");
  } catch (error) {
    tenantConfig = null;
    syncFlowEntryButtonCopy();
    chatHeader.textContent = "Assistant";
    document.title = "Assistant";
    conversationDispatcher.clear();
    bookingSummaryHistory.reset();
    bookingProgressWidget.reset();
    addMessage("Hello! How can I help you today?", "bot");
    console.error("Failed to load tenant config:", error);
  }
}

async function sendMessage() {
  const userMessage = messageInput.value.trim();
  await performSend(userMessage, { showUserMessage: true });
}

bindTextInputSubmission({
  input: messageInput,
  button: sendButton,
  onSubmit: sendMessage,
});
bookingResetButton.addEventListener("click", resetConversation);
for (const button of flowEntryButtons) {
  button.addEventListener("click", () => handleFlowEntryClick(button.dataset.flowEntry));
}

loadTenantConfig();
