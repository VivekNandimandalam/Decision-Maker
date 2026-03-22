import './App.css'
import { useEffect, useMemo, useState } from 'react'

import { CreatePoll } from './components/CreatePoll'
import { MyPolls } from './components/MyPolls'
import { PollPage } from './components/PollPage'

function getRouteSource() {
  const hash = window.location.hash.replace(/^#/, '')
  return hash || window.location.pathname
}

function App() {
  const [path, setPath] = useState(getRouteSource())

  useEffect(() => {
    const syncRoute = () => setPath(getRouteSource())
    const onPopState = () => syncRoute()
    const onHashChange = () => syncRoute()
    window.addEventListener('popstate', onPopState)
    window.addEventListener('hashchange', onHashChange)
    return () => {
      window.removeEventListener('popstate', onPopState)
      window.removeEventListener('hashchange', onHashChange)
    }
  }, [])

  const route = useMemo(() => {
    const pollMatch = path.match(/^\/poll\/([0-9a-f-]+)\/?$/i)
    if (pollMatch) {
      return { name: 'poll', pollId: pollMatch[1] }
    }

    const manageMatch = path.match(/^\/manage\/([0-9a-f-]+)\/?$/i)
    if (manageMatch) {
      return { name: 'manage', pollId: manageMatch[1] }
    }

    if (path === '/my-polls/' || path === '/my-polls') {
      return { name: 'my-polls', pollId: null }
    }

    return { name: 'home', pollId: null }
  }, [path])

  const navigate = (nextPath: string) => {
    const normalizedPath = nextPath.startsWith('/') ? nextPath : `/${nextPath}`
    const nextHash = `#${normalizedPath}`
    if (window.location.hash !== nextHash) {
      window.location.hash = normalizedPath
    } else {
      setPath(normalizedPath)
    }
  }

  return (
    <main className="page">
      <section className="panel panel-strong">
        <h1>Decision Maker</h1>
        <p className="sub">Create timed polls, share links, manage them from one device, and watch votes update live.</p>
        <div className="row">
          <button type="button" onClick={() => navigate('/')}>
            Create Poll
          </button>
          <button type="button" className="secondary" onClick={() => navigate('/my-polls/')}>
            My Polls
          </button>
        </div>
      </section>

      {route.name === 'poll' && route.pollId ? (
        <PollPage pollId={route.pollId} onNavigateToDashboard={() => navigate('/my-polls/')} />
      ) : null}

      {route.name === 'my-polls' ? (
        <MyPolls
          onNavigateHome={() => navigate('/')}
          onNavigateToPoll={(pollId) => navigate(`/poll/${pollId}/`)}
        />
      ) : null}

      {route.name === 'manage' && route.pollId ? (
        <MyPolls
          onNavigateHome={() => navigate('/')}
          onNavigateToPoll={(pollId) => navigate(`/poll/${pollId}/`)}
          selectedPollId={route.pollId}
        />
      ) : null}

      {route.name === 'home' ? (
        <CreatePoll
          onNavigateToPoll={(pollId) => navigate(`/poll/${pollId}/`)}
          onNavigateToDashboard={() => navigate('/my-polls/')}
        />
      ) : null}
    </main>
  )
}

export default App
