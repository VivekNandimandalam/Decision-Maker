import { FormEvent, useMemo, useState } from 'react'

import { apiRequest, buildShareLink, CreatedPoll, saveOwnedPoll } from '../lib/polls'

type FieldErrors = {
  question?: string
  options?: string
  expiration?: string
  optionFields: string[]
}

type CreatePollProps = {
  onNavigateToPoll: (pollId: string) => void
  onNavigateToDashboard: () => void
}

const MIN_OPTIONS = 2
const MAX_OPTIONS = 20
const MAX_QUESTION_LENGTH = 255
const MAX_OPTION_LENGTH = 255
const MIN_EXPIRATION_MS = 60_000

const expirationChoices = [
  { value: '1m', label: '1 minute' },
  { value: '5m', label: '5 minutes' },
  { value: '10m', label: '10 minutes' },
  { value: '30m', label: '30 minutes' },
  { value: '1h', label: '1 hour' },
  { value: 'custom', label: 'Custom date and time' },
]

function computeExpiresAt(choice: string, customDatetime: string): string | null {
  const now = new Date()

  if (choice === 'custom') {
    if (!customDatetime) {
      return null
    }
    return new Date(customDatetime).toISOString()
  }

  const expiry = new Date(now)
  if (choice === '1m') {
    expiry.setMinutes(expiry.getMinutes() + 1)
  } else if (choice === '5m') {
    expiry.setMinutes(expiry.getMinutes() + 5)
  } else if (choice === '10m') {
    expiry.setMinutes(expiry.getMinutes() + 10)
  } else if (choice === '30m') {
    expiry.setMinutes(expiry.getMinutes() + 30)
  } else if (choice === '1h') {
    expiry.setHours(expiry.getHours() + 1)
  } else {
    return null
  }

  return expiry.toISOString()
}

