# Bizz AI — Build Plan

## 1. Purpose

This document is the execution plan for building the Bizz AI MVP.

The project is divided into **5 phases**, with exactly **2 instruction sets per phase**.

That produces **10 controlled implementation milestones**.

The coding agent should execute one instruction set at a time.

### Execution rule

```text
Instruction Set
      ↓
Implement
      ↓
Run checks
      ↓
Fix issues
      ↓
Verify acceptance criteria
      ↓
STOP
      ↓
Next instruction set
```

Do not ask the coding agent to implement multiple phases in one request.

---

# PHASE 1 — FOUNDATION & DESIGN SYSTEM

## Goal

Create the technical foundation and establish the Bizz AI visual language before implementing business functionality.

---

## 1A — Project Foundation

### Objective

Initialize the Bizz AI repository and establish the frontend/backend development foundation.

### Build

Create:

```text
bizz-ai/
├── frontend/
├── backend/
├── docs/
├── docker-compose.yml
├── .env.example
├── README.md
├── PRODUCT.md
├── DESIGN.md
├── ARCHITECTURE.md
└── BUILD_PLAN.md
```

Initialize:

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Lucide icons
- Basic linting/type checking

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Database configuration
- Basic health endpoint

### Infrastructure

- PostgreSQL through Docker Compose
- Environment configuration
- Local development instructions

### Project conventions

The agent must read:

```text
PRODUCT.md
DESIGN.md
ARCHITECTURE.md
BUILD_PLAN.md
```

before implementing.

### Constraints

Do not build:

- Dashboard features
- Customer features
- ML
- LLM integration
- Complex authentication
- Business workflows

This instruction set is about foundation only.

### Acceptance Criteria

```text
[ ] Frontend starts successfully
[ ] Backend starts successfully
[ ] PostgreSQL starts successfully
[ ] Frontend can reach backend health endpoint
[ ] Environment variables are documented
[ ] No secrets are committed
[ ] Type checking passes
[ ] Backend basic checks pass
[ ] README contains local setup instructions
```

### Stop Condition

After the acceptance criteria pass, stop.

Do not continue to 1B automatically.

---

# 1B — Bizz AI Design System & Application Shell

## Objective

Build the visual foundation and application shell.

The application should already feel like Bizz AI before any real intelligence is implemented.

### Build

Establish:

- Typography
- Color tokens
- Spacing
- Border system
- Radius system
- Shadow system
- Light/dark theme foundation
- Responsive layout rules

Create reusable UI primitives using shadcn/ui where appropriate.

### Core components

```text
Button
Input
Select
Dropdown
Tabs
Badge
Card
Dialog
Drawer
Tooltip
Toast
Table
Skeleton
EmptyState
ErrorState
```

### Application shell

Create:

```text
Sidebar
Header
Main content container
Command palette
Navigation state
User menu placeholder
Notification placeholder
```

Primary navigation:

```text
Overview
Customers
Segments
Opportunities
Predictions
Insights
```

Secondary navigation:

```text
Data
Alerts
Reports
Settings
```

### Visual requirements

Follow `DESIGN.md`.

Especially:

- No excessive gradients
- No glassmorphism
- No glowing AI effects
- No decorative AI graphics
- No emoji interface icons
- No excessive rounded cards
- No random colors
- No decorative charts
- No giant dashboard typography

Use Lucide icons consistently.

### Placeholder screens

Create basic route/page shells for the major navigation items.

These screens should demonstrate the design system without pretending that functionality exists.

### Acceptance Criteria

```text
[ ] Application shell works
[ ] Navigation works
[ ] All primary routes resolve
[ ] Design tokens are consistent
[ ] Components are reusable
[ ] Responsive layout works
[ ] Light/dark themes are coherent
[ ] Keyboard focus is visible
[ ] No placeholder lorem ipsum
[ ] No fake business metrics
[ ] UI follows DESIGN.md
```

### Stop Condition

The shell should be visually reviewable as a standalone Bizz AI product.

Stop before Phase 2.

---

# PHASE 2 — AUTHENTICATION & BUSINESS DATA

## Goal

