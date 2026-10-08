import CodeCompassApp from './components/CodeCompassApp'
import DebugOnly from './components/DebugOnly'
import ServerStatus from './components/ServerStatus'

// Server Component: layout only. Everything interactive lives in Client Components.
export default function Home() {
  return (
    <main className="page">
      <header>
        <h1>CodeCompass</h1>
        <p className="headline">{"Ask plain-English questions about how your product's code works, and get answers backed by the exact lines of code."}</p>
        {/* Builder information: visible only with ?debug=1 */}
        <DebugOnly>
          <ServerStatus />
        </DebugOnly>
      </header>
      <CodeCompassApp />
    </main>
  )
}
