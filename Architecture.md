# Bizz AI — System Architecture

## 1. Architecture Objective

Bizz AI should use a modular architecture that separates:

- Presentation
- API/backend services
- Authentication
- Business data
- Analytics
- Machine learning
- LLM services
- Persistence
- Infrastructure

The architecture must remain understandable for a student development team while being structured enough to demonstrate sound software engineering practices.

The system should avoid premature distributed-system complexity.

---

## 2. High-Level Architecture

```text
                         ┌───────────────────────┐
                         │      BIZZ AI UI       │
                         │ Next.js + TypeScript  │
                         │ Tailwind + shadcn/ui  │
                         └───────────┬───────────┘
                                     │
                              HTTP / SSE
                                     │
                         ┌───────────▼───────────┐
                         │       FASTAPI         │
                         │      API Layer        │
                         └───────────┬───────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
       Authentication          Business APIs          Intelligence APIs
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │   Application Layer   │
                         │                       │
                         │ Customer Services     │
                         │ Segment Services      │
                         │ Opportunity Services  │
                         │ Prediction Services   │
                         │ Insight Services      │
                         └───────────┬───────────┘
                                     │
                   ┌─────────────────┼─────────────────┐
                   │                 │                 │
             PostgreSQL         Analytics/ML       LLM Layer
                   │                 │                 │
             Business data     Features/models    Gemini/Ollama
                   │                 │                 │
                   └─────────────────┼─────────────────┘
                                     │
                              Intelligence
                                     │
                         ┌───────────▼───────────┐
                         │      BIZZ AI UI       │
                         │ Insights / Actions    │
                         └───────────────────────┘
```

---

## 3. Repository Structure

Use a monorepo with clear frontend/backend separation.

```text
bizz-ai/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   └── public/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── analytics/
│   │   ├── ml/
│   │   └── llm/
│   │
│   ├── tests/
│   └── pyproject.toml
│
├── docs/
│
├── docker-compose.yml
├── .env.example
├── README.md
├── PRODUCT.md
├── DESIGN.md
├── ARCHITECTURE.md
└── BUILD_PLAN.md
```

The exact framework-generated files may differ, but application logic should remain organized according to responsibility.

---

## 4. Frontend Architecture

### Technology

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Lucide icons
- Recharts or an equivalent charting library
- TanStack Table where analytical tables require it

### Frontend responsibilities

The frontend is responsible for:

- Rendering the interface
- Navigation
- Forms
- Client-side interaction
- Data visualization
- Table interaction
- Authentication state
- Loading/error/empty states
- Calling backend APIs
- Presenting analytical results

The frontend should not contain the authoritative business calculations or ML logic.

---

## 5. Frontend Organization

Prefer feature-oriented organization where practical.

```text
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   │
│   └── (dashboard)/
│       ├── overview/
│       ├── customers/
│       ├── segments/
│       ├── opportunities/
│       ├── predictions/
│       ├── insights/
│       ├── data/
│       ├── alerts/
│       ├── reports/
│       └── settings/
│
├── components/
│   ├── ui/
│   ├── layout/
│   ├── charts/
│   ├── tables/
│   └── intelligence/
│
├── features/
│   ├── customers/
│   ├── segments/
│   ├── opportunities/
│   ├── predictions/
│   └── insights/
│
├── hooks/
├── lib/
├── types/
└── public/
```

Reusable UI primitives should not contain business-specific logic.

---

## 6. Backend Architecture

FastAPI acts as the main backend/API layer.

The backend should be organized into logical responsibilities:

```text
backend/app/

api/
    API routes and request handling

core/
    configuration
    security
    shared application concerns

db/
    database connection
    sessions
    migrations configuration

models/
    SQLAlchemy database models

schemas/
    Pydantic request/response schemas

services/
    business logic

analytics/
    metrics
    feature engineering
    customer analytics

ml/
    model training
    inference
    prediction logic
    model artifacts

llm/
    provider abstraction
    prompts
    structured AI responses
```