Create a complete application boundary and realistic business data foundation.

---

# 2A — Authentication

## Objective

Implement simple but legitimate authentication.

### Backend

Implement:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

Implement:

- User model
- Password hashing
- Authentication token/session mechanism
- Protected API dependency/middleware
- Validation
- Authentication error handling

### Frontend

Create:

```text
/login
/register
```

Implement:

- Registration form
- Login form
- Logout
- Auth state
- Protected dashboard routes
- Redirect behavior
- Loading states
- Error states

### Security requirements

- Never store plaintext passwords
- Never expose secrets
- Use environment variables
- Validate input
- Protect application APIs

### Acceptance Criteria

```text
[ ] User can register
[ ] User can log in
[ ] Incorrect credentials fail safely
[ ] User can access protected routes after login
[ ] Unauthenticated users cannot access protected application routes
[ ] User can log out
[ ] /auth/me returns current user
[ ] Passwords are hashed
[ ] Auth errors are handled cleanly
```

### Stop Condition

Do not add business features.

---

# 2B — Business Data Model & Demo Dataset

## Objective

Create the data foundation used by the analytics engine.

### Database entities

Implement initial models for:

```text
User
Customer
Product
Transaction
Campaign
Interaction
Segment
Prediction
Opportunity
Insight
Alert
```

Use PostgreSQL and SQLAlchemy.

Use migrations.

### Relationships

At minimum support:

```text
Customer
 ├── Transactions
 ├── Interactions
 ├── Campaign interactions
 ├── Predictions
 └── Opportunities

Product
 └── Transactions

Campaign
 └── Interactions

Segment
 └── Customers
```

### Demo data

Generate realistic interconnected demo data.

The dataset should contain meaningful relationships between:

- Customers
- Products
- Transactions
- Campaigns
- Interactions

The dataset must not consist of meaningless random values.

The initial dataset should be large enough to demonstrate the product but small enough to run locally.

A reasonable initial target is approximately:

```text
10,000 customers
50+ products
100,000+ transactions
interaction history
campaign activity
```

Exact scale may be adjusted based on local performance.

### Data requirements

Customer data should support:

- Recency
- Frequency
- Monetary value
- Engagement
- Purchase history

### Acceptance Criteria

```text
[ ] Database migrations work
[ ] Models are relationally consistent
[ ] Demo dataset can be generated repeatedly
[ ] Customer records connect to transactions
[ ] Transactions connect to products
[ ] Interactions connect to customers/campaigns
[ ] Data can be queried through backend services
[ ] No business logic is embedded in database seed scripts
```

### Stop Condition

At the end of Phase 2:

```text
Register → Login → Protected App → Database → Business Data
```

must work.

---

# PHASE 3 — INTELLIGENCE ENGINE & OVERVIEW

## Goal

Build the analytical foundation and expose it through the central Bizz AI dashboard.

---

# 3A — Analytics & ML Engine

## Objective

Implement the four core analytical pillars.

### Analytics

Create deterministic calculations for:

```text
Revenue
Customer count
Average order value
Purchase frequency
Engagement
Retention
Customer value
Segment metrics
Trend metrics
```

Every metric must have a clear calculation.

### Segmentation

Create features based on:

```text
Recency
Frequency
Monetary value
Engagement
Purchase behavior
```

Implement an initial clustering approach such as K-Means.

Do not arbitrarily assign customer labels.

Segments should be interpretable.

Potential business labels:

```text
High Value
Growth Potential
Occasional Buyers
At Risk
New Customers
```

Labels should reflect actual cluster characteristics.

### Churn prediction

Implement an initial churn model based on available customer behavior.

Return:

```text
customer_id
probability
risk classification
supporting features where available
```

### Purchase prediction

Implement an initial purchase-probability model.

### Opportunity scoring

Create deterministic opportunity scoring based on relevant business signals.

Possible inputs:

```text
Customer value
Purchase frequency
Product affinity
Engagement
Purchase history
Churn/risk information
```

### Model lifecycle

Separate:

```text
Training
Evaluation
Model persistence
Inference
```

Do not retrain models for every API request.

### Evaluation

Record appropriate metrics.

