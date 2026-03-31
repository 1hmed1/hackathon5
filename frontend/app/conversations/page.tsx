"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "../../components/Sidebar"
import { ThemeToggle } from "../../components/ThemeProvider"
import { api, type Conversation } from "../../lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card"
import { Badge } from "../../components/ui/badge"
import { Button } from "../../components/ui/button"
import {
  Mail,
  MessageCircle,
  Globe,
  Phone,
  Clock,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"

const channelIcons: Record<string, React.ReactNode> = {
  email: <Mail className="h-4 w-4" />,
  chat: <MessageCircle className="h-4 w-4" />,
  web: <Globe className="h-4 w-4" />,
  phone: <Phone className="h-4 w-4" />,
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadConversations() {
      setLoading(true)
      try {
        const data = await api.getConversations({ page, page_size: pageSize })
        setConversations(data.conversations)
        setTotal(data.total)
      } catch (error) {
        console.error("Failed to load conversations:", error)
      } finally {
        setLoading(false)
      }
    }
    loadConversations()
  }, [page, pageSize])

  const totalPages = Math.ceil(total / pageSize)

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "open":
        return "warning"
      case "active":
        return "default"
      case "closed":
        return "success"
      default:
        return "secondary"
    }
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
          <h1 className="text-2xl font-bold">Conversations</h1>
          <ThemeToggle />
        </header>

        <div className="p-6 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>All Conversations</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                </div>
              ) : conversations.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No conversations found
                </p>
              ) : (
                <>
                  <div className="space-y-4">
                    {conversations.map((conv) => (
                      <div
                        key={conv.id}
                        className="flex items-center justify-between rounded-lg border p-4 hover:bg-muted/50"
                      >
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                            {channelIcons[conv.channel] || <MessageCircle className="h-5 w-5" />}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{conv.customer_name}</span>
                              <Badge variant={getStatusVariant(conv.status)}>
                                {conv.status}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {conv.customer_email}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="text-right">
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              {channelIcons[conv.channel]}
                              <span className="capitalize">{conv.channel}</span>
                            </div>
                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              {new Date(conv.last_message_at).toLocaleString()}
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium">{conv.message_count} messages</p>
                          </div>
                          <Button variant="ghost" size="sm">
                            View
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Pagination */}
                  <div className="flex items-center justify-between border-t pt-4 mt-4">
                    <span className="text-sm text-muted-foreground">
                      Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} conversations
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
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
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