Routes should remain thin.

Business logic should live in services rather than being embedded inside route handlers.

---

## 7. API Structure

Use resource-oriented REST endpoints.

Example:

```text
/api/v1/auth
/api/v1/customers
/api/v1/segments
/api/v1/opportunities
/api/v1/predictions
/api/v1/insights
/api/v1/alerts
/api/v1/reports
/api/v1/data
```

Example endpoints:

```text
GET    /api/v1/customers
GET    /api/v1/customers/{id}

GET    /api/v1/segments
GET    /api/v1/segments/{id}

GET    /api/v1/opportunities
GET    /api/v1/opportunities/{id}

GET    /api/v1/predictions
GET    /api/v1/insights
GET    /api/v1/alerts
```

Use explicit request and response schemas.

Do not return raw database objects directly from API routes.

---

## 8. Authentication Architecture

Authentication is intentionally simple for v1.

```text
User
  │
  ├── Register
  │      ↓
  │   Password hash
  │      ↓
  │   PostgreSQL
  │
  └── Login
         ↓
      Verify hash
         ↓
      Auth token/session
         ↓
    Protected routes
```

Required functionality:

- Registration
- Login
- Logout
- Current user
- Protected application routes
- Password hashing
- Authentication middleware/dependencies

Passwords must never be stored in plaintext.

Authentication is a boundary around the application, not the primary product feature.

---

## 9. Database Architecture

PostgreSQL is the primary relational database.

Initial core entities:

```text
users
customers
products
transactions
campaigns
interactions
segments
predictions
opportunities
insights
alerts
```

Conceptual relationships:

```text
User
 │
 └── application access

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

Prediction
 └── Customer

Opportunity
 └── Customers / Segment
```

The exact relational schema should be designed before implementation of the corresponding feature.

Use database migrations.

---

## 10. Data Flow

The intended analytical data flow is:

```text
Data Sources
     ↓
Data Ingestion
     ↓
Validation / Cleaning
     ↓
Normalized Business Data
     ↓
Feature Engineering
     ↓
Analytics / ML
     ↓
Predictions / Scores
     ↓
Business Intelligence Layer
     ↓
API
     ↓
Bizz AI Interface
```

For the MVP, data sources can primarily be:

- Seeded demo data
- CSV import

Future integrations can include external CRM, commerce, marketing, and other systems.

---

## 11. Analytics Layer

The analytics layer converts raw business data into measurable business signals.

Initial responsibilities:

- Revenue calculation
- Customer counts
- Average order value
- Purchase frequency
- Engagement metrics
- Retention metrics
- Segment metrics
- Customer value metrics
- Trend calculations
- Feature generation

Analytics should use deterministic calculations wherever possible.

Metrics must have clearly defined formulas.

---

## 12. Machine Learning Layer

The ML layer provides predictive intelligence.

Initial models:

### Customer Segmentation

Use behavioral and transactional features such as:

- Recency
- Frequency
- Monetary value
- Engagement
- Purchase behavior

A clustering approach such as K-Means may be used for the initial implementation.

### Churn Prediction

Predict the probability that a customer will become inactive or churn according to the project's defined business rules.

### Purchase Prediction

Estimate the likelihood of a customer making a relevant future purchase.

### Opportunity Scoring

Combine relevant behavioral and business signals to rank potential opportunities.

The first implementation should favor models that are understandable, reproducible, and practical for the available dataset.

Do not introduce deep learning merely to make the project sound more advanced.

---

## 13. Model Lifecycle

Separate model training from inference.

Conceptually:

```text
Training Data
     ↓
Preprocessing
     ↓
Feature Engineering
     ↓
Train Model
     ↓
Evaluate
     ↓
Save Model Artifact
     ↓
Inference Service
     ↓
Prediction
```

The application should be able to load trained model artifacts for inference without retraining the model for every request.

Model evaluation should record appropriate metrics.

Examples:

