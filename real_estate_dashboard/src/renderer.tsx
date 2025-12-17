import { jsxRenderer } from 'hono/jsx-renderer'

export const renderer = jsxRenderer(({ children }) => {
  return (
    <html>
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Real Estate AI Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>{`
          body { margin: 0; font-family: system-ui, -apple-system, sans-serif; }
        `}</style>
      </head>
      <body>{children}</body>
    </html>
  )
})
