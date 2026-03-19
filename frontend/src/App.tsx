import './App.css'
import { CreatePoll } from './components/CreatePoll.tsx'
import { PollPage } from './components/PollPage.tsx'
import { useEffect, useMemo, useState } from 'react'

function App() {
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const pollIdFromPath = useMemo(() => {
    const match = path.match(/^\/poll\/([0-9a-f-]+)\/?$/i)
    return match ? match[1] : null
  }, [path])

  const navigateToPoll = (pollId: string) => {
    const nextPath = `/poll/${pollId}/`
    window.history.pushState({}, '', nextPath)
    setPath(nextPath)
  }

  const navigateHome = () => {
    window.history.pushState({}, '', '/')
    setPath('/')
  }

  return (
    <main className="page">
      <section className="panel panel-strong">
        <h1>Decision Maker</h1>
        <p className="sub">Create timed polls, share links, and watch live vote updates.</p>
        <div className="row">
          <button type="button" onClick={navigateHome}>Create Poll</button>
        </div>
      </section>
      {pollIdFromPath ? <PollPage pollId={pollIdFromPath} /> : <CreatePoll onNavigateToPoll={navigateToPoll} />}
    </main>
  )
}

export default App
