import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

const LABELS = {
  checking: 'Checking backend…',
  online: 'Backend connected',
  offline: 'Backend offline',
}

// Calls GET / on the backend once, to prove the frontend can reach FastAPI
export default function BackendStatus() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    apiFetch('/')
      .then(() => setStatus('online'))
      .catch(() => setStatus('offline'))
  }, [])

  return <span className={`backend-status ${status}`}>{LABELS[status]}</span>
}