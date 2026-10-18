import '@fontsource/young-serif'
import '@fontsource/hanken-grotesk/400.css'
import '@fontsource/hanken-grotesk/600.css'
import '@fontsource/spline-sans-mono/400.css'
import '@fontsource/spline-sans-mono/500.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { startAnalytics } from './analytics'
import { App } from './App'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

startAnalytics()
