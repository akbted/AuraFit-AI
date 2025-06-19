import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-background text-text flex flex-col items-center justify-center">
      <h1 className="text-4xl font-bold text-primary mb-4">AuraFit AI</h1>
      <p className="text-lg mb-8">Your AI-powered fitness companion</p>
      <button className="bg-primary hover:bg-primaryHover text-white font-bold py-2 px-4 rounded">
        Get Started
      </button>
    </div>
  )
}

export default App
