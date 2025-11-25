import { apiClient } from '@/lib/api'
import type {ChatMessage, ChatRequest, ChatResponse, OrchestrationRequest, OrchestrationResponse } from '@shared/types'

// Re-export for compatibility
export type {ChatMessage, ChatRequest, ChatResponse}

export const chatService = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const orchestrationRequest: OrchestrationRequest = {
      user_query: request.message,
      context: {
        conversation_history: request.conversation_history || [],
        current_recipe_id: request.current_recipe_id,
        recipe_id: 101,
      },
      user_profile: request.user_profile,
    }
    
    const response = await apiClient.post<OrchestrationResponse>(
      '/api/orchestrate',
      orchestrationRequest
    )

    return {
      message: this._formatMessage(response.data),
      intent: response.data.intent_detected,
      data: response.data.final_result || {},
      suggestions: this._generateSuggestions(response.data),
    }
  },

  _formatMessage(response: OrchestrationResponse): string {
    // Generic fallback in case of global failure
    if (!response.success) {
      return response.message || "I couldn't process your request, could you please rephrase it?"
    }

    const intent = response.intent_detected
    const final = response.final_result || {}

    switch (intent) {
      case 'multi_step':
        return this._formatMultiStep(response)

      case 'search':
        return this._formatSearchResults(final)

      case 'transform':
        return this._formatTransformResult(final)

      default:
        return "I processed your request, but I don't have a specific response format for this type of action yet."
    }
  },

  _generateSuggestions(response: OrchestrationResponse): string[] {
    const intent = response.intent_detected
    const final = response.final_result || {}
    const results = Array.isArray(final.results) ? final.results : []

    if (intent === 'search' && results.length) {
      return [
        "Transform recipe #1 to make it higher in protein",
        "Transform recipe #1 into a lactose-free version",
        "Give me more details about recipe #1",
        "Suggest other recipes with fewer calories",
      ]
    }

    if (intent === 'transform') {
      return [
        "Show me another possible transformation",
        "Compare this recipe with a classic version",
        "Suggest a similar recipe that's quicker to prepare",
      ]
    }

    if (intent === 'multi_step') {
      return [
        "Do the same thing with another base (chicken, fish...)",
        "Explain step by step what you did",
      ]
    }

    return [
      "Find me a healthy recipe using my ingredients",
      "Transform a recipe into a low-carb version",
      "Suggest a light dinner for tonight",
    ]
  },

  async detectIntent(message: string): Promise<{ intent: string; confidence: number }> {
    const response = await apiClient.post('/api/orchestrate/intent', { message })
    return response.data
  },

  _formatSearchResults(final: Record<string, any>): string {
    const results = Array.isArray(final.results) ? final.results : []

    if (!results.length) {
      return "I couldn't find any recipes that exactly match your request. You can refine your criteria or be a bit less strict with your constraints."
    }

    const total = results.length
    const intro =
      total === 1
        ? "I found 1 recipe you might like:\n\n"
        : `I found ${total} recipes that match your request:\n\n`

    const lines = results.map((r, index) => {
      const name = r.name ?? 'Recipe'
      const desc = r.description ?? ''
      const nutrition = r.nutrition ?? {}
      const calories = nutrition.calories ?? 'N/A'
      const protein = nutrition.protein_g ?? 'N/A'
      const scoreHealth = r.score_health ?? 'N/A'

      return (
        `${index + 1}. ${name}\n` +
        `- Calories: ${calories}\n` +
        `- Protein: ${protein} g\n` +
        `- Health score: ${scoreHealth}\n` +
        `${desc ? `- Description: ${desc}\n` : ''}`
      )
    })

    return intro + lines.join('\n')
  },

  _formatTransformResult(final: Record<string, any>): string {
    const originalName = final.original_name ?? 'the recipe'
    const transformedName = final.transformed_name ?? originalName

    const before = final.nutrition_before ?? {}
    const after = final.nutrition_after ?? {}
    const delta = final.delta ?? {}

    const caloriesBefore = before.calories ?? 'N/A'
    const caloriesAfter = after.calories ?? 'N/A'
    const proteinBefore = before.protein_g ?? 'N/A'
    const proteinAfter = after.protein_g ?? 'N/A'
    const carbsBefore = before.carbs_g ?? 'N/A'
    const carbsAfter = after.carbs_g ?? 'N/A'
    const scoreBefore = before.score_health ?? 'N/A'
    const scoreAfter = after.score_health ?? 'N/A'
    const deltaScore = delta.score_health ?? 'N/A'

    const substitutions = Array.isArray(final.substitutions) ? final.substitutions : []
    const subsLines = substitutions.map(
      (s) => `- ${s.original_ingredient} → ${s.substitute_ingredient} (${s.reason})`
    )

    return (
      `I transformed ${originalName} into ${transformedName} according to your constraints.\n\n` +
      `Before:\n` +
      `- Calories: ${caloriesBefore}\n` +
      `- Protein: ${proteinBefore} g\n` +
      `- Carbs: ${carbsBefore} g\n` +
      `- Health score: ${scoreBefore}\n\n` +
      `After:\n` +
      `- Calories: ${caloriesAfter}\n` +
      `- Protein: ${proteinAfter} g\n` +
      `- Carbs: ${carbsAfter} g\n` +
      `- Health score: ${scoreAfter} (DELTA: ${deltaScore} points)\n\n` +
      `Main substitutions:\n` +
      `${subsLines.length ? subsLines.join('\n') : '- No substitutions listed.'}\n`
    )
  },

  _formatMultiStep(response: OrchestrationResponse): string {
    const final = response.final_result || {}
    const steps = response.steps || []

    if (!steps.length) {
      return "I tried to execute multiple actions, but no steps could be completed."
    }

    const stepLines = steps.map((step, idx) => {
      const num = idx + 1
      const agent = step.agent || 'agent'

      if (agent === 'search') {
        return `Step ${num} – Search: "${step.input.query}" → ${step.output.results_count} result(s)`
      }

      if (agent === 'transform') {
        return `Step ${num} – Transformation: recipe ${step.input.recipe_id}, goal "${step.input.goal}"`
      }

      return `Step ${num} – Agent "${agent}" (${step.action}) executed`
    })

    let finalSummary = ''

    if (final.original_name || final.transformed_name) {
      finalSummary = this._formatTransformResult(final)
    } else if (Array.isArray(final.results)) {
      finalSummary = this._formatSearchResults(final)
    } else if (final.error) {
      finalSummary = `Final result: ${final.error}`
    } else {
      finalSummary =
        "Final result: the multi-step request was executed, but I don't have a detailed summary for this type of result."
    }

    return (
      `I executed multiple steps to process your request:\n` +
      `${stepLines.join('\n')}\n\n` +
      `${finalSummary}\n`
    )
  }

}

export default chatService;
