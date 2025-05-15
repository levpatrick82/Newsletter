import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import NewsletterBot from './components/NewsletterBot'
import NewsletterForm from './components/NewsletterForm'
import { subscribeToNewsletter } from './utils/api'

export default function App() {
  const [isLoading, setIsLoading] = useState(false)

  const handleSubscribe = async (email: string, name: string) => {
    setIsLoading(true)
    try {
      await subscribeToNewsletter(email, name)
    } catch (error) {
      console.error('Subscription error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Newsletter Management System
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Streamline your newsletter subscriptions with our automated system. 
            Subscribe individually or bulk process multiple websites.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Individual Subscription */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">
              Individual Subscription
            </h2>
            <NewsletterForm 
              onSubmit={handleSubscribe}
              isLoading={isLoading}
            />
          </div>

          {/* Bulk Processing */}
          <div>
            <NewsletterBot />
          </div>
        </div>

        {/* Features Section */}
        <div className="grid md:grid-cols-3 gap-6 mt-12">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Automated Processing
            </h3>
            <p className="text-gray-600">
              Bulk process newsletter subscriptions across multiple websites automatically.
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Progress Tracking
            </h3>
            <p className="text-gray-600">
              Monitor subscription progress in real-time with our intuitive interface.
            </p>
          </div>
          
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Error Handling
            </h3>
            <p className="text-gray-600">
              Robust error handling and reporting for failed subscriptions.
            </p>
          </div>
        </div>
      </div>
      
      <Toaster position="top-right" />
    </div>
  )
}