For classification, use relevant measures such as:

```text
Precision
Recall
F1
ROC-AUC where appropriate
```

For clustering, use:

```text
Silhouette score
Business interpretability
```

### Acceptance Criteria

```text
[ ] Analytics calculations are deterministic
[ ] Segments are generated from real features
[ ] Churn predictions are generated by a model
[ ] Purchase predictions are generated by a model
[ ] Opportunity scores are reproducible
[ ] Models can be loaded for inference
[ ] Model evaluation can be reproduced
[ ] ML logic is separated from API route handlers
[ ] No random values are used as fake predictions
```

### Stop Condition

Do not build the dashboard yet.

---

# 3B — Bizz AI Overview Dashboard

## Objective

Build the primary Bizz AI business intelligence interface using real backend data.

### Dashboard philosophy

The dashboard must answer:

```text
What is happening?
Why is it happening?
What is likely to happen next?
What should I investigate?
```

### Main sections

#### Business Health

Display meaningful KPIs such as:

```text
Revenue
Customers
Retention
Opportunities
```

Each metric should show context and change where available.

#### What Needs Attention

Surface important issues such as:

```text
Retention decline
High churn risk
Revenue anomaly
Engagement decline
```

Each item should include:

- Problem
- Impact
- Relevant context
- Priority
- Action

#### Opportunities

Show important opportunities with:

- Estimated value
- Customers affected
- Confidence/score
- Opportunity type

#### Business Trends

Use purposeful charts.

Charts must answer a business question.

### Investigation

Important dashboard elements should link to deeper workflows.

Example:

```text
Retention ↓
    ↓
Affected segment
    ↓
Affected customers
    ↓
Behavior
    ↓
Prediction
    ↓
Opportunity/action
```

### Acceptance Criteria

```text
[ ] Dashboard uses backend data
[ ] No hardcoded fake business metrics
[ ] KPI calculations match backend
[ ] Important changes are visible
[ ] "What Needs Attention" is functional
[ ] Opportunities are linked to underlying data
[ ] Charts have analytical purpose
[ ] Loading states exist
[ ] Empty states exist
[ ] Error states exist
[ ] Dashboard follows DESIGN.md
[ ] Desktop experience is polished
```

### Stop Condition

The Overview should now be a credible working business intelligence dashboard.

---

# PHASE 4 — BUSINESS WORKFLOWS & AI

## Goal

Connect Bizz AI's analytical outputs into coherent user workflows and introduce the LLM as an interpretation layer.

---

# 4A — Customers, Segments, Predictions & Opportunities

## Objective

Implement the four main intelligence workflows.

### Customers

Build:

- Customer table
- Search
- Filters
- Sorting
- Pagination
- Customer detail
- Customer intelligence drawer
- Purchase history
- Engagement
- Segment
- Prediction signals
- Relevant opportunities

### Segments

Build:

- Segment list
- Segment overview
- Customer count
- Revenue
- Engagement
- Retention
- Segment characteristics
- Customer inspection

### Predictions

Build:

- Prediction list
- Probability
- Risk classification
- Supporting factors
- Evidence
- Customer linkage

Do not confuse probability with confidence.

### Opportunities

Build:

- Opportunity list
- Opportunity detail
- Type
- Estimated value
- Customers affected
- Target segment
- Score/confidence
- Detection reasons
- Recommended action
- Underlying customers

### Acceptance Criteria

```text
[ ] Customer workflow is complete
[ ] Segment workflow is complete
[ ] Prediction workflow is complete
[ ] Opportunity workflow is complete
[ ] Tables support meaningful analysis
[ ] Users can navigate between related entities
[ ] Customer → Prediction → Opportunity relationships work
[ ] Segment → Customers relationships work
[ ] All workflows use real backend data
[ ] Loading/error/empty states work
```

### Stop Condition

Do not integrate the LLM yet.

---

# 4B — LLM Intelligence Layer

## Objective

Add natural-language intelligence without allowing the LLM to become the source of truth.

### Provider abstraction

Implement:

```text
LLMProvider
    │
    ├── GeminiProvider
    │
    └── OllamaProvider
```

