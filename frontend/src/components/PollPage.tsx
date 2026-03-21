import { useEffect, useMemo, useState } from 'react'

import { apiRequest, formatTimeRemaining, Poll, WS_BASE_URL } from '../lib/polls'

type PollPageProps = {
  pollId: string
  onNavigateToDashboard: () => void
}

export function PollPage({ pollId, onNavigateToDashboard }: PollPageProps) {
  const [poll, setPoll] = useState<Poll | null>(null)
  const [selectedOptionIds, setSelectedOptionIds] = useState<string[]>([])
  const [message, setMessage] = useState('Loading poll...')
  const [timeRemaining, setTimeRemaining] = useState('')
  const [wsState, setWsState] = useState('Disconnected')
  const [voterName, setVoterName] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const canVote = useMemo(
    () => !!poll && !poll.is_expired && voterName.trim().length > 0,
    [poll, voterName],
  )

  useEffect(() => {
    let mounted = true

    const loadPoll = async () => {
      try {
        const payload = await apiRequest<Poll>(`/polls/${pollId}/`)
        if (!mounted) {
          return
        }
        setPoll(payload)
        setMessage(payload.is_expired ? 'This poll has expired.' : 'Poll loaded successfully.')
      } catch (error) {
        if (!mounted) {
          return
        }
        setMessage(error instanceof Error ? error.message : 'Unable to fetch poll.')
      }
    }

    loadPoll()
    return () => {
      mounted = false
    }
  }, [pollId])

  useEffect(() => {
    if (!poll) {
      return
    }

    const refreshTime = () => setTimeRemaining(formatTimeRemaining(poll.expires_at))
    refreshTime()

    const interval = window.setInterval(() => {
      refreshTime()
      if (new Date(poll.expires_at).getTime() <= Date.now()) {
        setPoll((prev) => (prev ? { ...prev, is_expired: true } : prev))
      }
    }, 1000)

    return () => window.clearInterval(interval)
  }, [poll])

  useEffect(() => {
    const socket = new WebSocket(`${WS_BASE_URL}/polls/${pollId}/`)

    socket.onopen = () => setWsState('Connected')
    socket.onclose = () => setWsState('Disconnected')
    socket.onerror = () => setWsState('Error')
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as { type?: string; payload?: Poll | { id: string } }
        if ((parsed.type === 'poll.updated' || parsed.type === 'poll.expired') && parsed.payload) {
          setPoll(parsed.payload as Poll)
          setMessage(parsed.type === 'poll.expired' ? 'Poll expired.' : 'Live update received.')
        }
        if (parsed.type === 'poll.deleted') {
          setMessage('This poll has been deleted by its creator.')
          setPoll(null)
        }
      } catch {
        setMessage('Received malformed realtime message.')
      }
    }

    return () => {
      socket.close()
    }
  }, [pollId])

  const toggleOption = (optionId: string) => {
    if (!poll) {
      return
    }

    if (poll.multi_select) {
      setSelectedOptionIds((prev) =>
        prev.includes(optionId) ? prev.filter((id) => id !== optionId) : [...prev, optionId],
      )
      return
    }

    setSelectedOptionIds([optionId])
  }

  const submitVote = async () => {
    if (!poll) {
      return
    }
    if (selectedOptionIds.length === 0) {
      setMessage('Select at least one option to vote.')
      return
    }
    if (!voterName.trim()) {
      setMessage('Enter your name before voting.')
      return
    }

    setIsSubmitting(true)
    try {
      const payload = await apiRequest<Poll>(`/polls/${poll.id}/vote/`, {
        method: 'POST',
        body: JSON.stringify({
          voter_name: voterName.trim(),
          option_ids: selectedOptionIds,
        }),
      })
      setPoll(payload)
      setMessage('Vote submitted successfully.')
      setSelectedOptionIds([])
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Vote submission failed.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!poll) {
    return (
      <section className="panel">
        <div className="section-heading">
          <h2>Poll</h2>
          <button type="button" className="secondary" onClick={onNavigateToDashboard}>
            My Polls
          </button>
        </div>
        <p>{message}</p>
      </section>
    )
  }

  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>{poll.question}</h2>
          <p className="sub">Realtime status: {wsState}</p>
        </div>
        <button type="button" className="secondary" onClick={onNavigateToDashboard}>
          My Polls
        </button>
      </div>

      <div className="meta-grid">
        <p>Selection mode: {poll.multi_select ? 'Multiple options allowed' : 'Single option only'}</p>
        <p>Time remaining: {timeRemaining}</p>
        <p>Total votes: {poll.total_votes}</p>
        <p>Voters: {poll.vote_record_count}</p>
      </div>

      <label>
        Your Name
        <input
          value={voterName}
          onChange={(event) => setVoterName(event.target.value)}
          placeholder="Enter your name before voting"
          disabled={poll.is_expired}
        />
      </label>

      <div className="stack">
        {poll.options.map((option) => (
          <label key={option.id} className="choice">
            <input
              type={poll.multi_select ? 'checkbox' : 'radio'}
              name="vote-option"
              checked={selectedOptionIds.includes(option.id)}
              onChange={() => toggleOption(option.id)}
              disabled={poll.is_expired}
            />
            <span>{option.text}</span>
            <strong>{option.votes}</strong>
          </label>
        ))}
      </div>

      <div className="row">
        <button type="button" onClick={submitVote} disabled={!canVote || isSubmitting}>
          {poll.is_expired ? 'Poll expired' : isSubmitting ? 'Submitting...' : 'Submit Vote'}
        </button>
      </div>

      <div className="result-card">
        <h3>Recent voters</h3>
        {poll.recent_voters.length === 0 ? (
          <p>No votes yet.</p>
        ) : (
          <div className="stack">
            {poll.recent_voters
              .slice()
              .reverse()
              .map((entry) => (
                <p key={`${entry.voter_name}-${entry.created_at}`}>
                  {entry.voter_name} voted at {new Date(entry.created_at).toLocaleString()}
                </p>
              ))}
          </div>
        )}
      </div>

      <p className="status">{message}</p>
    </section>
  )
}
