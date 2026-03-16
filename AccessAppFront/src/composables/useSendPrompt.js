import { ref } from 'vue'
import { buildFirstChatTitle, createId, readAssistantText, withSingleRetry } from '../utils/helpers'
import { useFeatureStore } from '../stores/featureStore'

export function useSendPrompt({ 
  auth, 
  router, 
  chatStore, 
  classStore, 
  timelineMessages, 
  scrollToLatestTurn, 
  interactionError 
}) {
  const prompt = ref('')
  const interactionLoading = ref(false)
  const featureStore = useFeatureStore()


  function logSendCheckpoint(label, details = {}) {
    if (!import.meta.env.DEV) return
    console.info(`[useSendPrompt] ${label}`, details)
  }

  async function redirectGuest(cleanPrompt) {
    if (auth.role !== 'guest') return false
    interactionError.value = 'Please log in to send a prompt.'
    await router.push({ path: '/login', query: { next: '/', prompt: cleanPrompt } })
    return true
  }

  function resolveClassIdForChat() {
    const classIdForChat = classStore.selectedClassId || classStore.classes[0]?.id
    if (!classIdForChat) {
      interactionError.value = 'No class is available for this account yet.'
      return null
    }

    return classIdForChat
  }

  function resolveModelSelection() {
    const selectedModelValue = String(chatStore.selectedModel || '').trim()
    const [selectedProvider = '', ...modelParts] = selectedModelValue.split('::')
    const selectedModelId = modelParts.join('::').trim()
    const hasValidModelSelection = Boolean(selectedModelValue && selectedProvider.trim() && selectedModelId)

    if (!hasValidModelSelection) {
      interactionError.value = 'Please select a model before sending your prompt.'
      return null
    }
    return { 
      selectedModelValue, 
      selectedProvider: selectedProvider.trim(), 
      selectedModelId 
    }
  }

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

  function buildAiRequestPayload({ 
    cleanPrompt, 
    chatId, 
    classIdForChat,
    selectedProvider, 
    selectedModelId 
  }) {
    const selectedAccessibilityLinkIds = featureStore.selectedLinkIds

    return {
      prompt: cleanPrompt,
      chat_id: chatId,
      provider: selectedProvider || undefined,
      model_id: selectedModelId || undefined,
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

  function resolveAiInteractionErrorMessage(parsedError) {
    const { status, backendMessage, errorCode, errorSource } = parsedError
    const messageLower = String(backendMessage || '').toLowerCase()

    if (status === 400) {
      const rejectedPromptMessage = 'Prompt was rejected. Please edit and retry.'
      return `${rejectedPromptMessage} ${backendMessage}`.trim()
    }


    if (errorCode === 'provider_unavailable') {
      return backendMessage || 'The selected AI provider/model is unavailable. Please switch mode or choose a different model.'
    }
    const isProviderAuthIssue = errorCode === 'upstream_error'
      && errorSource === 'provider_runtime'
      && (status === 401 || messageLower.includes('repository not found') || messageLower.includes('invalid username or password'))

    if (isProviderAuthIssue) {
      return 'The selected Hugging Face model is unavailable or requires authentication. Choose another model or configure valid provider credentials.'
    }

    return backendMessage || 'AI is temporarily unavailable. Please retry.'
  }

  async function requestAssistantResponse({ 
    cleanPrompt, 
    chatId, 
    classIdForChat, 
    selectedProvider, 
    selectedModelId, 
    draftPrompt 
  }) {
    
    const payload = buildAiRequestPayload({ 
      cleanPrompt, 
      chatId, 
      classIdForChat, 
      selectedProvider, 
      selectedModelId 
    })

    try {
      return await chatStore.requestAiInteraction(payload)
    } catch (error) {
      const parsedError = parseAiInteractionError(error)

      if (import.meta.env.DEV) {
        console.error('[useSendPrompt] requestAiInteraction failed', {
          message: error?.message,
          status: parsedError.status,
          responseData: parsedError.responseData,
          errorCode: parsedError.errorCode,
          errorSource: parsedError.errorSource,
          stack: error?.stack
        })
      }

      interactionError.value = resolveAiInteractionErrorMessage(parsedError)
      prompt.value = draftPrompt
      return null
    }
  }

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

async function saveAssistantMessage({ 
  chatId, 
  assistantText, 
  pendingAssistantId 
}) {
    const savedAssistantMessage = await withSingleRetry(() =>
      chatStore.createMessage({
        chat_id: chatId,
        message_text: assistantText,
        help_intent: 'summarization'
      })
    )

    timelineMessages.value = timelineMessages.value.map((message) =>
      message.id === pendingAssistantId
        ? { id: savedAssistantMessage.id, role: 'assistant', text: savedAssistantMessage.message_text }
        : message
    )
    await scrollToLatestTurn()
  }

  function reportOuterFailure(
    error, 
    draftPrompt
  ) {
    if (import.meta.env.DEV) {
      console.error('[useSendPrompt] sendPrompt failed', {
        message: error?.message,
        status: error?.response?.status,
        responseData: error?.response?.data,
        stack: error?.stack
      })
    }

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

  async function canSendPrompt(cleanPrompt) {
    if (!cleanPrompt) return false
    if (await redirectGuest(cleanPrompt)) return false
    return true
  }

  function prepareSendContext() {
    const draftPrompt = prompt.value
    const cleanPrompt = draftPrompt.trim()
    const classIdForChat = resolveClassIdForChat()
    if (!classIdForChat) return null

    const modelSelection = resolveModelSelection()
    if (!modelSelection) return null

    return { 
      draftPrompt, 
      cleanPrompt, 
      classIdForChat, 
      modelSelection 
    }
  }

  function startInteraction() {
    interactionLoading.value = true
    interactionError.value = ''
  }

  function finishInteraction() {
    interactionLoading.value = false
  }

  function resolveAssistantText(
    aiResponse, 
    draftPrompt
  ) {
    const assistantText = readAssistantText(aiResponse)
    if (assistantText) return assistantText

    interactionError.value = 'Assistant response was not in a usable format. Please retry.'
    prompt.value = draftPrompt
    return ''
  }

  async function processSuccessfulAiResponse({ 
    aiResponse, 
    ensuredChat, 
    draftPrompt 
  }) {
    const assistantText = resolveAssistantText(aiResponse, draftPrompt)
    if (!assistantText) return false

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

  async function executeSendFlow({ 
    cleanPrompt, 
    classIdForChat, 
    modelSelection, 
    draftPrompt 
  }) {
    logSendCheckpoint('before ensureActiveChat', {
      cleanPromptLength: cleanPrompt.length,
      classIdForChat,
      selectedModelValue: modelSelection.selectedModelValue
    })
    const ensuredChat = await ensureChat({
      cleanPrompt,
      classIdForChat,
      selectedModelValue: modelSelection.selectedModelValue
    })

    logSendCheckpoint('after ensureActiveChat', {
      chatId: ensuredChat?.id
    })

    logSendCheckpoint('before createMessage (user)', {
      chatId: ensuredChat?.id
    })

    await saveUserMessage({ 
      chatId: ensuredChat.id, 
      cleanPrompt })

    logSendCheckpoint('after createMessage (user)', {
      chatId: ensuredChat?.id
    })

    logSendCheckpoint('before requestAiInteraction', {
      chatId: ensuredChat?.id,
      provider: modelSelection.selectedProvider,
      modelId: modelSelection.selectedModelId
    })

    const aiResponse = await requestAssistantResponse({
      cleanPrompt,
      chatId: ensuredChat.id,
      classIdForChat,
      selectedProvider: modelSelection.selectedProvider,
      selectedModelId: modelSelection.selectedModelId,
      draftPrompt
    })

    logSendCheckpoint('after requestAiInteraction', {
      chatId: ensuredChat?.id,
      responseReceived: Boolean(aiResponse)
    })

    if (!aiResponse) return

    logSendCheckpoint('before createMessage (assistant)', {
      chatId: ensuredChat?.id
    })

    await processSuccessfulAiResponse({ aiResponse, ensuredChat, draftPrompt })

    logSendCheckpoint('after createMessage (assistant)', {
      chatId: ensuredChat?.id
    })
    
  }


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