The provider should be selectable through environment configuration.

Example:

```text
LLM_PROVIDER=gemini
```

or:

```text
LLM_PROVIDER=ollama
```

### Responsibilities

The LLM may:

- Explain analytical results
- Summarize business changes
- Explain opportunities
- Generate recommendations
- Answer analytical questions using structured context
- Generate report summaries

### The LLM must not:

- Invent metrics
- Invent customers
- Invent predictions
- Invent opportunities
- Replace deterministic calculations
- Replace ML inference

### Structured context

Pass structured analytical context to the model.

Example:

```json
{
  "metric": {
    "name": "retention",
    "current": 87.4,
    "previous": 89.7,
    "change": -2.3
  },
  "affected_segment": {
    "name": "Occasional Buyers",
    "customers": 2184
  },
  "estimated_revenue_at_risk": 320000
}
```

### AI interface

Provide:

```text
Bizz Insight
Ask Bizz
Explain this
Summarize
```

The interface must remain restrained.

No:

- AI glow
- giant chatbot page
- decorative sparkle overload
- "AI magic" animations

### Provider failure

If the LLM is unavailable:

```text
Core analytics must continue working.
```

The application should show a useful fallback error state.

### Acceptance Criteria

```text
[ ] Gemini provider works when configured
[ ] Ollama provider works when configured
[ ] Provider can be switched through configuration
[ ] Core analytics work without an LLM
[ ] LLM receives structured context
[ ] LLM responses are clearly grounded in available data
[ ] LLM failures do not break the dashboard
[ ] Secrets are not exposed to frontend code
[ ] AI UI follows DESIGN.md
```

### Stop Condition

Bizz AI now has both deterministic intelligence and AI-assisted explanation.

---

# PHASE 5 — DATA, ALERTS, REPORTS & FINAL POLISH

## Goal

Complete the product loop and make the MVP presentation-ready.

---

# 5A — Data, Alerts & Reports

## Objective

Complete the supporting workflows around the intelligence engine.

### Data

Build:

```text
Data Sources
Dataset import
CSV upload
Dataset preview
Validation
Data health
```

For v1, CSV import is sufficient.

### Alerts

Create alerts for meaningful events such as:

```text
High churn risk
Revenue anomaly
Engagement decline
New opportunity
Segment change
```

Alerts should link to the underlying business object.

### Reports

Generate a structured business report containing:

```text
Executive Summary
Key Metrics
Customer Trends
Segment Analysis
Predictions
Opportunities
Recommendations
```

Where appropriate, the LLM can generate narrative summaries from structured analytical data.

### Acceptance Criteria

```text
[ ] CSV upload works
[ ] Dataset validation works
[ ] Dataset errors are understandable
[ ] Alerts are generated from actual business conditions
[ ] Alerts link to relevant data
[ ] Reports contain real analytics
[ ] Reports can include AI-generated summaries
[ ] Report generation handles failure states
```

### Stop Condition

Do not add unrelated features.

---

# 5B — Final Engineering & UX Quality Pass

## Objective

Make the existing product coherent, reliable, and presentation-ready.

This is a **quality pass**, not a feature-generation pass.

### UX audit

Check:

```text
Loading
Empty
Error
Success
Disabled
Hover
Focus
Confirmation
Navigation
Responsive behavior
```

### Visual audit

Remove:

- Unnecessary cards
- Excessive borders
- Excessive shadows
- Random colors
- Inconsistent spacing
- Inconsistent typography
- Inconsistent icons
- Unnecessary gradients
- Decorative elements
- Meaningless charts

Check:

- Typography hierarchy
- Information density
- Chart readability
- Table readability
- Alignment
- Visual rhythm
- Semantic color usage

### Accessibility

Verify:

- Keyboard navigation
- Focus states
- Semantic HTML
- Form labels
- Table headers
- Contrast
- Color-independent status communication

### Engineering audit

Check:

```text
TypeScript errors
Python type issues
Lint errors
API validation
Authentication
Database migrations
Environment variables
Error handling
Logging
Docker build
Production build
```

### Security audit

Confirm:

