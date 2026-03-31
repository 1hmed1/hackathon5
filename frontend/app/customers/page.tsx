"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "../../components/Sidebar"
import { ThemeToggle } from "../../components/ThemeProvider"
import { api, type Customer } from "../../lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card"
import { Badge } from "../../components/ui/badge"
import { Button } from "../../components/ui/button"
import {
  Mail,
  MessageCircle,
  Globe,
  Phone,
  Building2,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"

const channelIcons: Record<string, React.ReactNode> = {
  email: <Mail className="h-3 w-3" />,
  chat: <MessageCircle className="h-3 w-3" />,
  web: <Globe className="h-3 w-3" />,
  phone: <Phone className="h-3 w-3" />,
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadCustomers() {
      setLoading(true)
      try {
        const data = await api.getCustomers({ page, page_size: pageSize })
        setCustomers(data.customers)
        setTotal(data.total)
      } catch (error) {
        console.error("Failed to load customers:", error)
      } finally {
        setLoading(false)
      }
    }
    loadCustomers()
  }, [page, pageSize])

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
          <h1 className="text-2xl font-bold">Customers</h1>
          <ThemeToggle />
        </header>

        <div className="p-6 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Customer Directory</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                </div>
              ) : customers.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No customers found
                </p>
              ) : (
                <>
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {customers.map((customer) => (
                      <div
                        key={customer.id}
                        className="rounded-lg border p-4 hover:bg-muted/50"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                              <span className="text-sm font-medium text-primary">
                                {customer.name.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <p className="font-medium">{customer.name}</p>
                              <p className="text-sm text-muted-foreground">
                                {customer.email}
                              </p>
                            </div>
                          </div>
                        </div>
                        {customer.company && (
                          <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
                            <Building2 className="h-3 w-3" />
                            {customer.company}
                          </div>
                        )}
                        {Object.keys(customer.channel_identifiers).length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {Object.entries(customer.channel_identifiers).map(
                              ([channel, id]) =>
                                id && (
                                  <Badge key={channel} variant="secondary" className="text-xs">
                                    {channelIcons[channel]}
                                    <span className="ml-1">{channel}</span>
                                  </Badge>
                                )
                            )}
                          </div>
                        )}
                        <div className="mt-3 text-xs text-muted-foreground">
                          Customer since {new Date(customer.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Pagination */}
                  <div className="flex items-center justify-between border-t pt-4 mt-4">
                    <span className="text-sm text-muted-foreground">
                      Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} customers
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
