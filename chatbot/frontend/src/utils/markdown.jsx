// Minimal, safe markdown renderer for chat answers: paragraphs, numbered and
// bulleted lists, **bold**, *italic* and bare http(s) links. Builds React
// elements only (no innerHTML), so model output can't inject markup.
const INLINE = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|https?:\/\/[^\s)]+)/g

function renderInline(text, keyPrefix) {
  return text.split(INLINE).map((part, i) => {
    const key = `${keyPrefix}-${i}`
    if (!part) return null
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={key}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={key}>{part.slice(1, -1)}</em>
    }
    if (/^https?:\/\//.test(part)) {
      const trailing = part.match(/[.,;:!?]+$/)?.[0] || ''
      const href = trailing ? part.slice(0, -trailing.length) : part
      return (
        <span key={key}>
          <a href={href} target="_blank" rel="noopener noreferrer">{href}</a>
          {trailing}
        </span>
      )
    }
    return part
  })
}

export function renderMarkdown(source) {
  const lines = String(source || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let list = null
  let para = []

  const flushPara = () => {
    if (para.length) {
      blocks.push({ type: 'p', text: para.join(' ') })
      para = []
    }
  }
  const flushList = () => {
    if (list) {
      blocks.push(list)
      list = null
    }
  }

  for (const raw of lines) {
    const line = raw.trim()
    const ordered = line.match(/^(\d+)[.)]\s+(.*)$/)
    const bullet = line.match(/^[-*•]\s+(.*)$/)
    if (ordered || bullet) {
      flushPara()
      const type = ordered ? 'ol' : 'ul'
      if (!list || list.type !== type) {
        flushList()
        list = { type, items: [] }
      }
      list.items.push((ordered ? ordered[2] : bullet[1]).trim())
    } else if (!line) {
      flushPara()
      flushList()
    } else if (list && /^\s{2,}/.test(raw)) {
      list.items[list.items.length - 1] += ` ${line}`
    } else {
      flushList()
      para.push(line)
    }
  }
  flushPara()
  flushList()

  return blocks.map((block, i) => {
    if (block.type === 'p') return <p key={i}>{renderInline(block.text, `p${i}`)}</p>
    const Tag = block.type
    return (
      <Tag key={i}>
        {block.items.map((item, j) => (
          <li key={j}>{renderInline(item, `l${i}-${j}`)}</li>
        ))}
      </Tag>
    )
  })
}
