"use client"

import { useState } from "react"
import { ThemeToggle } from "@/components/ThemeProvider"
import { api } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Mail,
  User,
  FileText,
  Tag,
  AlertCircle,
  CheckCircle2,
  Send,
  MessageSquare,
  Headphones,
} from "lucide-react"

const categories = [
  { value: "technical", label: "Technical Issue" },
  { value: "billing", label: "Billing" },
  { value: "feature_request", label: "Feature Request" },
  { value: "account", label: "Account Management" },
  { value: "integration", label: "Integration" },
  { value: "other", label: "Other" },
]

const priorities = [
  { value: "low", label: "Low", description: "General questions, minor issues" },
  { value: "medium", label: "Medium", description: "Non-urgent problems" },
  { value: "high", label: "High", description: "Important issues affecting work" },
  { value: "critical", label: "Critical", description: "System down, data loss" },
]

const MAX_MESSAGE_LENGTH = 2000

export default function SupportPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    category: "technical",
    priority: "medium",
    message: "",
  })
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [ticketId, setTicketId] = useState<number | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const messageLength = formData.message.length
  const messageProgress = (messageLength / MAX_MESSAGE_LENGTH) * 100

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = "Name is required"
    }

    if (!formData.email.trim()) {
      newErrors.email = "Email is required"
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Please enter a valid email"
    }

    if (!formData.subject.trim()) {
      newErrors.subject = "Subject is required"
    }

    if (!formData.message.trim()) {
      newErrors.message = "Message is required"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) return

    setLoading(true)
    try {
      const response = await api.submitSupport(formData)
      setTicketId(response.ticket_id)
      setSubmitted(true)
    } catch (error) {
      console.error("Failed to submit ticket:", error)
      setErrors({ submit: "Failed to submit ticket. Please try again." })
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (
    field: string,
    value: string,
    validator?: (value: string) => string
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    if (validator) {
      const error = validator(value)
      setErrors((prev) => ({ ...prev, [field]: error }))
    } else if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }))
    }
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-background">
        {/* Header */}
        <header className="sticky top-0 z-10 flex h-16 items-center justify-end border-b bg-background/95 px-6 backdrop-blur">
          <ThemeToggle />
        </header>

        {/* Success Content */}
        <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center p-6">
          <Card className="w-full max-w-md">
            <CardContent className="pt-6">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                  <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
                </div>
                <h2 className="text-2xl font-bold text-foreground">
                  Ticket Submitted!
                </h2>
                <p className="mt-2 text-muted-foreground">
                  Your support ticket has been created successfully. Our AI Agent
                  will classify and route it to the appropriate team.
                </p>

                {ticketId && (
                  <div className="mt-6 rounded-lg bg-muted p-4">
                    <p className="text-sm text-muted-foreground">Ticket ID</p>
                    <p className="text-2xl font-bold text-primary">#{ticketId}</p>
                  </div>
                )}

                <div className="mt-6 space-y-3">
                  <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Mail className="h-4 w-4" />
                    A confirmation email has been sent to {formData.email}
                  </div>
                  <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Headphones className="h-4 w-4" />
                    Expected response time: 2-4 hours
                  </div>
                </div>

                <Button
                  className="mt-6"
                  onClick={() => {
                    setSubmitted(false)
                    setFormData({
                      name: "",
                      email: "",
                      subject: "",
                      category: "technical",
                      priority: "medium",
                      message: "",
                    })
                    setTicketId(null)
                  }}
                >
                  Submit Another Ticket
                </Button>
              </div>
            </CardContent>
          </Card>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b bg-background/95 px-6 backdrop-blur">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <span className="text-lg font-bold text-primary-foreground">N</span>
          </div>
          <span className="text-lg font-semibold">NovaSaaS Support</span>
        </div>
        <ThemeToggle />
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-3xl p-6">
        {/* Hero Section */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <MessageSquare className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-3xl font-bold">How can we help you?</h1>
          <p className="mt-2 text-muted-foreground">
            Submit a ticket and our AI-powered support team will assist you
            shortly.
          </p>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>Support Request Form</CardTitle>
            <CardDescription>
              Please provide as much detail as possible to help us resolve your
              issue quickly.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {errors.submit && (
                <div className="rounded-md bg-destructive/10 p-4">
                  <div className="flex items-center gap-2 text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-sm">{errors.submit}</span>
                  </div>
                </div>
              )}

              {/* Name and Email Row */}
              <div className="grid gap-4 md:grid-cols-2">
                {/* Name */}
                <div className="space-y-2">
                  <label
                    htmlFor="name"
                    className="text-sm font-medium flex items-center gap-2"
                  >
                    <User className="h-4 w-4" />
                    Name
                    <span className="text-destructive">*</span>
                  </label>
                  <input
                    id="name"
                    type="text"
                    value={formData.name}
                    onChange={(e) =>
                      handleChange(
                        "name",
                        e.target.value,
                        (v) => (v.trim() ? "" : "Name is required")
                      )
                    }
                    className={`w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring ${
                      errors.name ? "border-destructive" : "border-input"
                    }`}
                    placeholder="Your full name"
                  />
                  {errors.name && (
                    <p className="text-xs text-destructive">{errors.name}</p>
                  )}
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <label
                    htmlFor="email"
                    className="text-sm font-medium flex items-center gap-2"
                  >
                    <Mail className="h-4 w-4" />
                    Email
                    <span className="text-destructive">*</span>
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) =>
                      handleChange(
                        "email",
                        e.target.value,
                        (v) =>
                          /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
                            ? ""
                            : "Please enter a valid email"
                      )
                    }
                    className={`w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring ${
                      errors.email ? "border-destructive" : "border-input"
                    }`}
                    placeholder="your@email.com"
                  />
                  {errors.email && (
                    <p className="text-xs text-destructive">{errors.email}</p>
                  )}
                </div>
              </div>

              {/* Subject */}
              <div className="space-y-2">
                <label
                  htmlFor="subject"
                  className="text-sm font-medium flex items-center gap-2"
                >
                  <FileText className="h-4 w-4" />
                  Subject
                  <span className="text-destructive">*</span>
                </label>
                <input
                  id="subject"
                  type="text"
                  value={formData.subject}
                  onChange={(e) =>
                    handleChange(
                      "subject",
                      e.target.value,
                      (v) => (v.trim() ? "" : "Subject is required")
                    )
                  }
                  className={`w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring ${
                    errors.subject ? "border-destructive" : "border-input"
                  }`}
                  placeholder="Brief summary of your issue"
                />
                {errors.subject && (
                  <p className="text-xs text-destructive">{errors.subject}</p>
                )}
              </div>

              {/* Category and Priority Row */}
              <div className="grid gap-4 md:grid-cols-2">
                {/* Category */}
                <div className="space-y-2">
                  <label
                    htmlFor="category"
                    className="text-sm font-medium flex items-center gap-2"
                  >
                    <Tag className="h-4 w-4" />
                    Category
                  </label>
                  <select
                    id="category"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    {categories.map((cat) => (
                      <option key={cat.value} value={cat.value}>
                        {cat.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Priority */}
                <div className="space-y-2">
                  <label
                    htmlFor="priority"
                    className="text-sm font-medium flex items-center gap-2"
                  >
                    <AlertCircle className="h-4 w-4" />
                    Priority
                  </label>
                  <select
                    id="priority"
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    {priorities.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-muted-foreground">
                    {priorities.find((p) => p.value === formData.priority)?.description}
                  </p>
                </div>
              </div>

              {/* Message */}
              <div className="space-y-2">
                <label
                  htmlFor="message"
                  className="text-sm font-medium flex items-center gap-2"
                >
                  <MessageSquare className="h-4 w-4" />
                  Message
                  <span className="text-destructive">*</span>
                </label>
                <textarea
                  id="message"
                  rows={6}
                  value={formData.message}
                  onChange={(e) =>
                    handleChange(
                      "message",
                      e.target.value.slice(0, MAX_MESSAGE_LENGTH),
                      (v) => (v.trim() ? "" : "Message is required")
                    )
                  }
                  className={`w-full resize-none rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring ${
                    errors.message ? "border-destructive" : "border-input"
                  }`}
                  placeholder="Describe your issue in detail. Include steps to reproduce, expected behavior, and any relevant information."
                />
                <div className="flex items-center justify-between">
                  {errors.message ? (
                    <p className="text-xs text-destructive">{errors.message}</p>
                  ) : (
                    <span />
                  )}
                  <div className="flex items-center gap-2">
                    <div className="h-1 w-24 rounded-full bg-muted">
                      <div
                        className={`h-1 rounded-full transition-all ${
                          messageProgress > 90
                            ? "bg-destructive"
                            : messageProgress > 70
                            ? "bg-yellow-500"
                            : "bg-primary"
                        }`}
                        style={{ width: `${messageProgress}%` }}
                      />
                    </div>
                    <span
                      className={`text-xs ${
                        messageLength > MAX_MESSAGE_LENGTH - 100
                          ? "text-destructive"
                          : "text-muted-foreground"
                      }`}
                    >
                      {messageLength}/{MAX_MESSAGE_LENGTH}
                    </span>
                  </div>
                </div>
              </div>

              {/* Priority Guide */}
              <div className="rounded-lg bg-muted p-4">
                <h4 className="text-sm font-medium mb-3">Priority Guide</h4>
                <div className="grid gap-2 sm:grid-cols-2">
                  {priorities.map((p) => (
                    <div
                      key={p.value}
                      className={`flex items-start gap-2 rounded-md p-2 ${
                        formData.priority === p.value
                          ? "bg-background ring-1 ring-ring"
                          : ""
                      }`}
                    >
                      <Badge
                        variant={
                          p.value === "critical"
                            ? "destructive"
                            : p.value === "high"
                            ? "warning"
                            : p.value === "medium"
                            ? "default"
                            : "secondary"
                        }
                        className="mt-0.5"
                      >
                        {p.label}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {p.description}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Submit Button */}
              <div className="flex justify-end">
                <Button type="submit" disabled={loading} className="min-w-[150px]">
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Submitting...
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Send className="h-4 w-4" />
                      Submit Ticket
                    </div>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer Info */}
        <div className="mt-6 text-center text-sm text-muted-foreground">
          <p>
            By submitting this form, you agree to our{" "}
            <a href="#" className="text-primary hover:underline">
              Terms of Service
            </a>{" "}
            and{" "}
            <a href="#" className="text-primary hover:underline">
              Privacy Policy
            </a>
            .
          </p>
        </div>
      </main>
    </div>
  )
}
