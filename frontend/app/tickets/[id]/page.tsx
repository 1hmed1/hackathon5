"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { Sidebar } from "../../../components/Sidebar"
import { ThemeToggle } from "../../../components/ThemeProvider"
import { api, type TicketDetail, type TicketMessage } from "../../../lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card"
import { Badge } from "../../../components/ui/badge"
import { Button } from "../../../components/ui/button"
import {
  ArrowLeft,
  Mail,
  MessageCircle,
  Globe,
  Phone,
  AlertTriangle,
  CheckCircle2,
  Clock,
  User,
  Bot,
  Send,
} from "lucide-react"

const channelIcons: Record<string, React.ReactNode> = {
  email: <Mail className="h-4 w-4" />,
  chat: <MessageCircle className="h-4 w-4" />,
  web: <Globe className="h-4 w-4" />,
  phone: <Phone className="h-4 w-4" />,
}

export default function TicketDetailPage() {
  const router = useRouter()
  const params = useParams()
  const ticketId = parseInt(params.id as string)

  const [ticket, setTicket] = useState<TicketDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [replyMessage, setReplyMessage] = useState("")
  const [sending, setSending] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    async function loadTicket() {
      try {
        const data = await api.getTicket(ticketId)
        setTicket(data)
      } catch (error) {
        console.error("Failed to load ticket:", error)
      } finally {
        setLoading(false)
      }
    }
    loadTicket()
  }, [ticketId])

  const handleEscalate = async () => {
    setActionLoading("escalate")
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setActionLoading(null)
    alert("Ticket escalated successfully")
  }

  const handleResolve = async () => {
    setActionLoading("resolve")
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setActionLoading(null)
    alert("Ticket resolved successfully")
  }

  const handleSendReply = async () => {
    if (!replyMessage.trim()) return
    setSending(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setSending(false)
    setReplyMessage("")
    alert("Reply sent successfully")
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "critical":
        return "bg-red-500"
      case "high":
        return "bg-orange-500"
      case "medium":
        return "bg-blue-500"
      default:
        return "bg-gray-500"
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "open":
        return "bg-yellow-500"
      case "in_progress":
        return "bg-blue-500"
      case "resolved":
        return "bg-green-500"
      case "escalated":
        return "bg-red-500"
      default:
        return "bg-gray-500"
    }
  }

  const getSentimentColor = (score: number) => {
    if (score > 0.7) return "text-green-500"
    if (score > 0.4) return "text-yellow-500"
    return "text-red-500"
  }

  const getSentimentLabel = (score: number) => {
    if (score > 0.7) return "Positive"
    if (score > 0.4) return "Neutral"
    return "Negative"
  }

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
            <p className="mt-4 text-muted-foreground">Loading ticket...</p>
          </div>
        </main>
      </div>
    )
  }

  if (!ticket) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-xl font-semibold">Ticket not found</h2>
            <Button variant="link" onClick={() => router.push("/tickets")}>
              Back to Tickets
            </Button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {/* Header */}
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.push("/tickets")}>
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold">Ticket #{ticket.id}</h1>
              <p className="text-sm text-muted-foreground">{ticket.subject}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <ThemeToggle />
          </div>
        </header>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Ticket Info Bar */}
          <div className="flex flex-wrap items-center gap-4">
            <Badge
              variant={
                ticket.priority === "critical"
                  ? "destructive"
                  : ticket.priority === "high"
                  ? "warning"
                  : "default"
              }
              className="text-sm px-3 py-1"
            >
              {ticket.priority}
            </Badge>
            <Badge
              variant={
                ticket.status === "resolved"
                  ? "success"
                  : ticket.status === "escalated"
                  ? "destructive"
                  : "default"
              }
              className="text-sm px-3 py-1"
            >
              {ticket.status.replace("_", " ")}
            </Badge>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              {channelIcons[ticket.channel]}
              <span className="capitalize">{ticket.channel}</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              Created {new Date(ticket.created_at).toLocaleDateString()}
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* Message Thread */}
            <div className="lg:col-span-2 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Message Thread</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {ticket.messages.map((message, index) => (
                    <MessageBubble
                      key={message.id}
                      message={message}
                      isLast={index === ticket.messages.length - 1}
                    />
                  ))}

                  {/* Reply Input */}
                  <div className="border-t pt-4 mt-4">
                    <div className="flex gap-2">
                      <div className="flex-1 relative">
                        <textarea
                          value={replyMessage}
                          onChange={(e) => setReplyMessage(e.target.value)}
                          placeholder="Type your reply..."
                          rows={3}
                          className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                      </div>
                      <Button
                        onClick={handleSendReply}
                        disabled={sending || !replyMessage.trim()}
                        className="self-end"
                      >
                        {sending ? (
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                        ) : (
                          <>
                            Send
                            <Send className="h-4 w-4 ml-2" />
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
              {/* Actions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Button
                    variant="destructive"
                    className="w-full"
                    onClick={handleEscalate}
                    disabled={actionLoading === "escalate" || ticket.status === "escalated"}
                  >
                    {actionLoading === "escalate" ? (
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    ) : (
                      <>
                        <AlertTriangle className="h-4 w-4 mr-2" />
                        Escalate
                      </>
                    )}
                  </Button>
                  <Button
                    variant="default"
                    className="w-full"
                    onClick={handleResolve}
                    disabled={actionLoading === "resolve" || ticket.status === "resolved"}
                  >
                    {actionLoading === "resolve" ? (
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    ) : (
                      <>
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        Resolve
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* Ticket Details */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div>
                    <span className="text-muted-foreground">Customer ID:</span>
                    <span className="ml-2 font-medium">#{ticket.customer_id}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Category:</span>
                    <span className="ml-2 font-medium">
                      {ticket.category || "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Assigned To:</span>
                    <span className="ml-2 font-medium">
                      {ticket.assigned_to || "Unassigned"}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Last Updated:</span>
                    <span className="ml-2 font-medium">
                      {new Date(ticket.updated_at).toLocaleString()}
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Sentiment */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Sentiment Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className={`h-3 w-3 rounded-full ${getPriorityColor(
                          ticket.priority
                        )}`}
                      />
                      <span className="text-sm font-medium">
                        {getSentimentLabel(0.72)}
                      </span>
                    </div>
                    <span className={`text-lg font-bold ${getSentimentColor(0.72)}`}>
                      0.72
                    </span>
                  </div>
                  <div className="mt-3 h-2 w-full rounded-full bg-muted">
                    <div
                      className={`h-2 rounded-full transition-all ${getSentimentColor(0.72).replace("text-", "bg-")}`}
                      style={{ width: "72%" }}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Timeline */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Timeline</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <TimelineItem
                      icon={<Bot className="h-3 w-3" />}
                      title="Ticket Created"
                      time={new Date(ticket.created_at).toLocaleString()}
                    />
                    {ticket.messages.slice(0, 3).map((msg) => (
                      <TimelineItem
                        key={msg.id}
                        icon={
                          msg.sender_type === "customer" ? (
                            <User className="h-3 w-3" />
                          ) : (
                            <Bot className="h-3 w-3" />
                          )
                        }
                        title={`${msg.sender_type === "customer" ? "Customer" : "Agent"} replied`}
                        time={new Date(msg.timestamp).toLocaleString()}
                      />
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

function MessageBubble({
  message,
  isLast,
}: {
  message: TicketMessage
  isLast: boolean
}) {
  const isCustomer = message.sender_type === "customer"

  return (
    <div className={`flex gap-3 ${isCustomer ? "" : "flex-row-reverse"}`}>
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isCustomer ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
        }`}
      >
        {isCustomer ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </div>
      <div
        className={`max-w-[70%] rounded-lg px-4 py-2 ${
          isCustomer
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        }`}
      >
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium">{message.sender}</span>
          <span className="text-xs opacity-70">
            {new Date(message.timestamp).toLocaleString()}
          </span>
        </div>
        <p className="text-sm whitespace-pre-wrap">{message.message}</p>
      </div>
    </div>
  )
}

function TimelineItem({
  icon,
  title,
  time,
}: {
  icon: React.ReactNode
  title: string
  time: string
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted">
        {icon}
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{time}</p>
      </div>
    </div>
  )
}
