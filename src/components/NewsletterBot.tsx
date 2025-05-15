import { useState } from 'react'
import { toast } from 'react-hot-toast'
import clsx from 'clsx'

export default function NewsletterBot() {
  const [isRunning, setIsRunning] = useState(false)
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && file.name.endsWith('.csv')) {
      setCsvFile(file)
    } else {
      toast.error('Please select a valid CSV file')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!csvFile) {
      toast.error('Please select a CSV file')
      return
    }

    setIsRunning(true)
    const formData = new FormData()
    formData.append('csv_file', csvFile)

    try {
      const response = await fetch('/api/start-bot', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Failed to start bot')
      }

      // Start progress polling
      const pollInterval = setInterval(async () => {
        const progressResponse = await fetch('/api/progress')
        const data = await progressResponse.json()
        setProgress(data.progress)

        if (data.progress === 100 || data.status === 'completed') {
          clearInterval(pollInterval)
          setIsRunning(false)
          toast.success('Newsletter registration completed!')
        }
      }, 2000)

    } catch (error) {
      toast.error('Failed to start the bot')
      setIsRunning(false)
    }
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg relative">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">Bulk Processing</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Upload CSV with Website URLs
          </label>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-3 file:px-4
              file:rounded-md file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100
              transition-all duration-200"
            disabled={isRunning}
          />
        </div>

        {progress > 0 && (
          <div className="mt-6">
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-in-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-600 mt-3 text-center font-medium">
              Progress: {progress}%
            </p>
          </div>
        )}

        <button
          type="submit"
          disabled={!csvFile || isRunning}
          className={clsx(
            "w-full py-3 px-4 rounded-md text-white font-medium shadow-md",
            "transition duration-200 ease-in-out",
            isRunning || !csvFile
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-blue-600 hover:bg-blue-700"
          )}
        >
          {isRunning ? 'Bot Running...' : 'Start Registration'}
        </button>
        
        {isRunning && (
          <p className="text-sm text-gray-500 mt-4 text-center">
            Processing your websites. This may take a few minutes...
          </p>
        )}
      </form>
    </div>
  )
}