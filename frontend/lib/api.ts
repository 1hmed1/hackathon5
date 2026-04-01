const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export interface Ticket {
  id: number
  customer_id: number
  subject: string
  status: string
  priority: string
  channel: string
  category: string | null
  created_at: string
  updated_at: string
  assigned_to: string | null
}

export interface TicketMessage {
  id: number
  ticket_id: number
  sender: string
  sender_type: string
  message: string
  timestamp: string
}

export interface TicketDetail extends Ticket {
  messages: TicketMessage[]
}

export interface Customer {
  id: number
  name: string
  email: string
  company: string | null
  created_at: string
  channel_identifiers: Record<string, string | null>
}

export interface Conversation {
  id: number
  customer_id: number
  customer_name: string
  customer_email: string
  channel: string
  status: string
  last_message_at: string
  message_count: number
}

export interface MetricsOverview {
  total_tickets: number
  open_tickets: number
  escalations: number
  avg_sentiment: number
  tickets_by_channel: Record<string, number>
  tickets_by_status: Record<string, number>
}

export interface ChannelMetrics {
  channel: string
  total_tickets: number
  open_tickets: number
  resolved_tickets: number
  avg_response_time_hours: number | null
  avg_sentiment: number | null
}

export interface HealthStatus {
  status: string
  database: string
  channels: Record<string, string>
}

export interface SupportSubmission {
  name: string
  email: string
  subject: string
  category: string
  message: string
  priority: string
}

export interface SupportSubmissionResponse {
  ticket_id: number
  status: string
  message: string
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "An error occurred" }))
    throw new Error(error.detail || "An error occurred")
  }
  return response.json()
}

export const api = {
  // Health
  async getHealth(): Promise<HealthStatus> {
    const response = await fetch(`${API_BASE_URL}/health`)
    return handleResponse<HealthStatus>(response)
  },

  // Tickets
  async getTickets(params?: {
    status?: string
    channel?: string
    priority?: string
    page?: number
    page_size?: number
  }): Promise<{ tickets: Ticket[]; total: number; page: number; page_size: number; total_pages: number }> {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.set("status", params.status)
    if (params?.channel) searchParams.set("channel", params.channel)
    if (params?.priority) searchParams.set("priority", params.priority)
    if (params?.page) searchParams.set("page", params.page.toString())
    if (params?.page_size) searchParams.set("page_size", params.page_size.toString())

    const response = await fetch(`${API_BASE_URL}/api/tickets?${searchParams}`)
    return handleResponse(response)
  },

  async getTicket(id: number): Promise<TicketDetail> {
    const response = await fetch(`${API_BASE_URL}/api/tickets/${id}`)
    return handleResponse<TicketDetail>(response)
  },

  // Conversations
  async getConversations(params?: {
    page?: number
    page_size?: number
  }): Promise<{ conversations: Conversation[]; total: number; page: number; page_size: number }> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set("page", params.page.toString())
    if (params?.page_size) searchParams.set("page_size", params.page_size.toString())

    const response = await fetch(`${API_BASE_URL}/api/conversations?${searchParams}`)
    return handleResponse(response)
  },

  // Customers
  async getCustomers(params?: {
    page?: number
    page_size?: number
  }): Promise<{ customers: Customer[]; total: number; page: number; page_size: number }> {
    const searchParams = new URLSearchParams()
    if (params?.page) searchParams.set("page", params.page.toString())
    if (params?.page_size) searchParams.set("page_size", params.page_size.toString())

    const response = await fetch(`${API_BASE_URL}/api/customers?${searchParams}`)
    return handleResponse(response)
  },

  // Metrics
  async getMetricsOverview(): Promise<MetricsOverview> {
    const response = await fetch(`${API_BASE_URL}/api/metrics/overview`)
    return handleResponse<MetricsOverview>(response)
  },

  async getMetricsChannels(): Promise<ChannelMetrics[]> {
    const response = await fetch(`${API_BASE_URL}/api/metrics/channels`)
    return handleResponse<ChannelMetrics[]>(response)
  },

  // Support
  async submitSupport(data: SupportSubmission): Promise<SupportSubmissionResponse> {
    const response = await fetch(`${API_BASE_URL}/api/support/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
    return handleResponse<SupportSubmissionResponse>(response)
  },
}
