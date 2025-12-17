import app from './index'

const port = parseInt(process.env.PORT || '5173')

console.log(`Server running on http://0.0.0.0:${port}`)

export default {
    port,
    fetch: app.fetch,
}