export function CreatePoll({ onNavigateToPoll, onNavigateToDashboard }: CreatePollProps) {
  const [question, setQuestion] = useState('')
  const [options, setOptions] = useState<string[]>(['', ''])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [multiSelect, setMultiSelect] = useState(false)
  const [expirationChoice, setExpirationChoice] = useState('10m')
  const [customDatetime, setCustomDatetime] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({ optionFields: ['', ''] })
  const [serverMessage, setServerMessage] = useState('')
  const [createdPoll, setCreatedPoll] = useState<CreatedPoll | null>(null)

  const canAddOption = options.length < MAX_OPTIONS
  const canRemoveOption = options.length > MIN_OPTIONS

  const cleanedOptions = useMemo(
    () => options.map((value) => value.trim()).filter((value) => value.length > 0),
    [options],
  )

  const validate = (): boolean => {
    const nextErrors: FieldErrors = { optionFields: options.map(() => '') }
    const trimmedQuestion = question.trim()

    if (!trimmedQuestion) {
      nextErrors.question = 'Question is required.'
    } else if (trimmedQuestion.length > MAX_QUESTION_LENGTH) {
      nextErrors.question = `Question cannot exceed ${MAX_QUESTION_LENGTH} characters.`
    }

    options.forEach((option, index) => {
      const trimmed = option.trim()
      if (!trimmed) {
        nextErrors.optionFields[index] = 'Option cannot be empty.'
      } else if (trimmed.length > MAX_OPTION_LENGTH) {
        nextErrors.optionFields[index] = `Option cannot exceed ${MAX_OPTION_LENGTH} characters.`
      }
    })

    if (cleanedOptions.length < MIN_OPTIONS || cleanedOptions.length > MAX_OPTIONS) {
      nextErrors.options = `Options must be between ${MIN_OPTIONS} and ${MAX_OPTIONS}.`
    } else if (new Set(cleanedOptions).size !== cleanedOptions.length) {
      nextErrors.options = 'Options must be unique.'
    }

    const expiresAtIso = computeExpiresAt(expirationChoice, customDatetime)
    if (!expiresAtIso) {
      nextErrors.expiration = 'Select a valid expiration time.'
    } else if (new Date(expiresAtIso).getTime() - Date.now() < MIN_EXPIRATION_MS) {
      nextErrors.expiration = 'Expiration must be at least 1 minute in the future.'
    }

    const hasErrors =
      !!nextErrors.question ||
      !!nextErrors.options ||
      !!nextErrors.expiration ||
      nextErrors.optionFields.some((item) => item.length > 0)

    setErrors(nextErrors)
    return !hasErrors
  }

  const addOption = () => {
    if (!canAddOption) {
      return
    }

    setOptions((prev) => [...prev, ''])
    setErrors((prev) => ({ ...prev, optionFields: [...prev.optionFields, ''] }))
  }

  const removeOption = (index: number) => {
    if (!canRemoveOption) {
      return
    }

    setOptions((prev) => prev.filter((_, optionIndex) => optionIndex !== index))
    setErrors((prev) => ({
      ...prev,
      optionFields: prev.optionFields.filter((_, optionIndex) => optionIndex !== index),
    }))
  }

  const onOptionChange = (index: number, value: string) => {
    setOptions((prev) => prev.map((item, optionIndex) => (optionIndex === index ? value : item)))
    setErrors((prev) => {
      const nextOptionErrors = [...prev.optionFields]
      nextOptionErrors[index] = ''
      return { ...prev, options: '', optionFields: nextOptionErrors }
    })
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setServerMessage('')
    setCreatedPoll(null)

    if (!validate()) {
      return
    }

    const expiresAtIso = computeExpiresAt(expirationChoice, customDatetime)
    if (!expiresAtIso) {
      setServerMessage('Unable to compute expiration time.')
      return
    }

    setIsSubmitting(true)
    try {
      const payload = await apiRequest<CreatedPoll>('/polls/create/', {
        method: 'POST',
        body: JSON.stringify({
          question: question.trim(),
          options: cleanedOptions,
          multi_select: multiSelect,
          expires_at: expiresAtIso,
        }),
      })

      saveOwnedPoll(payload)
      setCreatedPoll(payload)
      setServerMessage('Poll created successfully.')
      setQuestion('')
      setOptions(['', ''])
      setErrors({ optionFields: ['', ''] })
    } catch (error) {
      setServerMessage(error instanceof Error ? error.message : 'Failed to create poll.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const copyShareLink = async () => {
    if (!createdPoll) {
      return
    }

    await navigator.clipboard.writeText(buildShareLink(createdPoll.id))
    setServerMessage('Share link copied to clipboard.')
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>Create Poll</h2>
          <p className="sub">Build a named, realtime poll and keep management on this device only.</p>
        </div>
        <button type="button" className="secondary" onClick={onNavigateToDashboard}>
          My Polls
        </button>
      </div>

      <form onSubmit={onSubmit} className="stack" noValidate>
        <label>
          Poll Question
          <input
            value={question}
            onChange={(event) => {
              setQuestion(event.target.value)
              setErrors((prev) => ({ ...prev, question: '' }))
            }}
            maxLength={MAX_QUESTION_LENGTH}
            placeholder="Enter your decision question"
          />
        </label>
        {errors.question ? <p className="field-error">{errors.question}</p> : null}

        <div className="stack">
          <span>Poll Options ({options.length}/{MAX_OPTIONS})</span>
          {options.map((option, index) => (
            <div key={`option-${index}`} className="option-row">
              <input
                value={option}
                onChange={(event) => onOptionChange(index, event.target.value)}
                maxLength={MAX_OPTION_LENGTH}
                placeholder={`Option ${index + 1}`}
              />
              <button
                type="button"
                className="secondary"
                onClick={() => removeOption(index)}
                disabled={!canRemoveOption}
              >
                Remove
              </button>
              {errors.optionFields[index] ? (
                <p className="field-error full-row">{errors.optionFields[index]}</p>
              ) : null}
            </div>
          ))}
        </div>

        {errors.options ? <p className="field-error">{errors.options}</p> : null}

        <label className="toggle-row">
          <input
            type="checkbox"
            checked={multiSelect}
            onChange={(event) => setMultiSelect(event.target.checked)}
          />
          <span>Allow multiple selections</span>
        </label>

        <label>
          Poll Expiration
          <select
            value={expirationChoice}
            onChange={(event) => {
              setExpirationChoice(event.target.value)
              setErrors((prev) => ({ ...prev, expiration: '' }))
            }}
          >
            {expirationChoices.map((choice) => (
              <option key={choice.value} value={choice.value}>
                {choice.label}
              </option>
            ))}
          </select>
        </label>

        {expirationChoice === 'custom' ? (
          <label>
            Custom Expiration Date and Time
            <input
              type="datetime-local"
              value={customDatetime}
              onChange={(event) => setCustomDatetime(event.target.value)}
            />
          </label>
        ) : null}

        {errors.expiration ? <p className="field-error">{errors.expiration}</p> : null}

        <div className="row">
          <button type="button" onClick={addOption} disabled={!canAddOption}>
            Add Option
          </button>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create Poll'}
          </button>
        </div>
      </form>

      {serverMessage ? <p className="status">{serverMessage}</p> : null}

      {createdPoll ? (
        <div className="result-card">
          <h3>Share Poll</h3>
          <p>
            Link: <a href={buildShareLink(createdPoll.id)}>{buildShareLink(createdPoll.id)}</a>
          </p>
          <p>This device can now manage the poll from the dashboard.</p>
          <div className="row">
            <button type="button" onClick={copyShareLink}>
              Copy Link
            </button>
            <button type="button" onClick={() => onNavigateToPoll(createdPoll.id)}>
              Open Voting Page
            </button>
            <button type="button" className="secondary" onClick={onNavigateToDashboard}>
              Open My Polls
            </button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