- Classification: precision, recall, F1, ROC-AUC where appropriate
- Clustering: silhouette score and business interpretability
- Ranking/scoring: appropriate ranking or validation metrics

---

## 14. Intelligence Layer

The intelligence layer connects analytics and ML outputs to business concepts.

Example:

```text
ML output
   ↓
Churn probability = 0.87
   ↓
Business interpretation
   ↓
High churn risk
   ↓
Affected segment
   ↓
Revenue at risk
   ↓
Bizz Insight
   ↓
Recommended investigation/action
```

This layer is critical because raw model output is not automatically business intelligence.

---

## 15. Opportunity Engine

The opportunity engine should convert analytical signals into business opportunities.

Example:

```text
Customer behavior
       +
Product affinity
       +
Customer value
       +
Purchase history
       +
Engagement
       ↓
Opportunity scoring
       ↓
Opportunity
```

Each opportunity should contain, where available:

- Type
- Target customers
- Target segment
- Estimated value
- Score/confidence
- Detection reasons
- Recommended action

Opportunity generation must be deterministic/reproducible for the same underlying data and configuration.

---

## 16. LLM Architecture

The LLM is an interpretation and interaction layer.

It is not the authoritative analytics engine.

```text
                    LLM SERVICE
                         │
              ┌──────────┴──────────┐
              │                     │
        Gemini Provider        Ollama Provider
              │                     │
              └──────────┬──────────┘
                         │
                   LLM Interface
                         │
                Structured Context
                         │
          ┌──────────────┴──────────────┐
          │                             │
      Analytics                     ML outputs
          │                             │
          └──────────────┬──────────────┘
                         ↓
                    LLM response
```

The provider interface should allow switching models without changing the rest of the application.

Potential providers:

- Gemini API
- Ollama/local model

The application should support operation without an LLM for core analytical functionality.

---

## 17. LLM Responsibilities

Appropriate uses:

- Explain analytical results
- Summarize business changes
- Explain why an opportunity matters
- Generate business-oriented insight text
- Answer questions using structured application data
- Produce report summaries
- Translate analytical outputs into natural language

Inappropriate uses:

- Inventing business metrics
- Inventing customers
- Generating authoritative financial calculations
- Replacing deterministic analytics
- Replacing ML inference
- Making unsupported claims

The LLM should receive structured context rather than unrestricted database access wherever practical.

---

## 18. Structured AI Context

Prefer passing structured analytical context to the LLM.

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

The LLM can then produce a concise explanation grounded in this context.

The system should not ask the model to independently calculate values that the analytics layer can calculate reliably.

---

## 19. LLM Provider Interface

Create a common interface conceptually similar to:

```text
LLMProvider

generate_insight(context)
answer_question(context, question)
summarize(context)
```

Implement providers independently:

```text
GeminiProvider
OllamaProvider
```

The application chooses the provider through configuration.

Example configuration concept:

```text
LLM_PROVIDER=gemini
```

or:

```text
LLM_PROVIDER=ollama
```

API keys and model configuration must come from environment variables.

---

## 20. Caching and Performance

Do not introduce complex distributed infrastructure prematurely.

Initial approach:

- PostgreSQL for persistent data
- Application-level caching where useful
- Precomputed analytical summaries where useful

Redis can be introduced later for:

- Expensive analytics caching
- Background tasks
- Rate limiting
- Job queues

Do not add Redis merely because it appears in a modern architecture diagram.

---

## 21. Background Processing

The initial MVP can perform many analytical tasks synchronously or through explicit processing actions.

If background work becomes necessary, introduce:

```text
FastAPI
   ↓
Job Queue
   ↓
Worker
   ↓
Analytics / ML processing
```

Potential future technologies:

- Redis
- Celery
- RQ

These are future implementation choices, not mandatory v1 dependencies.

---

## 22. Error Handling

Backend errors should use structured API responses.

Frontend should translate them into understandable messages.

Never expose:

