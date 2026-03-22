import { FormEvent, useEffect, useMemo, useState } from 'react'

import {
  API_BASE_URL,
  apiRequest,
  buildShareLink,
  loadOwnedPolls,
  Poll,
  removeOwnedPoll,
  StoredPollOwnership,
  updateOwnedPollQuestion,
} from '../lib/polls'

type MyPollsProps = {
  onNavigateHome: () => void
  onNavigateToPoll: (pollId: string) => void
  selectedPollId?: string | null
}

type EditablePoll = {
  question: string
  options: string[]
  multi_select: boolean
  expires_at: string
  creator_token: string
}

const MIN_EXPIRATION_MS = 60_000

function toLocalDatetimeInput(value: string) {
  const date = new Date(value)
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

export function MyPolls({ onNavigateHome, onNavigateToPoll, selectedPollId }: MyPollsProps) {
  const [ownedPolls, setOwnedPolls] = useState<StoredPollOwnership[]>([])
  const [pollsById, setPollsById] = useState<Record<string, Poll>>({})
  const [editingPollId, setEditingPollId] = useState<string | null>(selectedPollId || null)
  const [drafts, setDrafts] = useState<Record<string, EditablePoll>>({})
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setOwnedPolls(loadOwnedPolls())
  }, [])

  useEffect(() => {
    if (selectedPollId) {
      setEditingPollId(selectedPollId)
    }
  }, [selectedPollId])

  useEffect(() => {
    let cancelled = false

    const loadPolls = async () => {
      if (ownedPolls.length === 0) {
        setLoading(false)
        return
      }

      try {
        const results = await Promise.all(
          ownedPolls.map(async (item) => {
            try {
              const poll = await apiRequest<Poll>(`/polls/${item.id}/results/`)
              return { id: item.id, poll, missing: false } as const
            } catch (error) {
              const isMissing = error instanceof Error && error.message === 'Poll not found.'
              return { id: item.id, poll: null, missing: isMissing } as const
            }
          }),
        )

        if (cancelled) {
          return
        }

        const next: Record<string, Poll> = {}
        const missingPollIds: string[] = []
        results.forEach((entry) => {
          if (entry.poll) {
            next[entry.id] = entry.poll
          }
          if (entry.missing) {
            missingPollIds.push(entry.id)
          }
        })
        setPollsById(next)

        if (missingPollIds.length > 0) {
          missingPollIds.forEach((pollId) => removeOwnedPoll(pollId))
          setOwnedPolls(loadOwnedPolls())
          setMessage('Removed stale polls that no longer exist.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadPolls()
    return () => {
      cancelled = true
    }
  }, [ownedPolls])

  const visiblePolls = useMemo(
    () =>
      ownedPolls.map((ownedPoll) => ({
        ownedPoll,
        poll: pollsById[ownedPoll.id] || null,
      })),
    [ownedPolls, pollsById],
  )

  const beginEdit = (ownedPoll: StoredPollOwnership, poll: Poll | null) => {
    if (!poll) {
      return
    }

    setEditingPollId(ownedPoll.id)
    setDrafts((prev) => ({
      ...prev,
      [ownedPoll.id]: {
        question: poll.question,
        options: poll.options.map((option) => option.text),
        multi_select: poll.multi_select,
        expires_at: toLocalDatetimeInput(poll.expires_at),
        creator_token: ownedPoll.creatorToken,
      },
    }))
  }

  const updateDraft = (pollId: string, patch: Partial<EditablePoll>) => {
    setDrafts((prev) => ({
      ...prev,
      [pollId]: {
        ...prev[pollId],
        ...patch,
      },
    }))
  }

  const updateDraftOption = (pollId: string, optionIndex: number, value: string) => {
    const draft = drafts[pollId]
    if (!draft) {
      return
    }

    const nextOptions = draft.options.map((option, index) => (index === optionIndex ? value : option))
    updateDraft(pollId, { options: nextOptions })
  }

  const addDraftOption = (pollId: string) => {
    const draft = drafts[pollId]
    if (!draft || draft.options.length >= 20) {
      return
    }

    updateDraft(pollId, { options: [...draft.options, ''] })
  }

  const removeDraftOption = (pollId: string, optionIndex: number) => {
    const draft = drafts[pollId]
    if (!draft || draft.options.length <= 2) {
      return
    }

    updateDraft(pollId, { options: draft.options.filter((_, index) => index !== optionIndex) })
  }

  const saveEdit = async (event: FormEvent, pollId: string) => {
    event.preventDefault()
    const draft = drafts[pollId]
    if (!draft) {
      return
    }

    const expiresAt = new Date(draft.expires_at).toISOString()
    if (new Date(expiresAt).getTime() - Date.now() < MIN_EXPIRATION_MS) {
      setMessage('Edited polls must expire at least 1 minute in the future.')
      return
    }

    try {
      const payload = await apiRequest<Poll>(`/polls/${pollId}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          question: draft.question.trim(),
          options: draft.options.map((option) => option.trim()),
          multi_select: draft.multi_select,
          expires_at: expiresAt,
          creator_token: draft.creator_token,
        }),
      })

      setPollsById((prev) => ({ ...prev, [pollId]: payload }))
      updateOwnedPollQuestion(pollId, payload.question)
      setOwnedPolls(loadOwnedPolls())
      setEditingPollId(null)
      setMessage('Poll updated successfully.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Unable to update poll.')
    }
  }

  const deletePoll = async (ownedPoll: StoredPollOwnership) => {
    try {
      await fetch(
        `${API_BASE_URL}/polls/${ownedPoll.id}/?token=${encodeURIComponent(ownedPoll.creatorToken)}`,
        {
          method: 'DELETE',
          credentials: 'include',
        },
      ).then(async (response) => {
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}))
          throw new Error((payload as { detail?: string }).detail || 'Unable to delete poll.')
        }
      })

      removeOwnedPoll(ownedPoll.id)
      setOwnedPolls(loadOwnedPolls())
      setPollsById((prev) => {
        const next = { ...prev }
        delete next[ownedPoll.id]
        return next
      })
      setEditingPollId((prev) => (prev === ownedPoll.id ? null : prev))
      setMessage('Poll deleted successfully.')
    } catch (error) {
      if (error instanceof Error && error.message === 'Poll not found.') {
        removeOwnedPoll(ownedPoll.id)
        setOwnedPolls(loadOwnedPolls())
        setPollsById((prev) => {
          const next = { ...prev }
          delete next[ownedPoll.id]
          return next
        })
        setEditingPollId((prev) => (prev === ownedPoll.id ? null : prev))
        setMessage('Poll was already gone, so it was removed from this device list.')
        return
      }

      setMessage(error instanceof Error ? error.message : 'Unable to delete poll.')
    }
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>My Polls</h2>
          <p className="sub">Only polls created on this device appear here.</p>
        </div>
        <button type="button" onClick={onNavigateHome}>
          Create Poll
        </button>
      </div>

      {message ? <p className="status">{message}</p> : null}

      {loading ? <p>Loading your polls...</p> : null}

      {!loading && visiblePolls.length === 0 ? (
        <p>No polls have been created on this device yet.</p>
      ) : null}

      <div className="stack">
        {visiblePolls.map(({ ownedPoll, poll }) => {
          const draft = drafts[ownedPoll.id]
          const isEditing = editingPollId === ownedPoll.id && !!draft

          return (
            <article key={ownedPoll.id} className="result-card">
              <div className="section-heading">
                <div>
                  <h3>{poll?.question || ownedPoll.question}</h3>
                  <p>
                    {poll
                      ? `${poll.total_votes} votes • ${poll.is_expired ? 'Expired' : 'Active'}`
                      : 'Poll details unavailable'}
                  </p>
                </div>
                <div className="row">
                  <button type="button" className="secondary" onClick={() => onNavigateToPoll(ownedPoll.id)}>
                    Open
                  </button>
                  <button type="button" className="secondary" onClick={() => beginEdit(ownedPoll, poll)}>
                    Edit
                  </button>
                  <button type="button" className="danger" onClick={() => deletePoll(ownedPoll)}>
                    Delete
                  </button>
                </div>
              </div>

              <p>
                Link: <a href={buildShareLink(ownedPoll.id)}>{buildShareLink(ownedPoll.id)}</a>
              </p>

              {isEditing ? (
                <form className="stack" onSubmit={(event) => saveEdit(event, ownedPoll.id)}>
                  <label>
                    Question
                    <input
                      value={draft.question}
                      onChange={(event) => updateDraft(ownedPoll.id, { question: event.target.value })}
                    />
                  </label>

                  <label className="toggle-row">
                    <input
                      type="checkbox"
                      checked={draft.multi_select}
                      onChange={(event) =>
                        updateDraft(ownedPoll.id, { multi_select: event.target.checked })
                      }
                    />
                    <span>Allow multiple selections</span>
                  </label>

                  <label>
                    Expires At
                    <input
                      type="datetime-local"
                      value={draft.expires_at}
                      onChange={(event) => updateDraft(ownedPoll.id, { expires_at: event.target.value })}
                    />
                  </label>

                  <div className="stack">
                    {draft.options.map((option, index) => (
                      <div key={`${ownedPoll.id}-option-${index}`} className="option-row">
                        <input
                          value={option}
                          onChange={(event) => updateDraftOption(ownedPoll.id, index, event.target.value)}
                        />
                        <button
                          type="button"
                          className="secondary"
                          disabled={draft.options.length <= 2}
                          onClick={() => removeDraftOption(ownedPoll.id, index)}
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="row">
                    <button type="button" className="secondary" onClick={() => addDraftOption(ownedPoll.id)}>
                      Add Option
                    </button>
                    <button type="submit">Save Changes</button>
                    <button type="button" className="secondary" onClick={() => setEditingPollId(null)}>
                      Cancel
                    </button>
                  </div>
                </form>
              ) : null}
            </article>
          )
        })}
      </div>
    </section>
  )
}
