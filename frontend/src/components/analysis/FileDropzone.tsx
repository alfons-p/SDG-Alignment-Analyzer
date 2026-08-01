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
        className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
          dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-300'
        }`}
      >
        <Upload className="mx-auto text-slate-400 mb-3" size={36} />
        <p className="text-sm text-slate-600 font-medium">
          {multiple ? 'Drop PDFs here, or' : 'Drop PDF here or click to select'}
        </p>
        <p className="text-xs text-slate-400 mt-1">
          {multiple ? 'a whole folder or several files' : 'PDF only'}
        </p>

        <div className="mt-3 flex items-center justify-center gap-2">
          <label
            htmlFor="file-upload"
            className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg cursor-pointer hover:bg-blue-700 transition-colors"
          >
            <FileText size={14} /> {multiple ? 'Select PDFs' : 'Browse files'}
          </label>
          {multiple && (
            <label
              htmlFor="folder-upload"
              className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-slate-100 text-slate-700 text-sm rounded-lg cursor-pointer hover:bg-slate-200 transition-colors"
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

      {error && <p className="text-amber-600 text-xs mt-2">{error}</p>}
      {!multiple && selected && (
        <div className="flex items-center gap-2 mt-3 text-sm text-slate-700 bg-slate-50 p-2 rounded-lg">
          <FileText size={16} className="text-blue-600" />
          <span className="truncate">{selected.name}</span>
          <span className="text-xs text-slate-400">
            ({(selected.size / 1024 / 1024).toFixed(1)} MB)
          </span>
        </div>
      )}
    </div>
  )
}