- Stack traces
- Database credentials
- Internal paths
- Secret values

to normal users.

Log technical details on the backend.

---

## 23. Configuration

Use environment variables for:

```text
DATABASE_URL
SECRET_KEY
AUTH configuration
LLM_PROVIDER
GEMINI_API_KEY
GEMINI_MODEL
OLLAMA_BASE_URL
OLLAMA_MODEL
```

Provide:

```text
.env.example
```

Never commit actual API keys or secrets.

---

## 24. Docker

Use Docker Compose for local infrastructure.

Initial services:

```text
frontend
backend
postgres
```

Add services only when required.

The application should be runnable through a documented local development workflow.

---

## 25. Testing Strategy

### Frontend

Test:

- Important UI components
- Form behavior
- Critical user flows
- Loading/error states

### Backend

Test:

- Authentication
- API validation
- Core services
- Analytics calculations
- Prediction interfaces

### ML

Test:

- Feature generation
- Model loading
- Prediction shape/output
- Basic model evaluation

### Integration

At minimum verify:

```text
Register
  ↓
Login
  ↓
Protected application
  ↓
Fetch business data
  ↓
Analytics
  ↓
Prediction
  ↓
Opportunity
  ↓
Insight
```

---

## 26. Security Baseline

Minimum requirements:

- Password hashing
- Secret management through environment variables
- Protected API routes
- Input validation
- ORM/database parameterization
- CORS configuration
- Reasonable authentication token/session handling
- No secrets in source control

Security should be practical for the MVP rather than an attempt to recreate an enterprise security platform.

---

## 27. Observability

Backend should have structured logging for important events:

- Authentication failures
- API errors
- Data processing
- Model inference
- LLM calls
- Unexpected failures

Do not log sensitive credentials or unnecessary personal information.

---

## 28. Architectural Boundaries

The following boundaries should remain explicit:

```text
UI
 ↓
API
 ↓
Services
 ↓
Analytics / ML / LLM
 ↓
Database / Model Artifacts / Providers
```

Do not:

- Put SQL queries directly into UI components
- Put ML logic inside API route functions
- Put business rules into React components
- Call LLM providers directly from random frontend components
- Duplicate business calculations across frontend and backend

---

## 29. MVP Architectural Principle

> **Build a modular monolith first.**

Bizz AI does not need microservices for the initial version.

A clean modular backend with clear boundaries is preferable to multiple services that add operational complexity without providing meaningful value.

The architecture should leave room for future extraction of expensive components if the product grows.

---

## 30. Future Evolution

The architecture can later evolve toward:

```text
External Data Sources
        ↓
Data Ingestion Platform
        ↓
Data Warehouse / Lake
        ↓
Feature / Analytics Platform
        ↓
ML Platform
        ↓
Opportunity / Intelligence Engine
        ↓
Bizz AI Application
```

Potential future capabilities:

- Real-time event ingestion
- Automated marketing campaigns
- More sophisticated predictive models
- External CRM integrations
- Advanced recommendation systems
- Larger-scale data processing
- Model monitoring
- Experimentation/A-B testing

These are future extensions and should not complicate the MVP.

---

## 31. Architecture Quality Gate

Before adding a major feature, verify:

### Responsibility

Does the code live in the correct layer?

### Reuse

Can an existing service/component be reused?

### Data ownership

Is there one authoritative source for the calculation?

### Explainability

Can the output be traced back to data or model logic?

### Configuration

Are secrets and provider settings externalized?

### Failure

What happens when the database, model, or LLM is unavailable?

### Scalability

Would the design allow the expensive part to be moved to a worker later?

### Simplicity

Are we adding complexity because the product needs it, or because the technology looks impressive?

---

## 32. Final Architecture Principle

> **Bizz AI should be simple at the surface, structured underneath, and intelligent in the middle.**

The user should experience a calm, coherent business application.

Behind it, the system should maintain clear boundaries between business data, analytics, machine learning, AI interpretation, and presentation.
