import { LANGUAGES } from '../utils/api'
import Icon, { LogoMark } from './Icons'
import SyncStatusBadge from './SyncStatusBadge'

const LANGUAGE_NAMES = { en: 'English', ta: 'Tamil', hi: 'Hindi' }
const LANGUAGE_TAGS = { en: 'en', ta: 'ta', hi: 'hi' }

export default function Header({ language, onLanguageChange, onNewConversation, theme, onToggleTheme }) {
  return (
    <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between gap-2 border-b border-white/10 bg-brand px-3 sm:px-5">
      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
        <LogoMark className="h-8 w-8 shrink-0 rounded-lg" />
        <span className="hidden text-base font-bold tracking-tight text-white sm:inline">SchemeBot</span>
        <button
          type="button"
          onClick={onNewConversation}
          aria-label="New conversation"
          className="flex h-9 items-center gap-1.5 rounded-full border border-white/30 px-2.5 text-xs font-medium text-white transition-colors hover:bg-white/10 sm:px-3"
        >
          <Icon name="plus" className="h-4 w-4" />
          <span className="hidden sm:inline">New conversation</span>
        </button>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <SyncStatusBadge />
        <div role="group" aria-label="Answer language" className="flex gap-1">
          {LANGUAGES.map((lang) => {
            const active = language === lang.code
            return (
              <button
                key={lang.code}
                type="button"
                lang={LANGUAGE_TAGS[lang.code]}
                aria-pressed={active}
                aria-label={LANGUAGE_NAMES[lang.code]}
                onClick={() => onLanguageChange(lang.code)}
                className={`h-9 rounded-full px-2.5 text-xs font-semibold transition-colors sm:px-3 ${
                  active ? 'bg-accent text-white' : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                {lang.label}
              </button>
            )
          })}
        </div>
        <button
          type="button"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-pressed={theme === 'dark'}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/30 text-white transition-colors hover:bg-white/10"
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
