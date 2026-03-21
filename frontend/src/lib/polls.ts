export type PollOption = {
  id: string
  text: string
  votes: number
}

export type RecentVoter = {
  voter_name: string
  option_ids: string[]
  created_at: string
}

export type Poll = {
  id: string
  question: string
  multi_select: boolean
  expires_at: string
  is_expired: boolean
  options: PollOption[]
  total_votes: number
  vote_record_count: number
  recent_voters: RecentVoter[]
  share_url: string
  created_at: string
  updated_at: string
}

export type CreatedPoll = Poll & {
  creator_token: string
  manage_url: string
}

export type StoredPollOwnership = {
  id: string
  question: string
  createdAt: string
  creatorToken: string
}

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000/api'

export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://127.0.0.1:8000/ws'

const STORAGE_KEY = 'decision-maker-owned-polls'

export function loadOwnedPolls(): StoredPollOwnership[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return []
    }

    const parsed = JSON.parse(raw) as StoredPollOwnership[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveOwnedPoll(createdPoll: CreatedPoll) {
  const existing = loadOwnedPolls().filter((poll) => poll.id !== createdPoll.id)
  const next = [
    {
      id: createdPoll.id,
      question: createdPoll.question,
      createdAt: createdPoll.created_at,
      creatorToken: createdPoll.creator_token,
    },
    ...existing,
  ]
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
}

export function removeOwnedPoll(pollId: string) {
  const next = loadOwnedPolls().filter((poll) => poll.id !== pollId)
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
}

export function updateOwnedPollQuestion(pollId: string, question: string) {
  const next = loadOwnedPolls().map((poll) =>
    poll.id === pollId ? { ...poll, question } : poll,
  )
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error((payload as { detail?: string }).detail || 'Request failed.')
  }

  return payload as T
}

export function buildShareLink(pollId: string) {
  return `${window.location.origin}/poll/${pollId}/`
}

export function formatTimeRemaining(expiresAt: string): string {
  const nowMs = Date.now()
  const endMs = new Date(expiresAt).getTime()
  const diffMs = Math.max(0, endMs - nowMs)
  const totalSeconds = Math.floor(diffMs / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return `${hours}h ${minutes}m ${seconds}s`
}
