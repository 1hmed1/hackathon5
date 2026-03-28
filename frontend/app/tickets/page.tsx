"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Sidebar } from "@/components/Sidebar"
import { ThemeToggle } from "@/components/ThemeProvider"
import { api, type Ticket } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Mail,
  MessageCircle,
  Globe,
  Phone,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"

const channelIcons: Record<string, React.ReactNode> = {
  email: <Mail className="h-4 w-4" />,
  chat: <MessageCircle className="h-4 w-4" />,
  web: <Globe className="h-4 w-4" />,
  phone: <Phone className="h-4 w-4" />,
}

const statusOptions = ["all", "open", "in_progress", "resolved", "closed", "escalated"]
const channelOptions = ["all", "email", "chat", "web", "phone"]
const priorityOptions = ["all", "low", "medium", "high", "critical"]

export default function TicketsPage() {
  const router = useRouter()
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [loading, setLoading] = useState(true)

  // Filters
  const [status, setStatus] = useState("all")
  const [channel, setChannel] = useState("all")
  const [priority, setPriority] = useState("all")
  const [searchEmail, setSearchEmail] = useState("")

  useEffect(() => {
    async function loadTickets() {
      setLoading(true)
      try {
        const data = await api.getTickets({
          status: status !== "all" ? status : undefined,
          channel: channel !== "all" ? channel : undefined,
          priority: priority !== "all" ? priority : undefined,
          page,
          page_size: pageSize,
        })
        setTickets(data.tickets)
        setTotal(data.total)
      } catch (error) {
        console.error("Failed to load tickets:", error)
      } finally {
        setLoading(false)
      }
    }
    loadTickets()
  }, [status, channel, priority, page, pageSize])

  const totalPages = Math.ceil(total / pageSize)

  const handleTicketClick = (id: number) => {
    router.push(`/tickets/${id}`)
  }

  const getPriorityVariant = (priority: string) => {
    switch (priority) {
      case "critical":
        return "destructive"
      case "high":
        return "warning"
      case "medium":
        return "default"
      default:
        return "secondary"
    }
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "open":
        return "warning"
      case "in_progress":
        return "default"
      case "resolved":
        return "success"
      case "escalated":
        return "destructive"
      default:
        return "secondary"
    }
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {/* Header */}
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
          <h1 className="text-2xl font-bold">Tickets</h1>
          <div className="flex items-center gap-4">
            <ThemeToggle />
          </div>
        </header>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Filters */}
          <Card>
            <CardContent className="p-4">
              <div className="flex flex-wrap items-center gap-4">
                {/* Search */}
                <div className="relative flex-1 min-w-[200px]">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search by customer email..."
                    value={searchEmail}
                    onChange={(e) => setSearchEmail(e.target.value)}
                    className="w-full rounded-md border border-input bg-background pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                {/* Status Filter */}
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-muted-foreground" />
                  <select
                    value={status}
                    onChange={(e) => {
                      setStatus(e.target.value)
                      setPage(1)
                    }}
                    className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    {statusOptions.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt === "all" ? "All Status" : opt.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Channel Filter */}
                <select
                  value={channel}
                  onChange={(e) => {
                    setChannel(e.target.value)
                    setPage(1)
                  }}
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {channelOptions.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt === "all" ? "All Channels" : opt}
                    </option>
                  ))}
                </select>

                {/* Priority Filter */}
                <select
                  value={priority}
                  onChange={(e) => {
                    setPriority(e.target.value)
                    setPage(1)
                  }}
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {priorityOptions.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt === "all" ? "All Priorities" : opt}
                    </option>
                  ))}
                </select>

                {/* Reset Filters */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setStatus("all")
                    setChannel("all")
                    setPriority("all")
                    setSearchEmail("")
                    setPage(1)
                  }}
                >
                  Reset
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Tickets Table */}
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50 text-sm text-muted-foreground">
                      <th className="px-4 py-3 text-left font-medium">ID</th>
                      <th className="px-4 py-3 text-left font-medium">Customer</th>
                      <th className="px-4 py-3 text-left font-medium">Subject</th>
                      <th className="px-4 py-3 text-left font-medium">Channel</th>
                      <th className="px-4 py-3 text-left font-medium">Priority</th>
                      <th className="px-4 py-3 text-left font-medium">Status</th>
                      <th className="px-4 py-3 text-left font-medium">Created</th>
                      <th className="px-4 py-3 text-left font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      <tr>
                        <td colSpan={8} className="py-8 text-center text-muted-foreground">
                          <div className="flex items-center justify-center gap-2">
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                            Loading tickets...
                          </div>
                        </td>
                      </tr>
                    ) : tickets.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-8 text-center text-muted-foreground">
                          No tickets found
                        </td>
                      </tr>
                    ) : (
                      tickets.map((ticket) => (
                        <tr
                          key={ticket.id}
                          className="border-b last:border-0 hover:bg-muted/50"
                        >
                          <td className="px-4 py-3">
                            <span className="font-medium text-primary">
                              #{ticket.id}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm">Customer #{ticket.customer_id}</span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm max-w-[200px] truncate block">
                              {ticket.subject}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {channelIcons[ticket.channel]}
                              <span className="text-sm capitalize">{ticket.channel}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={getPriorityVariant(ticket.priority)}>
                              {ticket.priority}
                            </Badge>
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={getStatusVariant(ticket.status)}>
                              {ticket.status.replace("_", " ")}
                            </Badge>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm text-muted-foreground">
                              {new Date(ticket.created_at).toLocaleDateString()}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleTicketClick(ticket.id)}
                            >
                              View
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {!loading && tickets.length > 0 && (
                <div className="flex items-center justify-between border-t px-4 py-3">
                  <span className="text-sm text-muted-foreground">
                    Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} tickets
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      Page {page} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
