"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "@/components/Sidebar"
import { ThemeToggle } from "@/components/ThemeProvider"
import { api, type MetricsOverview, type Ticket } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  TrendingUp,
  TrendingDown,
  Mail,
  MessageCircle,
  Globe,
  Phone,
  ArrowUpRight,
  ArrowDownRight,
  AlertTriangle,
  CheckCircle2,
  Clock,
} from "lucide-react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"

// Channel icon mapping
const channelIcons: Record<string, React.ReactNode> = {
  email: <Mail className="h-4 w-4" />,
  chat: <MessageCircle className="h-4 w-4" />,
  web: <Globe className="h-4 w-4" />,
  phone: <Phone className="h-4 w-4" />,
}

// Status badge variant mapping
const statusVariants: Record<string, "default" | "success" | "warning" | "destructive"> = {
  open: "warning",
  in_progress: "default",
  resolved: "success",
  closed: "default",
  escalated: "destructive",
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null)
  const [recentTickets, setRecentTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadData() {
      try {
        const [metricsData, ticketsData] = await Promise.all([
          api.getMetricsOverview(),
          api.getTickets({ page: 1, page_size: 10 }),
        ])
        setMetrics(metricsData)
        setRecentTickets(ticketsData.tickets)
      } catch (error) {
        console.error("Failed to load dashboard data:", error)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  // Prepare channel data for chart
  const channelData = metrics
    ? Object.entries(metrics.tickets_by_channel).map(([channel, count]) => ({
        name: channel.charAt(0).toUpperCase() + channel.slice(1),
        count,
      }))
    : []

  // Calculate trends (simulated for demo)
  const getTrend = (value: number) => {
    const trend = value > 0 ? "up" : "down"
    const percent = Math.abs(value)
    return { trend, percent }
  }

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
            <p className="mt-4 text-muted-foreground">Loading dashboard...</p>
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
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <div className="flex items-center gap-4">
            <ThemeToggle />
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm text-muted-foreground">AI Agent Active</span>
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Stats Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {/* Total Tickets */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Tickets</CardTitle>
                <Ticket className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics?.total_tickets ?? 0}</div>
                <div className="flex items-center text-xs text-muted-foreground">
                  {getTrend(12).trend === "up" ? (
                    <ArrowUpRight className="h-3 w-3 text-green-500 mr-1" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3 text-red-500 mr-1" />
                  )}
                  <span className={getTrend(12).trend === "up" ? "text-green-500" : "text-red-500"}>
                    +{getTrend(12).percent}%
                  </span>
                  <span className="ml-1">from last week</span>
                </div>
              </CardContent>
            </Card>

            {/* Open Tickets */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Open Tickets</CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics?.open_tickets ?? 0}</div>
                <div className="flex items-center text-xs text-muted-foreground">
                  {getTrend(-5).trend === "up" ? (
                    <ArrowUpRight className="h-3 w-3 text-green-500 mr-1" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3 text-red-500 mr-1" />
                  )}
                  <span className={getTrend(-5).trend === "up" ? "text-green-500" : "text-red-500"}>
                    {getTrend(-5).trend === "up" ? "+" : "-"}{getTrend(-5).percent}%
                  </span>
                  <span className="ml-1">from last week</span>
                </div>
              </CardContent>
            </Card>

            {/* Escalations */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Escalations</CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{metrics?.escalations ?? 0}</div>
                <div className="flex items-center text-xs text-muted-foreground">
                  {getTrend(-20).trend === "up" ? (
                    <ArrowUpRight className="h-3 w-3 text-green-500 mr-1" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3 text-red-500 mr-1" />
                  )}
                  <span className={getTrend(-20).trend === "up" ? "text-green-500" : "text-red-500"}>
                    {getTrend(-20).trend === "up" ? "+" : "-"}{getTrend(-20).percent}%
                  </span>
                  <span className="ml-1">from last week</span>
                </div>
              </CardContent>
            </Card>

            {/* Avg Sentiment */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Sentiment</CardTitle>
                <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(metrics?.avg_sentiment ?? 0).toFixed(2)}
                </div>
                <div className="flex items-center text-xs text-muted-foreground">
                  {getTrend(8).trend === "up" ? (
                    <ArrowUpRight className="h-3 w-3 text-green-500 mr-1" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3 text-red-500 mr-1" />
                  )}
                  <span className={getTrend(8).trend === "up" ? "text-green-500" : "text-red-500"}>
                    +{getTrend(8).percent}%
                  </span>
                  <span className="ml-1">from last week</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts Row */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Tickets by Channel */}
            <Card>
              <CardHeader>
                <CardTitle>Tickets by Channel</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={channelData}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Bar
                        dataKey="count"
                        fill="hsl(var(--primary))"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Live Sentiment Gauge */}
            <Card>
              <CardHeader>
                <CardTitle>Live Sentiment Gauge</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col items-center justify-center">
                <div className="relative h-48 w-48">
                  <svg className="h-full w-full" viewBox="0 0 100 100">
                    {/* Background arc */}
                    <path
                      d="M 10 50 A 40 40 0 0 1 90 50"
                      fill="none"
                      stroke="hsl(var(--muted))"
                      strokeWidth="8"
                      strokeLinecap="round"
                    />
                    {/* Sentiment arc */}
                    <path
                      d="M 10 50 A 40 40 0 0 1 90 50"
                      fill="none"
                      stroke={
                        (metrics?.avg_sentiment ?? 0) > 0.7
                          ? "#22c55e"
                          : (metrics?.avg_sentiment ?? 0) > 0.4
                          ? "#eab308"
                          : "#ef4444"
                      }
                      strokeWidth="8"
                      strokeLinecap="round"
                      strokeDasharray="283"
                      strokeDashoffset={283 - (283 * (metrics?.avg_sentiment ?? 0))}
                      className="gauge-fill"
                      style={{ transition: "stroke-dashoffset 1s ease-out" }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl font-bold">
                      {((metrics?.avg_sentiment ?? 0) * 100).toFixed(0)}%
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {(metrics?.avg_sentiment ?? 0) > 0.7
                        ? "Positive"
                        : (metrics?.avg_sentiment ?? 0) > 0.4
                        ? "Neutral"
                        : "Negative"}
                    </span>
                  </div>
                </div>
                <div className="mt-4 flex gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <div className="h-2 w-2 rounded-full bg-green-500" />
                    Positive
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="h-2 w-2 rounded-full bg-yellow-500" />
                    Neutral
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="h-2 w-2 rounded-full bg-red-500" />
                    Negative
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent Tickets Table */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Tickets</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b text-sm text-muted-foreground">
                      <th className="pb-3 text-left font-medium">Ticket</th>
                      <th className="pb-3 text-left font-medium">Subject</th>
                      <th className="pb-3 text-left font-medium">Channel</th>
                      <th className="pb-3 text-left font-medium">Priority</th>
                      <th className="pb-3 text-left font-medium">Status</th>
                      <th className="pb-3 text-left font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentTickets.map((ticket) => (
                      <tr key={ticket.id} className="border-b last:border-0 hover:bg-muted/50">
                        <td className="py-3">
                          <span className="font-medium text-primary">
                            #{ticket.id}
                          </span>
                        </td>
                        <td className="py-3">
                          <span className="text-sm">{ticket.subject}</span>
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            {channelIcons[ticket.channel] || <Globe className="h-4 w-4" />}
                            <span className="text-sm capitalize">{ticket.channel}</span>
                          </div>
                        </td>
                        <td className="py-3">
                          <Badge
                            variant={
                              ticket.priority === "critical"
                                ? "destructive"
                                : ticket.priority === "high"
                                ? "warning"
                                : ticket.priority === "medium"
                                ? "default"
                                : "secondary"
                            }
                          >
                            {ticket.priority}
                          </Badge>
                        </td>
                        <td className="py-3">
                          <Badge variant={statusVariants[ticket.status] || "default"}>
                            {ticket.status.replace("_", " ")}
                          </Badge>
                        </td>
                        <td className="py-3">
                          <span className="text-sm text-muted-foreground">
                            {new Date(ticket.created_at).toLocaleDateString()}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

function Ticket() {
  return (
    <svg
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z"
      />
    </svg>
  )
}
