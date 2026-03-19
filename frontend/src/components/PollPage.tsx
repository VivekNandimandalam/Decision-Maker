import { useEffect, useMemo, useState } from 'react'

type PollOption = {
  id: string
  text: string
  votes: number
}

type Poll = {
  id: string
  question: string
  multi_select: boolean
  expires_at: string
  is_expired: boolean
  options: PollOption[]
  total_votes: number
  share_url: string
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ||
  'http://127.0.0.1:8000/api'

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://127.0.0.1:8000/ws'

function formatTimeRemaining(expiresAt: string): string {
  const nowMs = Date.now()
  const endMs = new Date(expiresAt).getTime()
  const diffMs = Math.max(0, endMs - nowMs)
  const totalSeconds = Math.floor(diffMs / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return `${hours}h ${minutes}m ${seconds}s`
}

type PollPageProps = {
  pollId: string
}

export function PollPage({ pollId }: PollPageProps) {
  const [poll, setPoll] = useState<Poll | null>(null)
  const [selectedOptionIds, setSelectedOptionIds] = useState<string[]>([])
  const [message, setMessage] = useState('Loading poll...')
  const [timeRemaining, setTimeRemaining] = useState('')
  const [wsState, setWsState] = useState('Disconnected')

  const canVote = useMemo(() => !!poll && !poll.is_expired, [poll])

  useEffect(() => {
    let mounted = true

    const loadPoll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/polls/${pollId}/`, {
          credentials: 'include',
        })
        const payload = await response.json()
        if (!response.ok) {
          throw new Error(payload.detail || 'Unable to fetch poll.')
        }
        if (!mounted) {
          return
        }
        setPoll(payload as Poll)
        setMessage('Poll loaded successfully.')
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

    const interval = setInterval(() => {
      setTimeRemaining(formatTimeRemaining(poll.expires_at))
    }, 1000)

    setTimeRemaining(formatTimeRemaining(poll.expires_at))
    return () => clearInterval(interval)
  }, [poll])

  useEffect(() => {
    const socket = new WebSocket(`${WS_BASE_URL}/polls/${pollId}/`)

    socket.onopen = () => {
      setWsState('Connected')
    }

    socket.onclose = () => {
      setWsState('Disconnected')
    }

    socket.onerror = () => {
      setWsState('Error')
    }

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as { type?: string; payload?: Poll }
        if (parsed.type === 'poll.updated' && parsed.payload) {
          setPoll(parsed.payload)
          setMessage('Live update received.')
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

    try {
      const response = await fetch(`${API_BASE_URL}/polls/${poll.id}/vote/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ option_ids: selectedOptionIds }),
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(payload.detail || 'Vote submission failed.')
      }
      setPoll(payload as Poll)
      setMessage('Vote submitted successfully.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Vote submission failed.')
    }
  }

  if (!poll) {
    return (
      <section className="panel">
        <h2>Poll</h2>
        <p>{message}</p>
      </section>
    )
  }

  return (
    <section className="panel">
      <h2>{poll.question}</h2>
      <p>Realtime status: {wsState}</p>
      <p>Selection mode: {poll.multi_select ? 'Multiple options allowed' : 'Single option only'}</p>
      <p>Time remaining: {timeRemaining}</p>
      <p>Total votes: {poll.total_votes}</p>

      <div className="stack">
        {poll.options.map((option) => (
          <label key={option.id} className="choice">
            <input
              type={poll.multi_select ? 'checkbox' : 'radio'}
              name="vote-option"
              checked={selectedOptionIds.includes(option.id)}
              onChange={() => toggleOption(option.id)}
              disabled={!canVote}
            />
            <span>{option.text}</span>
            <strong>{option.votes}</strong>
          </label>
        ))}
      </div>

      <div className="row">
        <button type="button" onClick={submitVote} disabled={!canVote}>
          {poll.is_expired ? 'Poll expired' : 'Submit Vote'}
        </button>
      </div>

      <p className="status">{message}</p>
    </section>
  )
}
