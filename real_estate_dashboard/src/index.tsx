import { Hono } from 'hono'
import { HTTPException } from 'hono/http-exception'
import { renderer } from './renderer'
import type { CallLog, GoogleToken } from './types'
import { getGoogleAuthURL, getGoogleTokens } from './auth'
import { setCookie, getCookie } from 'hono/cookie'
import { promises as fs, existsSync } from 'fs'
import { spawn } from 'child_process'
import { streamSSE } from 'hono/streaming'

// Helper to get the correct base path for voiceai directory
function getVoiceAIPath(): string {
  return existsSync('/app/real_estate_voiceai') ? '/app/real_estate_voiceai' : '../real_estate_voiceai'
}

type Bindings = {
  VAPI_API_KEY: string
  GOOGLE_CLIENT_ID: string
  GOOGLE_CLIENT_SECRET: string
  DASHBOARD_PASSWORD?: string
  BACKEND_URL?: string
  REDIRECT_URI?: string
}

const app = new Hono<{ Bindings: Bindings }>()

app.use(renderer)

// Authentication Middleware
app.use('*', async (c, next) => {
  const path = c.req.path
  // Public routes
  if (path === '/login' || path.startsWith('/auth') || path.startsWith('/src') || path.startsWith('/@')) {
    return next()
  }

  const token = getCookie(c, 'auth_token')
  if (!token) {
    return c.redirect('/login')
  }

  await next()
})

app.get('/login', (c) => {
  return c.render(
    <div class="min-h-screen flex items-center justify-center bg-gray-50">
      <div class="max-w-md w-full space-y-8 p-8 bg-white rounded-xl shadow-lg border border-gray-100">
        <div class="text-center">
          <h2 class="mt-6 text-3xl font-extrabold text-gray-900">Real Estate AI</h2>
          <p class="mt-2 text-sm text-gray-600">Please sign in to access the dashboard</p>
        </div>
        <form class="mt-8 space-y-6" action="/login" method="post">
          <div class="rounded-md shadow-sm -space-y-px">
            <div>
              <label for="password" class="sr-only">Password</label>
              <input id="password" name="password" type="password" required class="appearance-none rounded-md relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm" placeholder="Enter Password" />
            </div>
          </div>

          <div>
            <button type="submit" class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors">
              Sign in
            </button>
          </div>
        </form>
      </div>
    </div>
  )
})

app.post('/login', async (c) => {
  const body = await c.req.parseBody()
  const password = body['password']
  const correctPassword = c.env.DASHBOARD_PASSWORD

  if (correctPassword && password === correctPassword) {
    setCookie(c, 'auth_token', 'valid', {
      httpOnly: true,
      path: '/',
      maxAge: 86400 * 7, // 7 days
    })
    return c.redirect('/')
  }

  return c.html(
    <div class="min-h-screen flex items-center justify-center bg-gray-50">
      <div class="max-w-md w-full space-y-8 p-8 bg-white rounded-xl shadow-lg border border-gray-100">
        <div class="text-center">
          <h2 class="mt-6 text-3xl font-extrabold text-red-600">Access Denied</h2>
          <p class="mt-2 text-sm text-gray-600">Invalid password. Please try again.</p>
        </div>
        <div class="mt-8">
          <a href="/login" class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors">
            Back to Login
          </a>
        </div>
      </div>
    </div>
  )
})

app.get('/', (c) => {
  const isConnected = !!getCookie(c, 'google_access_token')
  return c.render(
    <DashboardLayout activeTab="home" isConnected={isConnected}>
      <div class="flex flex-col items-center justify-center h-full text-gray-500">
        <h1 class="text-2xl font-semibold mb-2">Welcome to the Dashboard</h1>
        <p>Select an option from the sidebar to get started.</p>
      </div>
    </DashboardLayout>
  )
})

app.get('/auth/google', (c) => {
  const clientId = c.env.GOOGLE_CLIENT_ID
  if (!clientId) return c.text("Missing GOOGLE_CLIENT_ID", 500)

  // Assuming we are running on localhost:5173 for dev
  const redirectUri = c.env.REDIRECT_URI || "http://localhost:5173/auth/google/callback"
  const url = getGoogleAuthURL(clientId, redirectUri)
  return c.redirect(url)
})

app.get('/auth/google/callback', async (c) => {
  const code = c.req.query('code')
  const clientId = c.env.GOOGLE_CLIENT_ID
  const clientSecret = c.env.GOOGLE_CLIENT_SECRET

  if (!code || !clientId || !clientSecret) {
    return c.text("Missing code or credentials", 400)
  }

  try {
    const redirectUri = c.env.REDIRECT_URI || "http://localhost:5173/auth/google/callback"
    const tokens = await getGoogleTokens(code, clientId, clientSecret, redirectUri)

    // Save tokens to shared file for Python backend
    await fs.writeFile(`${getVoiceAIPath()}/google_tokens.json`, JSON.stringify(tokens, null, 2))

    // In a real app, save these tokens to a database associated with the user.
    // For this dashboard, we might just set them in a cookie or log them for now.
    // Let's set a cookie so we can use it later.
    setCookie(c, 'google_access_token', tokens.access_token, {
      httpOnly: true,
      secure: false, // dev
      maxAge: 3600
    })

    return c.redirect('/chat_logs?connected=true')
  } catch (e) {
    return c.text(`Auth failed: ${e}`, 500)
  }
})

