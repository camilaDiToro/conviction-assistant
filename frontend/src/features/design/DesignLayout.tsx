import { Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Sidebar } from '@/components/Sidebar'

export default function DesignLayout() {
  const [expanded, setExpanded] = useState(true)
  const location = useLocation()

  // Auto-collapse on narrow screens; auto-scroll-to-top on navigation.
  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth < 960) setExpanded(false)
    }
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [location.pathname])

  return (
    <div className="min-h-screen flex bg-bg">
      <Sidebar expanded={expanded} onToggle={() => setExpanded(e => !e)} />
      <main className="flex-1 min-w-0">
        <div className="max-w-page mx-auto px-6 md:px-12 py-10 md:py-16">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
