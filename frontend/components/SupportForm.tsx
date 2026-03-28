'use client'

import { useState } from 'react'

interface FormData {
  subject: string
  description: string
  category: string
  priority: string
}

export default function SupportForm() {
  const [formData, setFormData] = useState<FormData>({
    subject: '',
    description: '',
    category: 'technical',
    priority: 'p3',
  })

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    console.log('Submitting ticket:', formData)
    setIsSubmitting(false)
    setSubmitted(true)
    
    // Reset after 3 seconds
    setTimeout(() => {
      setSubmitted(false)
      setFormData({ subject: '', description: '', category: 'technical', priority: 'p3' })
    }, 3000)
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="rounded-lg bg-white shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Create Support Ticket</h2>
          <p className="mt-1 text-sm text-gray-500">
            Submit a ticket and our AI Agent will classify and route it automatically.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {submitted ? (
            <div className="rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-800">Ticket submitted successfully!</h3>
                  <p className="mt-1 text-sm text-green-700">
                    Our AI Agent has classified your ticket and routed it to the appropriate team.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Subject */}
              <div>
                <label htmlFor="subject" className="block text-sm font-medium text-gray-700">
                  Subject
                </label>
                <input
                  type="text"
                  id="subject"
                  required
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2"
                  placeholder="Brief summary of the issue"
                />
              </div>

              {/* Category */}
              <div>
                <label htmlFor="category" className="block text-sm font-medium text-gray-700">
                  Category
                </label>
                <select
                  id="category"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2"
                >
                  <option value="technical">Technical Issue</option>
                  <option value="billing">Billing</option>
                  <option value="feature_request">Feature Request</option>
                  <option value="account">Account Management</option>
                  <option value="integration">Integration</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {/* Description */}
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <textarea
                  id="description"
                  rows={6}
                  required
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm border p-2"
                  placeholder="Describe the issue in detail. Include steps to reproduce, expected behavior, and actual behavior."
                />
                <p className="mt-2 text-sm text-gray-500">
                  Please include any relevant details such as browser, OS, or steps to reproduce.
                </p>
              </div>

              {/* Priority (for reference - AI will auto-classify) */}
              <div className="rounded-md bg-blue-50 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3 flex-1">
                    <h3 className="text-sm font-medium text-blue-800">AI Auto-Classification</h3>
                    <p className="mt-1 text-sm text-blue-700">
                      Our AI Agent will automatically classify the priority based on the issue description and escalation rules.
                    </p>
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={`
                    inline-flex justify-center py-2 px-4 border border-transparent shadow-sm 
                    text-sm font-medium rounded-md text-white 
                    ${isSubmitting ? 'bg-blue-400' : 'bg-blue-600 hover:bg-blue-700'}
                    focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                    disabled:cursor-not-allowed
                  `}
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Ticket'}
                </button>
              </div>
            </>
          )}
        </form>
      </div>

      {/* Priority Guide */}
      <div className="mt-6 rounded-lg bg-white shadow p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Priority Classification Guide</h3>
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">P1</span>
            <span className="text-sm text-gray-600">Critical - Platform unavailable, data loss, security breach</span>
          </div>
          <div className="flex items-start gap-3">
            <span className="inline-flex items-center rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium text-orange-800">P2</span>
            <span className="text-sm text-gray-600">High - Major feature not working, performance issues</span>
          </div>
          <div className="flex items-start gap-3">
            <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">P3</span>
            <span className="text-sm text-gray-600">Medium - Non-critical issues with workaround available</span>
          </div>
          <div className="flex items-start gap-3">
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-800">P4</span>
            <span className="text-sm text-gray-600">Low - Questions, feature requests, cosmetic issues</span>
          </div>
        </div>
      </div>
    </div>
  )
}
