const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY

export async function startAnalytics(): Promise<void> {
  if (!POSTHOG_KEY) return
  const { default: posthog } = await import('posthog-js')
  posthog.init(POSTHOG_KEY, {
    api_host: 'https://eu.i.posthog.com',
    cookieless_mode: 'always',
    disable_session_recording: true,
  })
}
