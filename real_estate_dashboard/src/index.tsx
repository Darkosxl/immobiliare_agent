import { Hono } from 'hono'
import { HTTPException } from 'hono/http-exception'
import { renderer } from './renderer'
import type { CallLog } from './types'

type Bindings = {
  VAPI_API_KEY: string
}

const app = new Hono<{ Bindings: Bindings }>()

app.use(renderer)

app.get('/', (c) => {
  return c.render(<h1>Hello!</h1>)
})

app.get('/chat_logs', async (c) => {
  const VAPI_API_KEY = c.env.VAPI_API_KEY
  if (!VAPI_API_KEY) {
    throw new HTTPException(500, { message: 'VAPI_API_KEY is not set' })
  }

  // Fetch real calls from Vapi
  const response = await fetch('https://api.vapi.ai/call', {
    headers: {
      'Authorization': `Bearer ${VAPI_API_KEY}`
    }
  })

  if (!response.ok) {
    throw new HTTPException(502, { message: 'Failed to fetch calls from Vapi' })
  }

  const logs = await response.json() as CallLog[]

  return c.render(
    <div class="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <script dangerouslySetInnerHTML={{ __html: `console.log("Full Logs Data:", ${JSON.stringify(logs)})` }} />
      <div class="max-w-3xl mx-auto">
        <div class="flex items-center justify-between mb-8">
          <h1 class="text-3xl font-bold text-gray-900">Call Logs</h1>
          <a href="/" class="text-indigo-600 hover:text-indigo-900 font-medium">Back to Home</a>
        </div>

        <div class="space-y-4">
          {logs.map((log) => (
            <details class="group bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-200">
              <summary class="flex items-center justify-between p-6 cursor-pointer list-none select-none bg-white hover:bg-gray-50 transition-colors">
                <div class="flex items-center gap-4">
                  <div class="flex-shrink-0">
                    <div class="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" /></svg>
                    </div>
                  </div>
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">
                      {new Date(log.startedAt).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                    </h3>
                    <p class="text-sm text-gray-500">{log.status} • ${log.cost?.toFixed(2) || "0.00"}</p>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  {log.artifact?.recordingUrl && (
                    <a
                      href={log.artifact.recordingUrl}
                      target="_blank"
                      onClick={(e) => e.stopPropagation()}
                      class="text-sm text-indigo-600 hover:text-indigo-800 font-medium px-3 py-1 rounded-full bg-indigo-50 hover:bg-indigo-100 transition-colors"
                    >
                      Listen
                    </a>
                  )}
                  <svg class="w-5 h-5 text-gray-400 group-open:rotate-180 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </summary>

              <div class="border-t border-gray-100 bg-gray-50/50 p-6">
                <div class="space-y-6">
                  {log.artifact?.messages?.map((msg: any, index: number) => {
                    // Skip the first message if it's the system prompt
                    if (index === 0 && msg.role === 'assistant') return null

                    const content = msg.message || msg.content
                    const hasContent = !!content
                    const toolCalls = msg.tool_calls || msg.toolCalls || []
                    const hasToolCalls = toolCalls.length > 0
                    const functionCall = msg.function_call || msg.functionCall
                    const hasFunctionCall = !!functionCall

                    if (!hasContent && !hasToolCalls && !hasFunctionCall) return null

                    return (
                      <div class={`flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        {/* Text Content */}
                        {hasContent && (
                          <div class={`max-w-[80%] rounded-2xl px-5 py-3 shadow-sm ${msg.role === 'user'
                            ? 'bg-indigo-600 text-white rounded-br-none'
                            : 'bg-white text-gray-800 border border-gray-200 rounded-bl-none'
                            }`}>
                            <div class="text-xs opacity-70 mb-1 font-medium uppercase tracking-wider">
                              {msg.role === 'user' ? 'User' : 'AI Assistant'}
                            </div>
                            <div class="text-lg leading-relaxed whitespace-pre-wrap">
                              {content}
                            </div>
                          </div>
                        )}

                        {/* Tool Calls */}
                        {hasToolCalls && toolCalls.map((tool: any) => {
                          let args = {}
                          try {
                            args = typeof tool.function?.arguments === 'string'
                              ? JSON.parse(tool.function.arguments)
                              : tool.function?.arguments || tool.arguments || {}
                          } catch (e) {
                            args = { raw: tool.function?.arguments }
                          }

                          return (
                            <div class="max-w-[80%] bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-900 shadow-sm">
                              <div class="flex items-center gap-2 mb-3 border-b border-yellow-200 pb-2">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-yellow-600"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></svg>
                                <span class="font-bold uppercase tracking-wide text-yellow-700">TOOL CALL: {tool.function?.name || tool.name || "Unknown"}</span>
                              </div>

                              <div class="space-y-1 font-mono text-xs">
                                {Object.entries(args).map(([key, value]) => (
                                  <div class="flex">
                                    <span class="font-semibold text-yellow-800 min-w-[120px]">- {key}:</span>
                                    <span class="text-yellow-900 break-all">{String(value)}</span>
                                  </div>
                                ))}
                                {Object.keys(args).length === 0 && <div class="italic opacity-70">No parameters</div>}
                              </div>
                            </div>
                          )
                        })}

                        {/* Legacy Function Call */}
                        {hasFunctionCall && (() => {
                          let args = {}
                          try {
                            args = typeof functionCall.arguments === 'string'
                              ? JSON.parse(functionCall.arguments)
                              : functionCall.arguments || {}
                          } catch (e) {
                            args = { raw: functionCall.arguments }
                          }

                          return (
                            <div class="max-w-[80%] bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-900 shadow-sm">
                              <div class="flex items-center gap-2 mb-3 border-b border-yellow-200 pb-2">
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-yellow-600"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></svg>
                                <span class="font-bold uppercase tracking-wide text-yellow-700">FUNCTION CALL: {functionCall.name}</span>
                              </div>
                              <div class="space-y-1 font-mono text-xs">
                                {Object.entries(args).map(([key, value]) => (
                                  <div class="flex">
                                    <span class="font-semibold text-yellow-800 min-w-[120px]">- {key}:</span>
                                    <span class="text-yellow-900 break-all">{String(value)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )
                        })()}
                      </div>
                    )
                  }) || (
                      <div class="text-center py-8 text-gray-500">
                        No transcript available for this call.
                      </div>
                    )}
                </div>
              </div>
            </details>
          ))}
        </div>
      </div>
    </div>
  )
})

export default app