```text
[ ] No API keys in frontend
[ ] No secrets committed
[ ] Passwords are hashed
[ ] Protected endpoints require authentication
[ ] Input validation exists
[ ] CORS is intentional
[ ] Errors do not expose sensitive internals
```

### Product integrity audit

Confirm:

```text
[ ] No fake metrics
[ ] No fake model predictions
[ ] No random opportunity generation
[ ] No unsupported AI claims
[ ] Analytics and ML remain authoritative
[ ] LLM remains an interpretation layer
[ ] Core application works without LLM availability
```

### Final user journey

The complete journey should work:

```text
Register
   ↓
Login
   ↓
Overview
   ↓
Notice business change
   ↓
Investigate
   ↓
Inspect segment
   ↓
Inspect customers
   ↓
Review prediction
   ↓
Discover opportunity
   ↓
Read Bizz Insight
   ↓
Take action / generate report
```

### Final acceptance criteria

```text
[ ] Complete user journey works
[ ] Frontend production build succeeds
[ ] Backend starts cleanly
[ ] Database migrations work
[ ] Authentication works
[ ] Analytics work
[ ] ML inference works
[ ] Opportunity engine works
[ ] LLM provider abstraction works
[ ] LLM failure does not break core product
[ ] Responsive behavior is acceptable
[ ] Accessibility baseline is met
[ ] No obvious visual inconsistencies
[ ] README documents setup
[ ] Environment variables documented
```

---

# 3. Agent Operating Rules

These rules apply to every instruction set.

## Rule 1 — Read the project documents first

Before making changes, read:

```text
PRODUCT.md
DESIGN.md
ARCHITECTURE.md
BUILD_PLAN.md
```

Relevant existing source code should also be inspected before modification.

---

## Rule 2 — Do not rewrite working code unnecessarily

Prefer incremental changes.

Do not replace an entire architecture simply because a different approach is easier to generate.

---

## Rule 3 — Do not invent requirements

If something is not specified and is not necessary for the current instruction set, do not add it.

---

## Rule 4 — Do not fake functionality

If a feature cannot yet be implemented, create an honest placeholder state rather than simulating intelligence with random values.

---

## Rule 5 — Keep layers separate

Respect:

```text
Frontend
    ↓
API
    ↓
Services
    ↓
Analytics / ML / LLM
    ↓
Persistence / Providers
```

---

## Rule 6 — Prefer simple architecture

Use the simplest architecture that satisfies the current requirement.

Do not introduce:

- Microservices
- Kubernetes
- Kafka
- Celery
- Redis
- Complex event buses

unless a later requirement actually needs them.

---

## Rule 7 — Verify before stopping

After implementation:

1. Run relevant checks.
2. Fix failures caused by the implementation.
3. Verify acceptance criteria.
4. Summarize what changed.
5. Clearly state anything that remains incomplete.
6. Stop.

---

## Rule 8 — Never silently weaken acceptance criteria

If something cannot be completed, report it instead of pretending it passed.

---

# 4. Phase Completion Map

```text
PHASE 1
Foundation
    1A Project Foundation
    1B Design System + Shell

PHASE 2
Authentication + Data
    2A Authentication
    2B Business Data

PHASE 3
Intelligence
    3A Analytics + ML
    3B Overview Dashboard

PHASE 4
Product Intelligence
    4A Business Workflows
    4B LLM Intelligence

PHASE 5
Completion
    5A Data + Alerts + Reports
    5B Final Engineering + UX
```

---

# 5. Definition of Done

Bizz AI MVP is considered complete when a user can:

```text
Authenticate
    ↓
View business health
    ↓
Understand important changes
    ↓
Investigate customers and segments
    ↓
Review predictions
    ↓
Discover opportunities
    ↓
Understand why those opportunities exist
    ↓
Receive AI-assisted explanations
    ↓
Review alerts
    ↓
Generate a business report
```

The finished product should demonstrate the project's four core pillars:

```text
Customer Segmentation
        +
Behavior Prediction
        +
Opportunity Identification
        +
Decision Support
```

while maintaining the central product philosophy:

> **Bizz AI does not just report the business. It helps the business reason about itself.**
