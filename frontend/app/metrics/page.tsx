"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "@/components/Sidebar"
import { ThemeToggle } from "@/components/ThemeProvider"
import { api, type MetricsOverview, type ChannelMetrics } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts"
import { Mail, MessageCircle, Globe, Phone, TrendingUp, TrendingDown } from "lucide-react"

const channelIcons: Record<string, React.ReactNode> = {
  email: <Mail className="h-4 w-4" />,
  chat: <MessageCircle className="h-4 w-4" />,
  web: <Globe className="h-4 w-4" />,
  phone: <Phone className="h-4 w-4" />,
}

const COLORS = ["#3b82f6", "#22c55e", "#eab308", "#ef4444", "#8b5cf6", "#ec4899"]

export default function MetricsPage() {
  const [overview, setOverview] = useState<MetricsOverview | null>(null)
  const [channelMetrics, setChannelMetrics] = useState<ChannelMetrics[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadMetrics() {
      setLoading(true)
      try {
        const [overviewData, channelData] = await Promise.all([
          api.getMetricsOverview(),
          api.getMetricsChannels(),
        ])
        setOverview(overviewData)
        setChannelMetrics(channelData)
      } catch (error) {
        console.error("Failed to load metrics:", error)
      } finally {
        setLoading(false)
      }
    }
    loadMetrics()
  }, [])

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
            <p className="mt-4 text-muted-foreground">Loading metrics...</p>
          </div>
        </main>
      </div>
    )
  }

  // Prepare status data for pie chart
  const statusData = overview
    ? Object.entries(overview.tickets_by_status).map(([status, count]) => ({
        name: status.replace("_", " ").charAt(0).toUpperCase() + status.replace("_", " ").slice(1),
        value: count,
      }))
    : []

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
          <h1 className="text-2xl font-bold">Metrics</h1>
          <ThemeToggle />
        </header>

        <div className="p-6 space-y-6">
          {/* Overview Stats */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Tickets</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{overview?.total_tickets ?? 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Open Tickets</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{overview?.open_tickets ?? 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Escalations</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{overview?.escalations ?? 0}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Sentiment</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(overview?.avg_sentiment ?? 0).toFixed(2)}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Tickets by Status */}
            <Card>
              <CardHeader>
                <CardTitle>Tickets by Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={statusData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) =>
                          `${name}: ${(percent * 100).toFixed(0)}%`
                        }
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {statusData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={COLORS[index % COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Tickets by Channel */}
            <Card>
              <CardHeader>
                <CardTitle>Tickets by Channel</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(overview?.tickets_by_channel || {}).map(
                        ([channel, count]) => ({
                          name: channel.charAt(0).toUpperCase() + channel.slice(1),
                          count,
                        })
                      )}
                    >
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis dataKey="name" className="text-xs" />
                      <YAxis className="text-xs" />
                      <Tooltip />
                      <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Channel Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Channel Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b text-sm text-muted-foreground">
                      <th className="pb-3 text-left font-medium">Channel</th>
                      <th className="pb-3 text-left font-medium">Total</th>
                      <th className="pb-3 text-left font-medium">Open</th>
                      <th className="pb-3 text-left font-medium">Resolved</th>
                      <th className="pb-3 text-left font-medium">Avg Response</th>
                      <th className="pb-3 text-left font-medium">Avg Sentiment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {channelMetrics.map((channel) => (
                      <tr key={channel.channel} className="border-b last:border-0">
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            {channelIcons[channel.channel]}
                            <span className="capitalize font-medium">
                              {channel.channel}
                            </span>
                          </div>
                        </td>
                        <td className="py-3">{channel.total_tickets}</td>
                        <td className="py-3">
                          <span className="text-yellow-600">{channel.open_tickets}</span>
                        </td>
                        <td className="py-3">
                          <span className="text-green-600">{channel.resolved_tickets}</span>
                        </td>
                        <td className="py-3">
                          {channel.avg_response_time_hours
                            ? `${channel.avg_response_time_hours.toFixed(1)}h`
                            : "N/A"}
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            {channel.avg_sentiment !== null && (
                              <>
                                {channel.avg_sentiment > 0.7 ? (
                                  <TrendingUp className="h-4 w-4 text-green-500" />
                                ) : channel.avg_sentiment > 0.4 ? (
                                  <TrendingUp className="h-4 w-4 text-yellow-500" />
                                ) : (
                                  <TrendingDown className="h-4 w-4 text-red-500" />
                                )}
                                <span
                                  className={
                                    channel.avg_sentiment > 0.7
                                      ? "text-green-600"
                                      : channel.avg_sentiment > 0.4
                                      ? "text-yellow-600"
                                      : "text-red-600"
                                  }
                                >
                                  {channel.avg_sentiment.toFixed(2)}
                                </span>
                              </>
                            )}
                          </div>
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
