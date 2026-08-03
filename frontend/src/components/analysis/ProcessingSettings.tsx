import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { ProcessingSettings } from '../../types'

interface Props {
  settings: Partial<ProcessingSettings>
  onChange: (s: Partial<ProcessingSettings>) => void
}

function buildUniformThresholds(value: number): Record<number, number> {
  const out: Record<number, number> = {}
  for (let i = 1; i <= 17; i++) out[i] = value
  return out
}

export function ProcessingSettingsPanel({ settings, onChange }: Props) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  const useCustom = settings.use_custom_thresholds ?? false
  const useBert = settings.use_bert_classifier ?? true
  const useHybrid = settings.use_hybrid ?? true

  const universalThreshold = (settings.sdg_thresholds ?? {})[1] ?? 0.5

  return (
    <div className="space-y-5">
      {/* Hybrid model */}
      <div>
        <label className="ps-label">Hybrid model</label>
        <input
          type="text"
          value={settings.model_name ?? 'voyager205/sdg-variant-finetuned'}
          onChange={(e) => onChange({ model_name: e.target.value })}
          className="ps-input"
        />
      </div>

      {/* Engine toggles */}
      <div className="flex flex-wrap gap-3">
        <label className="ps-check">
          <input
            type="checkbox"
            checked={useHybrid}
            onChange={(e) => onChange({ use_hybrid: e.target.checked })}
          />
          Hybrid engine (ST + sdgBERT)
        </label>
        <label className="ps-check">
          <input
            type="checkbox"
            checked={settings.enable_bias_corrections ?? true}
            onChange={(e) => onChange({ enable_bias_corrections: e.target.checked })}
          />
          Bias corrections
        </label>
      </div>

      {/* Activity Sentence Extraction group */}
      <fieldset className="ps-fieldset">
        <legend className="ps-legend">Activity Sentence Extraction</legend>
        <div className="space-y-3 mt-1">
          <label className="ps-check">
            <input
              type="checkbox"
              checked={useBert}
              onChange={(e) => onChange({ use_bert_classifier: e.target.checked })}
            />
            BERT classifier
          </label>

          <label className="ps-check">
            <input
              type="checkbox"
              checked={settings.nofinancial ?? false}
              onChange={(e) => onChange({ nofinancial: e.target.checked })}
            />
            Exclude financial statements
          </label>

          <label className="ps-check">
            <input
              type="checkbox"
              checked={settings.require_action_verb ?? false}
              onChange={(e) => onChange({ require_action_verb: e.target.checked })}
            />
            Require action verb in BERT results
          </label>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="ps-label">Min words</label>
              <input
                type="number"
                min={5}
                max={200}
                value={settings.min_words ?? 20}
                onChange={(e) => onChange({ min_words: +e.target.value })}
                className="ps-input"
              />
            </div>
            <div>
              <label className="ps-label">Max words</label>
              <input
                type="number"
                min={50}
                max={2000}
                value={settings.max_words ?? 500}
                onChange={(e) => onChange({ max_words: +e.target.value })}
                className="ps-input"
              />
            </div>
          </div>

          {useBert && (
            <div>
              <label className="ps-label">
                BERT confidence threshold ({settings.min_confidence ?? 0.7})
              </label>
              <input
                type="range"
                min="0.5"
                max="0.95"
                step="0.05"
                value={settings.min_confidence ?? 0.7}
                onChange={(e) => onChange({ min_confidence: +e.target.value })}
                className="ps-range"
              />
            </div>
          )}
        </div>
      </fieldset>

      {/* Advanced settings */}
      <button type="button" onClick={() => setShowAdvanced(!showAdvanced)} className="ps-adv-btn">
        {showAdvanced ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        Advanced settings
      </button>

      {showAdvanced && (
        <div className="space-y-4 ps-adv-wrap">
          {/* spaCy model */}
          <div>
            <label className="ps-label">spaCy model</label>
            <select
              value={settings.spacy_model ?? 'en_core_web_sm'}
              onChange={(e) => onChange({ spacy_model: e.target.value })}
              className="ps-input"
              style={{ maxWidth: '20rem' }}
            >
              <option value="en_core_web_sm">en_core_web_sm (fast)</option>
              <option value="en_core_web_md">en_core_web_md (medium)</option>
              <option value="en_core_web_lg">en_core_web_lg (accurate)</option>
              <option value="en_core_web_trf">en_core_web_trf (transformer)</option>
            </select>
          </div>

          {/* Top activities */}
          <div>
            <label className="ps-label">Top activities limit (0 = all)</label>
            <input
              type="number"
              min={0}
              value={settings.top_activities ?? 0}
              onChange={(e) => onChange({ top_activities: +e.target.value })}
              className="ps-input"
              style={{ width: '6rem' }}
            />
          </div>

          {/* Ensemble mode (only when hybrid on) */}
          {useHybrid && (
            <div>
              <label className="ps-label">Ensemble mode</label>
              <select
                value={settings.ensemble_mode ?? 'weighted'}
                onChange={(e) => onChange({ ensemble_mode: e.target.value })}
                className="ps-input"
                style={{ maxWidth: '20rem' }}
              >
                <option value="weighted">weighted</option>
                <option value="fallback">fallback</option>
                <option value="single">single</option>
              </select>
            </div>
          )}

          {/* Custom alignment threshold */}
          <div className="space-y-2">
            <label className="ps-check">
              <input
                type="checkbox"
                checked={useCustom}
                onChange={(e) => {
                  const enabled = e.target.checked
                  onChange({
                    use_custom_thresholds: enabled,
                    sdg_thresholds: enabled ? buildUniformThresholds(0.5) : {},
                  })
                }}
              />
              Override alignment threshold
            </label>

            {useCustom && (
              <div>
                <label className="ps-label">
                  Alignment threshold ({universalThreshold.toFixed(2)})
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={universalThreshold}
                  onChange={(e) => {
                    const val = +e.target.value
                    onChange({ sdg_thresholds: buildUniformThresholds(val) })
                  }}
                  className="ps-range"
                />
                <p style={{ fontSize: 10, color: 'color-mix(in srgb, var(--color-text) 45%, transparent)', marginTop: 4 }}>
                  Applied uniformly to all 17 SDGs. Default uses per-SDG optimized thresholds.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