app.get('/auth/google/disconnect', async (c) => {
  // Clear cookie
  setCookie(c, 'google_access_token', '', {
    maxAge: 0
  })

  // Delete tokens file
  try {
    await fs.unlink(`${getVoiceAIPath()}/google_tokens.json`)
  } catch (e) {
    // Ignore if file doesn't exist
  }

  // Call Python backend to disconnect
  try {
    const backendUrl = c.env.BACKEND_URL || 'http://localhost:8000'
    await fetch(`${backendUrl}/disconnect`, { method: 'POST' })
  } catch (e) {
    // Ignore if backend is not running
  }

  return c.redirect('/')
})

// Global state for the Python process
let pythonProcess: any = null
const logBuffer: string[] = []
const MAX_LOGS = 1000

function addToLogs(data: string) {
  const lines = data.split('\n')
  for (const line of lines) {
    if (!line.trim()) continue
    logBuffer.push(line)
    if (logBuffer.length > MAX_LOGS) {
      logBuffer.shift()
    }
  }
}

app.post('/api/server/start', async (c) => {
  if (pythonProcess) {
    return c.json({ message: 'Server already running' })
  }

  try {
    // Spawn the Python process
    const basePath = getVoiceAIPath()
    const scriptPath = `${basePath}/fastapi_endpoint.py`
    const pythonPath = `${basePath}/venv/bin/python`

    pythonProcess = spawn(pythonPath, ['-u', scriptPath], {
      cwd: basePath,
      stdio: ['ignore', 'pipe', 'pipe']
    })

    // Stream stdout
    pythonProcess.stdout.on('data', (data: Buffer) => {
      addToLogs(data.toString())
    })

    // Stream stderr
    pythonProcess.stderr.on('data', (data: Buffer) => {
      addToLogs(data.toString())
    })

    addToLogs(`[SYSTEM] Server started with PID: ${pythonProcess.pid}`)

    return c.json({ message: 'Server started', pid: pythonProcess.pid })
  } catch (e) {
    addToLogs(`[SYSTEM] Failed to start server: ${e}`)
    return c.json({ error: String(e) }, 500)
  }
})

app.post('/api/server/stop', async (c) => {
  if (pythonProcess) {
    const pid = pythonProcess.pid
    pythonProcess.kill()

    // Wait for process to actually exit
    await new Promise<void>((resolve) => {
      const checkInterval = setInterval(() => {
        try {
          process.kill(pid, 0) // Check if process exists
        } catch (e) {
          clearInterval(checkInterval)
          resolve()
        }
      }, 100)

      // Timeout after 5 seconds
      setTimeout(() => {
        clearInterval(checkInterval)
        resolve()
      }, 5000)
    })

    pythonProcess = null
    addToLogs('[SYSTEM] Server stopped by user')
    return c.json({ message: 'Server stopped' })
  }
  return c.json({ message: 'Server not running' })
})

// Ensure cleanup on exit
const cleanup = () => {
  if (pythonProcess) {
    console.log('Cleaning up Python process...')
    pythonProcess.kill()
  }
  process.exit()
}

process.on('SIGINT', cleanup)
process.on('SIGTERM', cleanup)
process.on('exit', () => {
  if (pythonProcess) pythonProcess.kill()
})

app.get('/api/server/status', (c) => {
  return c.json({ running: !!pythonProcess })
})

app.get('/api/server/logs', (c) => {
  return streamSSE(c, async (stream) => {
    // Send initial logs
    for (const log of logBuffer) {
      await stream.writeSSE({ data: log })
    }

    // Poll for new logs (simple implementation)
    // In a real app, we'd use an EventEmitter
    let lastIndex = logBuffer.length
    while (true) {
      if (logBuffer.length > lastIndex) {
        const newLogs = logBuffer.slice(lastIndex)
        lastIndex = logBuffer.length
        for (const log of newLogs) {
          await stream.writeSSE({ data: log })
        }
      }
      await stream.sleep(100)
    }
  })
})

