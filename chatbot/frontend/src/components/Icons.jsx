// One consistent inline icon set (24px grid, 2px round stroke).
const PATHS = {
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
  check: <path d="M20 6 9 17l-5-5" />,
  checkCircle: <><circle cx="12" cy="12" r="9" /><path d="m8.5 12.5 2.5 2.5 4.5-5" /></>,
  xCircle: <><circle cx="12" cy="12" r="9" /><path d="m9 9 6 6M15 9l-6 6" /></>,
  alertCircle: <><circle cx="12" cy="12" r="9" /><path d="M12 8v4.5M12 16h.01" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
  file: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></>,
  paperclip: <path d="M21.4 11 12.2 20.2a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 0 1 5.7 5.7l-9.2 9.2a2 2 0 0 1-2.9-2.8l8.5-8.5" />,
  send: <><path d="m22 2-11 11" /><path d="M22 2 15 22l-4-9-9-4z" /></>,
  thumbUp: <><path d="M7 10v11H3V10z" /><path d="M7 10l4-8a3 3 0 0 1 3 3v4h6a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.6 21H7" /></>,
  thumbDown: <><path d="M17 14V3h4v11z" /><path d="m17 14-4 8a3 3 0 0 1-3-3v-4H4a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.4 3H17" /></>,
  refresh: <><path d="M21 12a9 9 0 1 1-3-6.7L21 8" /><path d="M21 3v5h-5" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  expand: <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />,
  minimize: <path d="M5 12h14" />,
  close: <path d="M18 6 6 18M6 6l12 12" />,
  chat: <path d="M21 12a8 8 0 0 1-11.7 7.1L3 21l1.9-5.7A8 8 0 1 1 21 12z" />,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  arrowRight: <path d="M5 12h14M13 6l6 6-6 6" />,
  external: <><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>,
  shield: <><path d="M12 3 4 6v6c0 4.5 3.2 8 8 9 4.8-1 8-4.5 8-9V6z" /><path d="m9 12 2 2 4-4" /></>,
  quote: <><path d="M7 7h4v5a4 4 0 0 1-4 4" /><path d="M15 7h4v5a4 4 0 0 1-4 4" /></>,
  wifiOff: <><path d="M2 2l20 20M8.5 16.4a5 5 0 0 1 7 0M5 12.9a10 10 0 0 1 5-2.7M19 12.9a10 10 0 0 0-2.4-1.8M2 8.8a15 15 0 0 1 4.2-2.7M22 8.8A15 15 0 0 0 12 5M12 20h.01" /></>,
  sprout: <><path d="M7 20h10M12 20v-9" /><path d="M12 11c0-4 2.5-6 7-6 0 4-2.5 6-7 6zM12 13c0-3-2-5-6-5 0 3 2 5 6 5z" /></>,
  home: <><path d="m3 11 9-8 9 8" /><path d="M5 10v10h14V10M10 20v-6h4v6" /></>,
  database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></>,
}

export default function Icon({ name, className = 'h-5 w-5', ...rest }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {PATHS[name]}
    </svg>
  )
}

// Logo mark: a civic dome on a rounded tile with a red accent base.
// tone="light" is a white tile (for dark backgrounds), "dark" a navy tile.
export function LogoMark({ className = 'h-8 w-8', tone = 'light' }) {
  const tile = tone === 'light' ? '#ffffff' : '#0b2447'
  const glyph = tone === 'light' ? '#0b2447' : '#ffffff'
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="8" fill={tile} />
      <path d="M16 6.5c-3.6 0-6.5 2.6-6.5 5.8V13h13v-.7c0-3.2-2.9-5.8-6.5-5.8z" fill={glyph} />
      <rect x="8.5" y="14.5" width="15" height="1.8" rx=".9" fill={glyph} />
      <rect x="10.2" y="17.4" width="2.2" height="5.4" rx=".6" fill={glyph} />
      <rect x="14.9" y="17.4" width="2.2" height="5.4" rx=".6" fill={glyph} />
      <rect x="19.6" y="17.4" width="2.2" height="5.4" rx=".6" fill={glyph} />
      <rect x="8" y="24" width="16" height="2" rx="1" fill="#c8283f" />
    </svg>
  )
}
