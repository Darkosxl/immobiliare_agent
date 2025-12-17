import app from './index'

const port = parseInt(process.env.PORT || '5173')

console.log(`Server running on http://0.0.0.0:${port}`)

// Pass environment variables to Hono context
const env = {
    VAPI_API_KEY: process.env.VAPI_API_KEY,
    GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET,
    DASHBOARD_PASSWORD: process.env.DASHBOARD_PASSWORD,
    BACKEND_URL: process.env.BACKEND_URL,
    REDIRECT_URI: process.env.REDIRECT_URI,
}

export default {
    port,
    fetch: (request: Request) => app.fetch(request, env),
}
