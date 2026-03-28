'use client'

import { useState } from 'react'

interface TicketStats {
  total: number
  p1: number
  p2: number
  p3: number
  p4: number
}

interface CustomerStats {
  total: number
  atRisk: number
  enterprise: number
}

export default function Dashboard() {
  const [stats] = useState<TicketStats>({
    total: 247,
    p1: 2,
    p2: 15,
    p3: 89,
    p4: 141,
  })

  const [customerStats] = useState<CustomerStats>({
    total: 12543,
    atRisk: 47,
    enterprise: 47,
  })

  const recentTickets = [
    { id: 'TKT-2026-0342', subject: 'Gantt chart not loading', priority: 'P2', customer: 'TechCorp Inc', status: 'in_progress', age: '23 min' },
    { id: 'TKT-2026-0341', subject: 'How to set up automation rules?', priority: 'P4', customer: 'StartupXYZ', status: 'open', age: '1 hour' },
    { id: 'TKT-2026-0340', subject: 'Integration with Salesforce failing', priority: 'P2', customer: 'Enterprise Co', status: 'open', age: '2 hours' },
    { id: 'TKT-2026-0339', subject: 'Mobile app crashes on iOS', priority: 'P2', customer: 'Design Agency', status: 'waiting_customer', age: '4 hours' },
    { id: 'TKT-2026-0338', subject: 'Feature request: Dark mode', priority: 'P4', customer: 'Small Biz LLC', status: 'open', age: '6 hours' },
  ]

  const aiInsights = [
    { type: 'alert', message: '3 tickets approaching SLA breach', severity: 'high' },
    { type: 'info', message: 'Customer health score improved for 12 accounts', severity: 'low' },
    { type: 'success', message: 'AI auto-resolved 47 tickets this week', severity: 'low' },
  ]

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Tickets */}
        <div className="overflow-hidden rounded-lg bg-white shadow">
          <div className="p-6">
            <dt className="truncate text-sm font-medium text-gray-500">Open Tickets</dt>
            <dd className="mt-2 text-3xl font-semibold text-gray-900">{stats.total}</dd>
          </div>
          <div className="bg-gray-50 px-6 py-3">
            <div className="flex text-sm">
              <span className="text-red-600 font-medium">P1: {stats.p1}</span>
              <span className="ml-4 text-orange-600 font-medium">P2: {stats.p2}</span>
              <span className="ml-4 text-blue-600 font-medium">P3: {stats.p3}</span>
              <span className="ml-4 text-gray-600 font-medium">P4: {stats.p4}</span>
            </div>
          </div>
        </div>

        {/* Total Customers */}
        <div className="overflow-hidden rounded-lg bg-white shadow">
          <div className="p-6">
            <dt className="truncate text-sm font-medium text-gray-500">Total Customers</dt>
            <dd className="mt-2 text-3xl font-semibold text-gray-900">{customerStats.total.toLocaleString()}</dd>
          </div>
          <div className="bg-gray-50 px-6 py-3">
            <div className="flex text-sm">
              <span className="text-green-600 font-medium">Enterprise: {customerStats.enterprise}</span>
              <span className="ml-4 text-red-600 font-medium">At Risk: {customerStats.atRisk}</span>
            </div>
          </div>
        </div>

        {/* AI Agent Stats */}
        <div className="overflow-hidden rounded-lg bg-white shadow">
          <div className="p-6">
            <dt className="truncate text-sm font-medium text-gray-500">AI Auto-Resolved</dt>
            <dd className="mt-2 text-3xl font-semibold text-gray-900">47</dd>
          </div>
          <div className="bg-gray-50 px-6 py-3">
            <div className="text-sm text-gray-600">
              This week
            </div>
          </div>
        </div>

        {/* Avg Response Time */}
        <div className="overflow-hidden rounded-lg bg-white shadow">
          <div className="p-6">
            <dt className="truncate text-sm font-medium text-gray-500">Avg Response Time</dt>
            <dd className="mt-2 text-3xl font-semibold text-gray-900">1.2h</dd>
          </div>
          <div className="bg-gray-50 px-6 py-3">
            <div className="text-sm text-green-600">
              ↓ 15% from last week
            </div>
          </div>
        </div>
      </div>

      {/* AI Insights */}
      <div className="rounded-lg bg-white shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">AI Agent Insights</h2>
        </div>
        <div className="p-6 space-y-3">
          {aiInsights.map((insight, index) => (
            <div
              key={index}
              className={`flex items-center gap-3 rounded-md p-3 ${
                insight.severity === 'high' ? 'bg-red-50' : 'bg-blue-50'
              }`}
            >
              <span className={`text-lg ${
                insight.severity === 'high' ? '🚨' : insight.type === 'success' ? '✅' : 'ℹ️'
              }`}></span>
              <span className="text-sm text-gray-700">{insight.message}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Tickets */}
      <div className="rounded-lg bg-white shadow">
        <div className="px-6 py-4 border-b flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">Recent Tickets</h2>
          <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            View All
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticket</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Subject</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Priority</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Age</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {recentTickets.map((ticket) => (
                <tr key={ticket.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                    {ticket.id}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{ticket.subject}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{ticket.customer}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      ticket.priority === 'P1' ? 'bg-red-100 text-red-800' :
                      ticket.priority === 'P2' ? 'bg-orange-100 text-orange-800' :
                      ticket.priority === 'P3' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {ticket.priority}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      ticket.status === 'in_progress' ? 'bg-yellow-100 text-yellow-800' :
                      ticket.status === 'waiting_customer' ? 'bg-purple-100 text-purple-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {ticket.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{ticket.age}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
