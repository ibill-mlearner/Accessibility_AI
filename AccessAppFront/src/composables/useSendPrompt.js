import { ref } from 'vue'
import { buildFirstChatTitle, createId, readAssistantText, withSingleRetry } from '../utils/helpers'
import { useFeatureStore } from '../stores/featureStore'
import { filterSiteWideFeatures } from '../utils/accessibilityFeatureScope'

export function useSendPrompt({
  auth,
  router,
  chatStore,
  classStore,
  timelineMessages,
  scrollToLatestTurn,
  interactionError
}) {
  // Tracks the current composer text across request lifecycle transitions.
  const prompt = ref('')
  // Prevents concurrent send flows and controls UI loading states.
  const interactionLoading = ref(false)
  // Provides selected accessibility feature context for outbound AI payloads.
  const featureStore = useFeatureStore()
  // Keeps model-contact failures user-safe and consistent across error sources.
  const SAFE_MODEL_CONTACT_ERROR_MESSAGE = 'There was a problem with the model contact the administrator.'

  // Emits detailed errors only in DEV so production logs remain controlled.
  function logDevError(label, payload) {
    if (!import.meta.env.DEV) return
    console.error(label, payload)
  }

  // --- Parsing + normalization helpers -------------------------------------

  // Normalizes backend/provider error envelopes into one frontend error object.
  function parseAiInteractionError(error) {
    const status = error?.response?.status
    const responseData = error?.response?.data
    const responseError = responseData?.error

    const backendMessage = typeof responseData === 'string'
      ? responseData
      : responseError?.message || responseData?.message || responseData?.error || ''

    return {
      status,
      responseData,
      errorCode: responseError?.code || responseData?.code || '',
      errorSource: responseError?.details?.source || responseData?.details?.source || '',
      backendMessage
    }
  }

  // Maps normalized error envelopes to user-facing messages with provider-safe fallbacks.
  function resolveAiInteractionErrorMessage(parsedError) {
    const { status, backendMessage, errorCode, errorSource } = parsedError
    const messageLower = String(backendMessage || '').toLowerCase()

    if (status === 400) {
      const rejectedPromptMessage = 'Prompt was rejected. Please edit and retry.'
      return `${rejectedPromptMessage} ${backendMessage}`.trim()
    }

    const isModelContactFailure = new Set([
      'runtime_unavailable',
      'provider_unavailable',
      'provider_auth_failed',
      'provider_model_not_found',
      'provider_gated_model',
      'upstream_error'
    ]).has(errorCode)

    if (isModelContactFailure) {
      return SAFE_MODEL_CONTACT_ERROR_MESSAGE
    }

    // Preserves compatibility for older provider-auth error signatures.
    const backwardCompatProviderAuthSignal = errorCode === 'upstream_error'
      && errorSource === 'provider_runtime'
      && (status === 401 || messageLower.includes('repository not found') || messageLower.includes('invalid username or password'))

    if (backwardCompatProviderAuthSignal) {
      return SAFE_MODEL_CONTACT_ERROR_MESSAGE
    }

    return backendMessage || 'AI is temporarily unavailable. Please retry.'
  }

  // Extracts usable assistant text and sets a retryable message when payloads are malformed.
  function resolveAssistantText(aiResponse, draftPrompt) {
    const assistantText = readAssistantText(aiResponse)
    if (assistantText) return assistantText

    interactionError.value = 'Assistant response was not in a usable format. Please retry.'
    prompt.value = draftPrompt
    return ''
  }

  // --- Sending + persistence helpers ---------------------------------------

  // Redirects guests to login while preserving intended prompt context.
  async function redirectGuest(cleanPrompt) {
    if (auth.role !== 'guest') return false
    interactionError.value = 'Please log in to send a prompt.'
    await router.push({ path: '/login', query: { next: '/', prompt: cleanPrompt } })
    return true
  }

  // Resolves class scope required for chat creation/AI context payloads.
  function resolveClassIdForChat() {
    const classIdForChat = classStore.selectedClassId || classStore.classes[0]?.id
    if (!classIdForChat) {
      interactionError.value = 'No class is available for this account yet.'
      return null
    }

    return classIdForChat
  }

  // Resolves the currently selected provider/model tuple from chat store state.
  function resolveSelectedModelValue() {
    return String(chatStore.selectedModel || '').trim()
  }

  // Ensures a chat exists before AI interaction calls begin.
  async function ensureChat({
    cleanPrompt,
    classIdForChat,
    selectedModelValue
  }) {
    return withSingleRetry(() =>
      chatStore.ensureActiveChat({
        title: buildFirstChatTitle(cleanPrompt, chatStore.chats.length + 1),
        started_at: new Date().toISOString(),
        model: selectedModelValue,
        class_id: classIdForChat,
        user_id: auth.currentUser?.id
      })
    )
  }

  // Persists the user's prompt as a chat message and appends it to the local timeline.
  async function saveUserMessage({
    chatId,
    cleanPrompt
  }) {
    const userMessage = await withSingleRetry(() =>
      chatStore.createMessage({
        chat_id: chatId,
        message_text: cleanPrompt,
        help_intent: 'summarization'
      })
    )

    timelineMessages.value.push({
      id: userMessage.id,
      role: 'user',
      text: userMessage.message_text
    })

    await scrollToLatestTurn()
    return userMessage
  }

  // Builds the backend interaction payload from prompt + class + selected accessibility context.
  function buildAiRequestPayload({
    cleanPrompt,
    chatId,
    classIdForChat
  }) {
    const selectedSet = new Set(featureStore.selectedLinkIds)
    const selectedAccessibilityLinkIds = filterSiteWideFeatures(featureStore.features)
      .map((feature) => Number(feature?.id))
      .filter((id) => Number.isInteger(id) && selectedSet.has(id))

    return {
      prompt: cleanPrompt,
      chat_id: chatId,
      selected_accessibility_link_ids: selectedAccessibilityLinkIds,
      selected_accommodations_id_system_prompts_ids: selectedAccessibilityLinkIds,
      use_user_feature_preferences: true,
      context: {
        chat_id: chatId,
        class_id: classIdForChat,
        messages: [{ role: 'user', content: cleanPrompt }],
        selected_accessibility_link_ids: selectedAccessibilityLinkIds
      }
    }
  }

  // Executes the interaction request and converts transport failures into user-facing error state.
  async function requestAssistantResponse({
    cleanPrompt,
    chatId,
    classIdForChat,
    draftPrompt
  }) {
    const payload = buildAiRequestPayload({
      cleanPrompt,
      chatId,
      classIdForChat
    })

    try {
      return await chatStore.requestAiInteraction(payload)
    } catch (error) {
      const parsedError = parseAiInteractionError(error)

      logDevError('[useSendPrompt] requestAiInteraction failed', {
        message: error?.message,
        status: parsedError.status,
        responseData: parsedError.responseData,
        errorCode: parsedError.errorCode,
        errorSource: parsedError.errorSource,
        stack: error?.stack
      })

      interactionError.value = resolveAiInteractionErrorMessage(parsedError)
      prompt.value = draftPrompt
      return null
    }
  }

  // Persists assistant text and reconciles the optimistic pending message when needed.
  async function saveAssistantMessage({
    chatId,
    assistantText,
    pendingAssistantId = null
  }) {
    const savedAssistantMessage = await withSingleRetry(() =>
      chatStore.createMessage({
        chat_id: chatId,
        message_text: assistantText,
        help_intent: 'summarization'
      })
    )

    if (!pendingAssistantId) return
    if (!isChatStillSelected(chatId)) return

    timelineMessages.value = timelineMessages.value.map((message) =>
      message.id === pendingAssistantId
        ? { id: savedAssistantMessage.id, role: 'assistant', text: savedAssistantMessage.message_text }
        : message
    )
    await scrollToLatestTurn()
  }

  // Converts unexpected outer flow failures into retryable UI errors.
  function reportOuterFailure(error, draftPrompt) {
    logDevError('[useSendPrompt] sendPrompt failed', {
      message: error?.message,
      status: error?.response?.status,
      responseData: error?.response?.data,
      stack: error?.stack
    })

    const storeMessage = String(error?.message || '')
    const normalizedStoreMessage = storeMessage.toLowerCase()
    interactionError.value = normalizedStoreMessage.includes('start chat')
      ? 'Couldn’t start chat. Please retry.'
      : normalizedStoreMessage.includes('save message')
        ? timelineMessages.value.some((message) => message.unsaved)
          ? 'Response generated but couldn’t be saved. Retry save?'
          : 'Message not saved. Retry sending?'
        : 'Something went wrong. Please retry.'

    prompt.value = draftPrompt
  }

  // Validates the user can send and handles guest redirect policy.
  async function canSendPrompt(cleanPrompt) {
    if (!cleanPrompt) return false
    if (await redirectGuest(cleanPrompt)) return false
    return true
  }

  // Snapshots the send-flow context so retries/error paths can restore original intent.
  function prepareSendContext() {
    const draftPrompt = prompt.value
    const cleanPrompt = draftPrompt.trim()
    const classIdForChat = resolveClassIdForChat()
    if (!classIdForChat) return null

    const selectedModelValue = resolveSelectedModelValue()

    return {
      draftPrompt,
      cleanPrompt,
      classIdForChat,
      selectedModelValue
    }
  }

  // --- Generation + timeline mutation helpers ------------------------------

  // Creates an optimistic assistant row so users see immediate response progress.
  function addPendingAssistantMessage(assistantText) {
    const pendingAssistantId = `assistant-unsaved-${createId()}`

    timelineMessages.value.push({
      id: pendingAssistantId,
      role: 'assistant',
      text: assistantText,
      unsaved: true
    })

    return pendingAssistantId
  }

  // Guards optimistic updates so only the currently selected chat is mutated.
  function isChatStillSelected(chatId) {
    return Number(chatStore.selectedChatId) === Number(chatId)
  }

  // Generates final assistant timeline state for both selected and background chat scenarios.
  async function processSuccessfulAiResponse({
    aiResponse,
    ensuredChat,
    draftPrompt
  }) {
    const assistantText = resolveAssistantText(aiResponse, draftPrompt)
    if (!assistantText) return false

    if (!isChatStillSelected(ensuredChat.id)) {
      await saveAssistantMessage({
        chatId: ensuredChat.id,
        assistantText
      })
      prompt.value = ''
      return true
    }

    const pendingAssistantId = addPendingAssistantMessage(assistantText)
    await scrollToLatestTurn()

    await saveAssistantMessage({
      chatId: ensuredChat.id,
      assistantText,
      pendingAssistantId
    })

    prompt.value = ''
    return true
  }

  // Runs the full send sequence: ensure chat, persist user message, call AI, persist assistant.
  async function executeSendFlow({
    cleanPrompt,
    classIdForChat,
    selectedModelValue,
    draftPrompt
  }) {
    const ensuredChat = await ensureChat({
      cleanPrompt,
      classIdForChat,
      selectedModelValue
    })

    await saveUserMessage({
      chatId: ensuredChat.id,
      cleanPrompt
    })

    const aiResponse = await requestAssistantResponse({
      cleanPrompt,
      chatId: ensuredChat.id,
      classIdForChat,
      draftPrompt
    })

    if (!aiResponse) return

    await processSuccessfulAiResponse({ aiResponse, ensuredChat, draftPrompt })
  }

  // Marks interaction lifecycle start so UI can block duplicate sends and clear stale errors.
  function startInteraction() {
    interactionLoading.value = true
    interactionError.value = ''
  }

  // Marks interaction lifecycle completion regardless of success/failure.
  function finishInteraction() {
    interactionLoading.value = false
  }

  // Public entry point for composer submit actions.
  async function sendPrompt() {
    if (interactionLoading.value) return

    const cleanPrompt = prompt.value.trim()
    if (!(await canSendPrompt(cleanPrompt))) return

    const sendContext = prepareSendContext()
    if (!sendContext) return

    startInteraction()

    try {
      await executeSendFlow(sendContext)
    } catch (error) {
      reportOuterFailure(error, sendContext.draftPrompt)
    } finally {
      finishInteraction()
    }
  }

  return { prompt, interactionLoading, sendPrompt }
}
