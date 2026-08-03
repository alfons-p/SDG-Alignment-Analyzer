import { useCallback, useState } from 'react'
import { Upload, FolderOpen, FileText } from 'lucide-react'

// webkitdirectory is a non-standard input attribute; declare it for TS/JSX.
declare module 'react' {
  interface InputHTMLAttributes<T> {
    webkitdirectory?: string
    directory?: string
  }
}

type Props = {
  /** Single-file callback (back-compat). Receives the first accepted PDF. */
  onFile?: (file: File) => void
  /** Multi-file callback. Receives all accepted PDFs (used in batch mode). */
  onFiles?: (files: File[]) => void
  /** Allow selecting many files / a folder. */
  multiple?: boolean
}

export function FileDropzone({ onFile, onFiles, multiple = false }: Props) {
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<File | null>(null)

  const accept = useCallback(
    (files: File[]) => {
      setError('')
      const pdfs = files.filter((f) => f.name.toLowerCase().endsWith('.pdf'))
      const nonPdf = files.length - pdfs.length

      if (!pdfs.length) {
        setError(files.length ? 'No PDF files found' : 'No files selected')
        return
      }
      if (nonPdf) setError(`Skipped ${nonPdf} non-PDF file${nonPdf === 1 ? '' : 's'}.`)

      if (multiple) {
        onFiles?.(pdfs)
      } else {
        setSelected(pdfs[0])
        onFile?.(pdfs[0])
      }
    },
    [multiple, onFile, onFiles],
  )

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          accept(Array.from(e.dataTransfer.files))
        }}
        style={{
          position: 'relative',
          border: `2px dashed ${dragOver ? 'var(--color-accent)' : 'color-mix(in srgb, var(--color-text) 22%, transparent)'}`,
          borderRadius: 18,
          padding: 40,
          textAlign: 'center',
          transition: 'border-color .15s, background .15s',
          background: dragOver ? 'var(--color-accent-100)' : 'transparent',
        }}
      >
        <Upload style={{ margin: '0 auto 12px', color: 'color-mix(in srgb, var(--color-text) 45%, transparent)' }} size={36} />
        <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)' }}>
          {multiple ? 'Drop PDFs here, or' : 'Drop PDF here or click to select'}
        </p>
        <p style={{ fontSize: 12, color: 'color-mix(in srgb, var(--color-text) 50%, transparent)', marginTop: 4 }}>
          {multiple ? 'a whole folder or several files' : 'PDF only'}
        </p>

        <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <label
            htmlFor="file-upload"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 16px', background: 'var(--color-accent)', color: 'var(--color-bg)', fontSize: 13.5, borderRadius: 999, cursor: 'pointer' }}
          >
            <FileText size={14} /> {multiple ? 'Select PDFs' : 'Browse files'}
          </label>
          {multiple && (
            <label
              htmlFor="folder-upload"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 16px', background: 'var(--color-surface)', color: 'var(--color-text)', border: '1px solid color-mix(in srgb, var(--color-text) 15%, transparent)', fontSize: 13.5, borderRadius: 999, cursor: 'pointer' }}
            >
              <FolderOpen size={14} /> Pick folder
            </label>
          )}
        </div>

        <input
          type="file"
          accept=".pdf"
          multiple={multiple}
          className="hidden"
          id="file-upload"
          onChange={(e) => { accept(Array.from(e.target.files ?? [])); e.target.value = '' }}
        />
        {multiple && (
          <input
            type="file"
            webkitdirectory=""
            directory=""
            multiple
            className="hidden"
            id="folder-upload"
            onChange={(e) => { accept(Array.from(e.target.files ?? [])); e.target.value = '' }}
          />
        )}
      </div>

      {error && <p style={{ fontSize: 12, color: 'var(--color-accent-700)', marginTop: 8 }}>{error}</p>}
      {!multiple && selected && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontSize: 14, color: 'var(--color-text)', background: 'var(--color-surface)', padding: 10, borderRadius: 12 }}>
          <FileText size={16} style={{ color: 'var(--color-accent)' }} />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selected.name}</span>
          <span style={{ fontSize: 12, color: 'color-mix(in srgb, var(--color-text) 45%, transparent)' }}>
            ({(selected.size / 1024 / 1024).toFixed(1)} MB)
          </span>
        </div>
      )}
    </div>
  )
}