const DashboardLayout = (props: { children: any, activeTab: 'logs' | 'server' | 'home', isConnected: boolean }) => {
  return (
    <div class="min-h-screen bg-gray-50 flex">
      {/* Sidebar (25%) */}
      <div class="w-1/4 bg-white border-r border-gray-200 flex flex-col fixed h-full">
        <div class="p-6 border-b border-gray-200">
          <h1 class="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-indigo-600"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
            Real Estate AI
          </h1>
        </div>

        <nav class="flex-1 p-4 space-y-2">
          <a href="/chat_logs" class={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${props.activeTab === 'logs' ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}`}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
            Call Logs
          </a>
          <a href="/server" class={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${props.activeTab === 'server' ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}`}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
            Voice AI Server
          </a>
        </nav>

        <div class="p-4 border-t border-gray-200">
          {props.isConnected ? (
            <div class="space-y-2">
              <div class="flex items-center gap-2 px-4 py-2 bg-green-50 rounded-lg border border-green-100">
                <div class="w-2 h-2 rounded-full bg-green-500"></div>
                <span class="text-sm font-medium text-green-700">Google Connected</span>
              </div>
              <a href="/auth/google/disconnect" class="flex items-center justify-center gap-2 w-full px-4 py-2 border border-red-200 text-sm font-medium rounded-md text-red-600 bg-red-50 hover:bg-red-100 transition-colors">
                Disconnect
              </a>
            </div>
          ) : (
            <a href="/auth/google" class="flex items-center justify-center gap-2 w-full px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors">
              <svg class="w-4 h-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512"><path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path></svg>
              Connect Google
            </a>
          )}
        </div>
      </div>

      {/* Main Content (75%) */}
      <div class="w-3/4 ml-[25%] p-8">
        {props.children}
      </div>
    </div>
  )
}

app.get('/server', (c) => {
  const isConnected = c.req.query('connected') === 'true' || !!getCookie(c, 'google_access_token')

  return c.render(
    <DashboardLayout activeTab="server" isConnected={isConnected}>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col overflow-hidden h-[calc(100vh-4rem)]">
        <div class="p-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-500"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
            Backend Server Console
          </h2>
          <div class="flex items-center gap-2">
            <div id="status-indicator" class="w-3 h-3 rounded-full bg-red-500"></div>
            <span id="status-text" class="text-sm font-medium text-gray-600">Stopped</span>
          </div>
        </div>

        <div class="p-4 bg-gray-50 border-b border-gray-200 flex gap-2">
          <button id="btn-start" class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-medium text-sm transition-colors flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            Start Server
          </button>
          <button id="btn-stop" class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 font-medium text-sm transition-colors flex items-center gap-2" disabled>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>
            Stop Server
          </button>
        </div>

        <div class="flex-1 bg-gray-900 p-4 overflow-auto font-mono text-xs text-green-400" id="terminal">
          <div class="opacity-50 mb-2"># System Ready. Waiting for command...</div>
        </div>
      </div>

      <script dangerouslySetInnerHTML={{
        __html: `
        const btnStart = document.getElementById('btn-start');
        const btnStop = document.getElementById('btn-stop');
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        const terminal = document.getElementById('terminal');
        let evtSource = null;

        function updateStatus(running) {
          if (running) {
            statusIndicator.classList.remove('bg-red-500');
            statusIndicator.classList.add('bg-green-500');
            statusText.innerText = 'Running';
            btnStart.disabled = true;
            btnStart.classList.add('opacity-50', 'cursor-not-allowed');
            btnStop.disabled = false;
            btnStop.classList.remove('opacity-50', 'cursor-not-allowed');
            
            if (!evtSource) {
              startLogStream();
            }
          } else {
            statusIndicator.classList.remove('bg-green-500');
            statusIndicator.classList.add('bg-red-500');
            statusText.innerText = 'Stopped';
            btnStart.disabled = false;
            btnStart.classList.remove('opacity-50', 'cursor-not-allowed');
            btnStop.disabled = true;
            btnStop.classList.add('opacity-50', 'cursor-not-allowed');
            
            if (evtSource) {
              evtSource.close();
              evtSource = null;
            }
          }
        }

        function appendLog(text) {
          const div = document.createElement('div');
          div.innerText = text;
          terminal.appendChild(div);
          terminal.scrollTop = terminal.scrollHeight;
        }

        function startLogStream() {
          evtSource = new EventSource("/api/server/logs");
          evtSource.onmessage = function(event) {
            appendLog(event.data);
          };
          evtSource.onerror = function() {
            console.log("SSE Error");
            evtSource.close();
            evtSource = null;
          };
        }

        btnStart.onclick = async () => {
          try {
            const res = await fetch('/api/server/start', { method: 'POST' });
            if (res.ok) updateStatus(true);
            else appendLog('[ERROR] Failed to start server');
          } catch (e) {
            appendLog('[ERROR] ' + e);
          }
        };

        btnStop.onclick = async () => {
           try {
            const res = await fetch('/api/server/stop', { method: 'POST' });
            if (res.ok) updateStatus(false);
           } catch (e) {
             appendLog('[ERROR] ' + e);
           }
        };

        // Check initial status
        fetch('/api/server/status')
          .then(res => res.json())
          .then(data => updateStatus(data.running));
      `}} />
    </DashboardLayout>
  )
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
  const isConnected = c.req.query('connected') === 'true' || !!getCookie(c, 'google_access_token')

  return c.render(
    <DashboardLayout activeTab="logs" isConnected={isConnected}>
      <script dangerouslySetInnerHTML={{ __html: `console.log("Full Logs Data:", ${JSON.stringify(logs)})` }} />

      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-gray-900">Recent Calls</h2>
        <div class="text-sm text-gray-500">
          {logs.length} calls found
        </div>
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
    </DashboardLayout>
  )
})

export default app
