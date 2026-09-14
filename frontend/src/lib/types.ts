// Espelha apps/users/models.py::Role no backend — mantenha os dois em sincronia.
export type Role = "ADMIN" | "MANAGER" | "SALES" | "DEVELOPER" | "FINANCE" | "SUPPORT"

export interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  role: Role
  is_active: boolean
  two_factor_enabled: boolean
  date_joined: string
  last_login: string | null
}

export interface LoginResponse {
  access: string
  refresh: string
  requires_2fa_setup: boolean
}

export interface TwoFactorSetupResponse {
  secret: string
  otpauth_url: string
}

// Cada seção só existe na resposta se o papel do usuário tiver acesso a ela
// (apps/dashboard/services.py::build_summary decide isso no backend).
export interface DashboardSummary {
  quotations?: Record<string, number>
  projects?: Record<string, number>
  projects_by_status?: Record<string, number>
  finance?: {
    receivable_pending: string
    overdue_total: string
    overdue_count: number
    revenue_this_month: string
    expenses_paid_this_month: string
    net_this_month: string
    commissions_pending: string
  }
  customers?: {
    total: number
    new_this_month: number
  }
  sales?: {
    quotations_by_status: Record<string, number>
    commissions_pending: string
    commissions_paid: string
  }
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// --- customers (apps/customers) ---

export type CustomerKind = "INDIVIDUAL" | "COMPANY"
export type PaymentMethod = "BOLETO" | "CARD"

export interface CustomerContact {
  id: string
  customer: string
  name: string
  role: string
  email: string
  phone: string
  created_at: string
}

export interface Customer {
  id: string
  kind: CustomerKind
  legal_name: string
  document: string
  email: string
  phone: string
  preferred_payment_method: PaymentMethod
  created_by: string
  contacts: CustomerContact[]
  created_at: string
  updated_at: string
}

// --- quotations (apps/quotations) ---

export type QuotationStatus = "DRAFT" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "CANCELLED"
export type ProjectType = "SYSTEM" | "AUTOMATION" | "WEBSITE" | "PWA" | "APP" | "SAAS" | "OTHER"

export interface Quotation {
  id: string
  customer: string
  sales_rep: string
  service_type: ProjectType
  description: string
  amount: string
  deadline_days: number | null
  status: QuotationStatus
  notes: string
  decided_at: string | null
  decided_by: string | null
  created_at: string
  updated_at: string
}

// --- projects (apps/projects) ---

export type ProjectStatus =
  | "APPROVED"
  | "AWAITING_INITIAL_PAYMENT"
  | "INITIAL_PAYMENT_CONFIRMED"
  | "IN_DEVELOPMENT"
  | "DEVELOPMENT_COMPLETED"
  | "AWAITING_CLIENT_ACCEPTANCE"
  | "ACCEPTED"
  | "AWAITING_FINAL_PAYMENT"
  | "FINAL_PAYMENT_CONFIRMED"
  | "DELIVERED"
  | "MAINTENANCE"

export interface Project {
  id: string
  customer: string
  quotation: string
  name: string
  project_type: ProjectType
  description: string
  responsible: string
  amount: string
  status: ProjectStatus
  expected_delivery_at: string | null
  delivered_at: string | null
  created_at: string
  updated_at: string
}

// --- finance (apps/finance) ---

export type ChargeType = "INITIAL" | "FINAL" | "RECURRING" | "SCOPE_CHANGE"
export type ChargeStatus = "PENDING" | "PROCESSING" | "PAID" | "OVERDUE" | "CANCELLED" | "FAILED"

export interface Charge {
  id: string
  project: string | null
  customer: string
  charge_type: ChargeType
  percentage: string | null
  amount: string
  due_date: string
  status: ChargeStatus
  payment_method: PaymentMethod
  external_provider: string
  external_id: string | null
  payment_link: string
  paid_at: string | null
  created_at: string
  updated_at: string
}

export interface Payment {
  id: string
  charge: string
  amount: string
  external_id: string
  method: string
  paid_at: string
  created_at: string
}

export type RevenueSource = "PROJECT" | "RECURRING" | "OTHER"

export interface Revenue {
  id: string
  source: RevenueSource
  payment: string | null
  amount: string
  description: string
  received_at: string
  created_at: string
}

export type ExpenseStatus = "PENDING" | "PAID" | "OVERDUE" | "CANCELLED"

export interface Expense {
  id: string
  category: string
  description: string
  amount: string
  due_date: string
  paid_at: string | null
  status: ExpenseStatus
  document: string | null
  created_by: string
  created_at: string
  updated_at: string
}

export type CommissionStatus = "PENDING" | "PAID"

export interface Commission {
  id: string
  sales_rep: string
  project: string
  payment: string
  percentage: string
  amount: string
  status: CommissionStatus
  created_at: string
  paid_at: string | null
}

export type SubscriptionStatus = "ACTIVE" | "PAUSED" | "CANCELLED"

export interface Subscription {
  id: string
  customer: string
  project: string | null
  service_description: string
  amount: string
  frequency: "MONTHLY"
  start_date: string
  next_billing_date: string
  status: SubscriptionStatus
  external_id: string | null
  created_at: string
  updated_at: string
}

// --- support (apps/support) ---

export type TicketStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED"
export type TicketPriority = "LOW" | "NORMAL" | "HIGH"

export interface Ticket {
  id: string
  customer: string
  subject: string
  description: string
  priority: TicketPriority
  status: TicketStatus
  assigned_to: string | null
  created_by: string
  resolved_at: string | null
  created_at: string
  updated_at: string
}

// --- audit (apps/audit) ---

export interface AuditLog {
  id: string
  user: string | null
  action: string
  entity_type: string
  entity_id: string
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  metadata: Record<string, unknown>
  created_at: string
}

// --- settings (apps/core) ---

export interface IntegrationsStatus {
  mercadopago: { configured: boolean }
  whatsapp: { configured: boolean }
}

// --- documents (apps/documents) ---

export type DocumentCategory = "CONTRACT" | "INVOICE" | "RECEIPT" | "PROJECT_FILE" | "OTHER"

export interface DocumentFile {
  id: string
  customer: string | null
  project: string | null
  category: DocumentCategory
  file: string
  original_filename: string
  mime_type: string
  size_bytes: number
  checksum_sha256: string
  uploaded_by: string
  created_at: string
}

// Espelha apps/leads/models.py — contato que chegou pelo site público e
// ainda não é cliente (não tem CPF/CNPJ, e a maioria nunca vai ter).
export type LeadStatus = "NEW" | "CONTACTED" | "QUALIFIED" | "CONVERTED" | "DISCARDED"
export type BudgetRange = "UNDECIDED" | "UNDER_5K" | "FROM_5K_TO_15K" | "FROM_15K_TO_40K" | "ABOVE_40K"

export interface Lead {
  id: string
  name: string
  company: string
  email: string
  phone: string
  service_type: ProjectType
  service_type_display: string
  budget_range: BudgetRange
  budget_range_display: string
  message: string
  status: LeadStatus
  internal_notes: string
  handled_by: string | null
  handled_by_name: string
  customer: string | null
  customer_name: string
  created_at: string
  updated_at: string
}

/** O que o formulário do site manda em `POST /public/contact/`. `website` é a
 * armadilha de robô — sempre vazia quando é gente de verdade preenchendo. */
export interface ContatoPublico {
  name: string
  company: string
  email: string
  phone: string
  service_type: ProjectType
  budget_range: BudgetRange
  message: string
  website: string
}
