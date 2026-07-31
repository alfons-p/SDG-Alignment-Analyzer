import { useCallback, useState } from 'react'
import { Upload, FileText } from 'lucide-react'

const MAX_BYTES = 50 * 1024 * 1024

export function FileDropzone({ onFile }: { onFile: (file: File) => void }) {
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<File | null>(null)

  const handle = useCallback(
    (file: File) => {
      setError('')
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Only PDF files are supported')
        return
      }
      if (file.size > MAX_BYTES) {
        setError('File too large. Maximum is 50MB')
        return
      }
      setSelected(file)
      onFile(file)
    },
    [onFile],
  )

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          const file = e.dataTransfer.files[0]
          if (file) handle(file)
        }}
        className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
          dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-300'
        }`}
      >
        <Upload className="mx-auto text-slate-400 mb-3" size={36} />
        <p className="text-sm text-slate-600 font-medium">Drop PDF here or click to select</p>
        <p className="text-xs text-slate-400 mt-1">Max 50MB</p>
        <input
          type="file"
          accept=".pdf"
          className="absolute inset-0 opacity-0 cursor-pointer"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handle(file)
          }}
          style={{ display: 'none' }}
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className="mt-3 inline-block px-4 py-1.5 bg-blue-600 text-white text-sm rounded-lg cursor-pointer hover:bg-blue-700 transition-colors"
        >
          Browse files
        </label>
      </div>
      {error && <p className="text-red-600 text-xs mt-2">{error}</p>}
      {selected && !error && (
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
