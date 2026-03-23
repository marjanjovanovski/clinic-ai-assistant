import { createChatTranscript } from "/frontend/chat/chat-shell.js";
import { createBookingProgressWidget } from "/frontend/widgets/booking-progress/booking-progress.js";
import { createBookingSummaryElement } from "/frontend/widgets/booking-summary/booking-summary.js";
import { createSlotListWidget } from "/frontend/widgets/slot-list/slot-list.js";

export function createConversationWidgetRegistry() {
  const handlers = new Map();

  function register(type, mountWidget) {
    if (!type || typeof mountWidget !== "function") {
      throw new Error("Widget type and mount function are required.");
    }
    handlers.set(type, mountWidget);
    return api;
  }

  function has(type) {
    return handlers.has(type);
  }

  function mount(type, payload = {}, context = {}) {
    const mountWidget = handlers.get(type);
    if (!mountWidget) {
      throw new Error(`Unknown conversation widget: ${type}`);
    }
    return normalizeMountResult(mountWidget(payload, context));
  }

  function supportedTypes() {
    return Array.from(handlers.keys());
  }

  const api = {
    has,
    mount,
    register,
    supportedTypes,
  };

  return api;
}

export function registerDefaultConversationWidgets(
  registry,
  {
    bookingSummaryTemplate = null,
    labelForField = null,
  } = {},
) {
  registry.register("booking-progress", (payload) => ({
    widget: createBookingProgressWidget(payload),
    element: payload.root,
    wrapInMessage: false,
  }));

  registry.register("booking-summary", (payload, context) => ({
    element: createBookingSummaryElement({
      template: context.template || bookingSummaryTemplate,
      summary: payload.summary || payload,
      labelForField: context.labelForField || labelForField,
    }),
    wrapInMessage: false,
  }));

  registry.register("slot-list", (payload) => {
    const widget = createSlotListWidget(payload);
    return {
      widget,
      element: widget.root,
      wrapInMessage: true,
    };
  });

  return registry;
}

export function createConversationWidgetDispatcher({
  container,
  registry,
  afterAppend = null,
}) {
  const transcript = createChatTranscript(container, {
    afterAppend({ sender, element }) {
      if (typeof afterAppend === "function") {
        afterAppend({
          container,
          element,
          kind: "message",
          sender,
          type: null,
          widget: null,
        });
      }
    },
  });

  function appendNode(node, meta = {}) {
    container.appendChild(node);
    if (typeof afterAppend === "function") {
      afterAppend({
        container,
        element: node,
        kind: meta.kind || "message",
        sender: meta.sender || null,
        type: meta.type || null,
        widget: meta.widget || null,
      });
    }
    scrollToBottom();
    return node;
  }

  function scrollToBottom() {
    container.scrollTop = container.scrollHeight;
  }

  function clear() {
    container.innerHTML = "";
  }

  function addTextMessage(text, sender) {
    return transcript.addMessage(text, sender);
  }

  function addWidget(type, payload = {}, options = {}) {
    const { sender = "bot", ...context } = options;
    const rendered = registry.mount(type, payload, context);
    const element = rendered.wrapInMessage
      ? wrapWidgetElement(rendered.element, sender, type)
      : rendered.element;

    return {
      element: appendNode(element, {
        kind: "widget",
        sender,
        type,
        widget: rendered.widget || null,
      }),
      widget: rendered.widget || null,
    };
  }

  return {
    addTextMessage,
    addWidget,
    clear: transcript.clear,
    scrollToBottom: transcript.scrollToBottom,
  };
}

function wrapWidgetElement(element, sender, type = null) {
  const messageEl = document.createElement("div");
  messageEl.classList.add("message", sender);
  messageEl.classList.add("message-widget");
  if (type) {
    messageEl.classList.add(`message-widget-${type}`);
  }
  messageEl.appendChild(element);
  return messageEl;
}

function normalizeMountResult(result) {
  if (result instanceof HTMLElement) {
    return {
      element: result,
      widget: null,
      wrapInMessage: true,
    };
  }

  if (!result || !(result.element instanceof HTMLElement)) {
    throw new Error("Widget handlers must return an element or a normalized widget result.");
  }

  return {
    element: result.element,
    widget: result.widget || null,
    wrapInMessage: result.wrapInMessage !== false,
  };
}
