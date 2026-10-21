import { useCallback, useEffect, useState } from 'react'

const THEME_KEY = 'gsa_theme'

function readSaved() {
  try {
    return localStorage.getItem(THEME_KEY)
  } catch {
    return null
  }
}

function systemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

// Follows the system setting until the user picks a theme with the toggle.
export function useTheme() {
  const [theme, setTheme] = useState(() => readSaved() || systemTheme())

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      if (!readSaved()) setTheme(systemTheme())
    }
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark'
      try {
        localStorage.setItem(THEME_KEY, next)
      } catch {
        // storage unavailable: theme still applies for this visit
      }
      return next
    })
  }, [])

  return { theme, toggle }
}
