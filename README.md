# Remote Career Navigator

## AI International Career Copilot

> Convierte tu experiencia local en una carrera internacional.

---

# 1. Concepto del producto

**Remote Career Navigator** es una plataforma de inteligencia artificial orientada a profesionales LATAM que buscan empleos internacionales remotos y tienen dificultades para interpretar ofertas en inglés, evaluar su compatibilidad profesional y preparar postulaciones.

La plataforma no sería simplemente un job board.

Su propuesta de valor sería:

> **No solamente encuentra trabajos → convierte una oportunidad internacional en una postulación viable.**

### Problemas que resuelve

* Dificultad para encontrar trabajos internacionales compatibles con LATAM.
* Dificultad para leer ofertas laborales en inglés.
* Desconocimiento del salario internacional adecuado.
* CV poco adaptado al mercado internacional.
* Dificultad para determinar si realmente se cumplen los requisitos.
* Dificultad para comunicarse con recruiters.
* Falta de preparación para entrevistas internacionales.
* Falta de seguimiento de múltiples postulaciones.

---

# 2. Público objetivo

## Primer nicho

Profesionales tecnológicos senior de Latinoamérica que buscan trabajar remotamente para empresas internacionales.

Especialmente:

* Software Engineers
* Solution Architects
* Application Architects
* Enterprise Architects
* Cloud Architects
* Technical Leads
* Engineering Managers
* DevOps Engineers
* Data Engineers
* Technical Consultants

### Perfil inicial recomendado

El MVP podría enfocarse inicialmente en:

> **Senior Technology Professionals LATAM → International Remote Jobs**

---

# 3. Propuesta de valor

La plataforma acompaña al candidato durante todo el proceso:

```text
Perfil profesional
       ↓
Descubrimiento de oportunidades
       ↓
Análisis de oferta
       ↓
Compatibilidad
       ↓
Explicación en español
       ↓
Adaptación del CV
       ↓
Postulación
       ↓
Preparación para entrevista
       ↓
Seguimiento
```

---

# 4. Flujo principal del usuario

```text
                    ┌──────────────────┐
                    │     REGISTRO     │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │ PERFIL PROFESIONAL│
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │ MOTOR DE PERFIL  │
                    │ Skills           │
                    │ Seniority        │
                    │ Experience       │
                    └────────┬─────────┘
                             ↓
              ┌──────────────────────────────┐
              │       JOB DISCOVERY          │
              │ Job Boards / APIs / Careers  │
              └──────────────┬───────────────┘
                             ↓
                    ┌──────────────────┐
                    │ JOB ANALYZER      │
                    │ Requirements      │
                    │ Salary            │
                    │ Location          │
                    │ English           │
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │   MATCH SCORE     │
                    │    0 ── 100      │
                    └────────┬─────────┘
                             ↓
                 ┌───────────┴───────────┐
                 ↓                       ↓
          ALTA COMPATIBILIDAD       BAJA COMPATIBILIDAD
                 ↓
          ┌───────────────┐
          │ APPLICATION   │
          │ COPILOT       │
          └───────┬───────┘
                  ↓
        ┌─────────────────────┐
        │ CV personalizado    │
        │ Cover Letter        │
        │ Recruiter Message   │
        └──────────┬──────────┘
                   ↓
          ┌─────────────────┐
          │ INTERVIEW COACH │
          └────────┬────────┘
                   ↓
          ┌─────────────────┐
          │ APPLICATION CRM │
          └─────────────────┘
```

---

# 5. Módulos funcionales

## 5.1 Professional Profile

El usuario puede cargar:

* CV PDF
* CV DOCX
* LinkedIn
* Portfolio
* Certificaciones

La IA extrae:

```text
Nombre
Profesión
Senioridad
Años de experiencia
Roles
Empresas
Industrias
Skills
Tecnologías
Certificaciones
Idiomas
País
Disponibilidad
Expectativa salarial
Preferencias laborales
```

### Professional Profile Graph

El perfil se representa como un grafo de capacidades.

```text
                    Candidate
                       │
          ┌────────────┼────────────┐
          │            │            │
    Architecture      Cloud      Integration
          │            │            │
    ┌─────┼─────┐      │       ┌────┼────┐
    │     │     │      │       │    │    │
Application Solution Enterprise AWS Azure APIs Events
```

Esto permite realizar matching semántico entre el candidato y las ofertas.

---

# 6. Job Discovery

El sistema obtiene oportunidades desde diferentes fuentes.

## Fuentes potenciales

* Job Boards
* Career Pages
* Greenhouse
* Lever
* Workable
* APIs de empleo
* Fuentes permitidas de terceros

### Consideración importante

No se debería comenzar con scraping indiscriminado de LinkedIn.

Existen riesgos relacionados con:

* Terms of Service
* CAPTCHAs
* bloqueos
* cambios de HTML
* mantenimiento
* restricciones de automatización

El MVP debería priorizar APIs y fuentes permitidas.

---

# 7. Job Analyzer

Cuando el usuario encuentra una oferta, el sistema la analiza.

### Ejemplo

```text
Senior Solution Architect
Remote — USA

Salary:
USD 120k–150k

Experience:
7+ years

Cloud:
AWS

Architecture:
Required

English:
Advanced
```

La plataforma genera un resumen:

### ¿Qué está buscando realmente la empresa?

```text
Architecture       ██████████ 95%
Cloud              ████████   80%
Integration        █████████  90%
Leadership         ████████   80%
English            ██████████ 95%
```

---

# 8. English Intelligence

Esta funcionalidad es uno de los principales diferenciadores del producto.

No se limita a traducir.

La plataforma explica el significado profesional de la oferta.

### Ejemplo

**Texto:**

> "We are looking for someone who can drive architectural decisions."

### Explicación:

> "Drive architectural decisions" significa que esperan que la persona pueda **tomar, defender y liderar decisiones de arquitectura**, no simplemente documentarlas.

---

## English Difficulty Score

```text
Reading              🟡 Intermediate
Technical vocabulary 🟢 Good
Interview English    🔴 Needs preparation
```

También se puede ofrecer:

> **"Explícame esta oferta como si mi inglés fuera básico."**

---

# 9. Match Engine

El sistema calcula un score de compatibilidad.

## Ejemplo

```text
Match Score: 84/100
```

### Factores

```text
Technical Skills       25%
Experience             20%
Seniority              15%
Architecture           10%
Industry               10%
Location               10%
Language               10%
```

### Resultado

```text
Technical Skills       92%
Experience             88%
Architecture           95%
Industry               70%
English                60%
Location              100%
```

### Explicación generada por IA

**Strengths**

* Application Architecture
* Integration
* Enterprise environments
* Technical leadership

**Gaps**

* AWS certification preferred
* English communication
* Fintech experience

---

# 10. Regla fundamental del Match Engine

El LLM no debe ser la única fuente de verdad.

Se recomienda una arquitectura híbrida.

## Deterministic Logic

Usar reglas determinísticas para:

* años de experiencia
* ubicación
* salario
* requisitos obligatorios
* autorización laboral
* seniority
* tecnologías específicas

## AI Logic

Utilizar IA para:

* semantic matching
* interpretación de requisitos
* explicación
* traducción
* clasificación
* análisis contextual

---

# 11. Application Copilot

Cuando el usuario selecciona:

> **Quiero postular**

el sistema genera materiales personalizados.

### Componentes

```text
Job Requirements
        ↓
Candidate Evidence
        ↓
CV Adaptation
        ↓
Cover Letter
        ↓
Recruiter Message
```

---

# 12. Protección contra información inventada

La IA nunca debería inventar experiencia.

Ejemplo:

### Job Requirement

> Experience designing API architectures.

### Candidate Evidence

> Experiencia diseñando integraciones mediante APIs.

### Output permitido

> Designed API-based integration architectures across enterprise applications.

Pero únicamente si existe evidencia en el perfil.

---

# 13. Recruiter Copilot

Generación de mensajes personalizados para recruiters.

Ejemplo:

```text
Hi Sarah,

I noticed you're recruiting for a Senior Solution Architect
position. My background includes application, solution and
enterprise architecture within multinational environments.

The role looks closely aligned with my experience.

I'd be happy to connect and discuss the opportunity.
```

El sistema también debería proporcionar:

> **Explícame en español qué estoy enviando.**

---

# 14. Interview Coach

El sistema conoce:

* CV del candidato
* Job Description
* Empresa
* Skills requeridos
* Seniority
* Arquitectura solicitada

Entonces genera preguntas específicas.

### Ejemplo

> Tell me about a complex architecture decision you made.

El usuario puede responder primero en español.

```text
Respuesta en español
        ↓
Traducción profesional
        ↓
Inglés simplificado
        ↓
Versión senior
        ↓
Pronunciación
        ↓
Feedback
```

---

# 15. Niveles de respuesta

## Nivel 1 — Simple English

> I designed the architecture for the integration platform.

## Nivel 2 — Professional English

> I was responsible for designing the architecture of the integration platform.

## Nivel 3 — Senior / Executive English

> From an architectural perspective, I evaluated the main integration patterns and selected the approach that best balanced scalability, maintainability and business requirements.

---

# 16. Application CRM

Dashboard para controlar todas las oportunidades.

```text
Company       Position                Status
--------------------------------------------------
Company A     Solution Architect      Interview
Company B     Application Architect   Applied
Company C     Cloud Architect         Recruiter
Company D     Enterprise Architect    Rejected
```

### Estados

```text
Saved
Analyzing
Ready to Apply
Applied
Recruiter Contacted
Interview
Technical Interview
Final Interview
Offer
Rejected
Withdrawn
```

---

# 17. International Employability Score

Una funcionalidad estratégica.

El sistema genera un score global:

```text
International Employability Score
                72/100
```

### Componentes

```text
Technical Profile      88
Architecture           91
Experience             85
English                57
International CV       64
Interview Readiness    59
Remote Compatibility   90
```

El objetivo no es solamente decir:

> "Este trabajo es bueno para ti."

Sino:

> **"Esto es lo que actualmente te impide acceder a trabajos de USD 8,000 mensuales."**

---

# 18. Arquitectura técnica — MVP

No empezar con microservicios.

Una arquitectura modular monolith es suficiente.

```text
                     ┌───────────────┐
                     │   Web / PWA   │
                     │    Angular    │
                     └───────┬───────┘
                             │
                        HTTPS / REST
                             │
                     ┌───────▼───────┐
                     │ API / Backend │
                     │    FastAPI    │
                     └───────┬───────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
       PostgreSQL       Redis / Queue    Object Storage
            │
            ▼
         pgvector
```

---

# 19. Backend

## Tecnología propuesta

**Python + FastAPI**

Razones:

* integración sencilla con LLMs
* NLP
* embeddings
* document processing
* scoring
* AI pipelines
* APIs REST
* rapidez de desarrollo

---

# 20. Frontend

## Tecnología

**Angular + TypeScript**

Responsabilidades:

* Dashboard
* Profile
* Job Explorer
* Job Analysis
* Match Score
* Application Manager
* Interview Coach

---

# 21. Database

## PostgreSQL

Usar PostgreSQL para:

* usuarios
* perfiles
* experiencias
* skills
* jobs
* aplicaciones
* entrevistas
* scoring

## pgvector

Utilizar pgvector para búsqueda semántica.

```text
Candidate Embedding
        ↕
Semantic Similarity
        ↕
Job Embedding
```

---

# 22. AI Architecture

No enviar todo directamente a un LLM.

```text
                  ┌───────────────┐
                  │   AI Gateway  │
                  └───────┬───────┘
                          │
          ┌───────────────┼────────────────┐
          ↓               ↓                ↓
   Profile LLM       Job LLM        Interview LLM
          │               │                │
          └───────────────┼────────────────┘
                          ↓
                  Validation Layer
                          ↓
                    Application DB
```

---

# 23. AI Services

Separar responsabilidades:

```text
Profile Analyzer
Job Analyzer
Translation Service
Job Matcher
CV Tailor
Recruiter Assistant
Interview Coach
English Coach
```

Esto permite cambiar de modelo sin modificar toda la aplicación.

---

# 24. Model Gateway

Se recomienda utilizar una capa de abstracción:

```text
Application
     ↓
   AI Gateway
     ↓
 ┌───┼──────────┐
 ↓   ↓          ↓
LLM1 LLM2      LLM3
```

Ventajas:

* evitar lock-in
* controlar costos
* cambiar modelos
* fallback
* observabilidad
* rate limiting

---

# 25. Event-driven Architecture

Cuando la plataforma crezca:

```text
Job Discovered
      ↓
job.created
      ↓
job.normalized
      ↓
job.analyzed
      ↓
match.calculated
      ↓
notification.created
```

Para MVP:

* Redis
* Celery

Para mayor escala:

* Kafka
* AWS EventBridge
* SNS/SQS

---

# 26. Arquitectura evolucionada

```text
                         CDN
                          │
                         WAF
                          │
                    API Gateway
                          │
             ┌────────────┴────────────┐
             │                         │
       Application API             AI Gateway
             │                         │
      ┌──────┼──────┐           ┌──────┼──────┐
      ↓      ↓      ↓           ↓      ↓      ↓
   Profile  Jobs  Applications LLM    RAG  Embeddings
   Service Service   Service
      │      │      │
      └──────┼──────┘
             ↓
        PostgreSQL
             │
       ┌─────┴─────┐
       ↓           ↓
    pgvector      Redis
```

---

# 27. Bounded Contexts

Una evolución arquitectónica podría separar el dominio en:

```text
Identity
Profile
Career
Job Discovery
Job Analysis
Matching
Application
Interview
AI
Notification
Billing
```

### Dependencias principales

```text
Identity
   ↓
Profile
   ↓
Matching ← Job
   ↓
Application
   ↓
Interview
```

---

# 28. Data Model

```text
User
 │
 ├── Profile
 │    ├── Experience
 │    ├── Skills
 │    ├── Education
 │    └── Languages
 │
 ├── Documents
 │
 ├── JobMatches
 │      └── Job
 │
 ├── Applications
 │
 └── Interviews
```

### Job

```text
Job
 ├── Company
 ├── Location
 ├── Salary
 ├── Requirements
 ├── Technologies
 ├── Language
 └── RemotePolicy
```

---

# 29. Seguridad

El sistema manejará información profesional y documentos privados.

Desde el MVP:

* OAuth/OIDC
* HTTPS
* encryption at rest
* secrets management
* RBAC
* audit logs
* tenant isolation
* secure sessions
* document deletion
* consent management

### AI Data Privacy

Los CVs y datos de los usuarios no deben utilizarse para entrenar modelos sin consentimiento explícito.

---

# 30. Cloud Architecture

Una primera implementación podría utilizar AWS.

## Servicios

```text
CloudFront
    │
    ↓
AWS WAF
    │
    ↓
API Gateway
    │
    ↓
ECS / Fargate
    │
    ├── FastAPI
    │
    ├── Celery
    │
    └── Workers
          │
          ├── RDS PostgreSQL
          ├── ElastiCache Redis
          └── S3
```

### AI

```text
FastAPI
   ↓
AI Gateway
   ↓
LLM Provider
```

El proveedor concreto debería mantenerse desacoplado.

---

# 31. Observabilidad

Desde el comienzo:

### Logs

* application logs
* security logs
* AI requests
* errors

### Metrics

* job ingestion rate
* match latency
* LLM latency
* token usage
* cost per analysis
* application conversion rate

### Tracing

OpenTelemetry.

---

# 32. Métricas de producto

Las métricas más importantes serían:

### Acquisition

```text
Visitors
Signups
Profile Completion
```

### Engagement

```text
Jobs analyzed
CVs generated
Applications created
Interview sessions
```

### Conversion

```text
Profile → Application
Application → Interview
Interview → Offer
```

### Business

```text
Free → Pro conversion
Monthly recurring revenue
Customer acquisition cost
Customer lifetime value
```

---

# 33. MVP

No intentar construir todo inicialmente.

## MVP v1

### 1. Professional Profile

* CV upload
* CV parsing
* skills extraction
* experience extraction

### 2. Job Analyzer

* Job Description input
* translation
* requirements extraction
* salary extraction

### 3. Match Engine

* compatibility score
* strengths
* gaps

### 4. English Explainer

* translation
* simplified English
* vocabulary explanation

### 5. Application Copilot

* customized CV
* cover letter
* recruiter message

### 6. Application Tracker

* saved jobs
* applications
* interview status

---

# 34. MVP User Journey

```text
1. User creates account
        ↓
2. Uploads CV
        ↓
3. AI creates professional profile
        ↓
4. User pastes job description
        ↓
5. System analyzes job
        ↓
6. System generates Match Score
        ↓
7. System explains job in Spanish
        ↓
8. User selects "Apply"
        ↓
9. AI generates tailored CV
        ↓
10. AI generates recruiter message
        ↓
11. User applies
        ↓
12. Application enters CRM
        ↓
13. User practices interview
        ↓
14. User receives offer
```

---

# 35. Product Roadmap

## Sprint 1 — Foundation

* Authentication
* User profile
* CV upload
* PDF/DOCX parser
* PostgreSQL

## Sprint 2 — AI Profile

* CV extraction
* Skills extraction
* Experience normalization
* Professional profile

## Sprint 3 — Jobs

* Job ingestion
* Job normalization
* Duplicate detection
* Job database

## Sprint 4 — Matching

* Embeddings
* Deterministic scoring
* AI explanation

## Sprint 5 — Application

* CV tailoring
* Cover letter
* Recruiter message

## Sprint 6 — English

* Job translation
* Vocabulary explanation
* Simplified English

## Sprint 7 — Interview

* Interview simulator
* Answer evaluation
* Personalized questions

## Sprint 8 — Dashboard

* Applications
* Pipeline
* Metrics
* Notifications

---

# 36. Business Model

## Free

* 10 job analyses/month
* Basic matching
* Basic translation

## Pro

**USD 15–25/month**

Incluye:

* Unlimited job analysis
* Personalized CV
* Recruiter messages
* Interview preparation
* Advanced matching

## Premium

**USD 40–70/month**

Incluye:

* Advanced interview coach
* Career roadmap
* Salary analysis
* Application automation
* English coaching

---

# 37. B2B Opportunity

A largo plazo existe una segunda línea de negocio:

## LATAM Talent Acquisition

Empresas internacionales podrían utilizar la plataforma para identificar profesionales LATAM compatibles con posiciones internacionales.

```text
Company
   ↓
Job Description
   ↓
AI Matching
   ↓
LATAM Talent Pool
   ↓
Candidate Ranking
   ↓
Recruiter
```

El modelo B2B puede tener un potencial económico mayor que el B2C.

---

# 38. Diferenciador estratégico

El producto no debería competir directamente con LinkedIn como job board.

El posicionamiento sería:

> **LinkedIn encuentra oportunidades. Remote Career Navigator ayuda al candidato a convertirlas en oportunidades reales.**

### Diferenciadores

1. Traducción contextual.
2. Explicación de ofertas.
3. Matching basado en evidencia.
4. CV internacional personalizado.
5. Recruiter Copilot.
6. Interview Coach.
7. English Coach.
8. International Employability Score.
9. Salary intelligence.
10. Application CRM.

---

# 39. Posicionamiento inicial

## Nombre

**Remote Career Navigator**

## Categoría

**AI International Career Copilot**

## Target

**LATAM Senior Technology Professionals**

## Promesa

> **Convierte tu experiencia local en una carrera internacional.**

## Problema principal

> Profesionales técnicamente capaces que no logran acceder a oportunidades internacionales porque tienen dificultades con el idioma, el posicionamiento profesional o el proceso de búsqueda.

---

# 40. Caso de uso inicial

Un arquitecto de software de Perú tiene experiencia suficiente para ganar:

> **USD 5,000–8,000+/mes**

pero tiene dificultades para:

* leer ofertas en inglés
* identificar cuáles realmente le corresponden
* saber cuánto pedir
* adaptar su CV
* contactar recruiters
* responder entrevistas en inglés

La plataforma convierte:

```text
Experiencia profesional
        +
Oferta internacional
        +
AI
        ↓
Oportunidad de contratación
```

---

# 41. Arquitectura recomendada para empezar

No construiría microservicios desde el día uno.

### Stack inicial

```text
Frontend
Angular + TypeScript

Backend
Python + FastAPI

Database
PostgreSQL

Vector Search
pgvector

Cache / Queue
Redis

Workers
Celery

Storage
AWS S3

Cloud
AWS

AI
LLM Gateway + configurable providers

Observability
OpenTelemetry
```

### Estilo arquitectónico

> **Modular Monolith + Event-Driven Internal Architecture**

Esto permite comenzar rápidamente sin perder una ruta clara hacia microservicios si el producto alcanza escala.

---

# 42. Evolución arquitectónica

```text
                    MVP
                     │
                     ↓
            Modular Monolith
                     │
                     ↓
              Product-Market Fit
                     │
                     ↓
             High Traffic / Scale
                     │
                     ↓
             Extract Services
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
     Job Service  AI Service  Matching
        │            │            │
        └────────────┼────────────┘
                     ↓
              Event Platform
```

La regla sería:

> **No distribuir el sistema porque "microservices is best practice". Distribuirlo cuando exista una razón de negocio o escalabilidad.**

---

# 43. Visión a largo plazo

El producto puede evolucionar de:

```text
Job Search Tool
```

a:

```text
AI Career Platform
```

y eventualmente:

```text
International Talent Infrastructure
```

El roadmap conceptual sería:

```text
Phase 1
Job Discovery
        ↓
Phase 2
Career Copilot
        ↓
Phase 3
Interview & English Coach
        ↓
Phase 4
Talent Marketplace
        ↓
Phase 5
International Talent Platform
```

---

# 44. Hipótesis principal del producto

La hipótesis que habría que validar antes de construir demasiado es:

> **¿Los profesionales senior LATAM están dispuestos a pagar por una herramienta que traduzca, evalúe y prepare oportunidades internacionales específicamente para su perfil?**

El MVP debe validar esta hipótesis antes de invertir en una arquitectura compleja.

---

# 45. Métrica North Star

Una posible North Star Metric:

> **Qualified International Applications**

Es decir:

> Número de postulaciones internacionales en las que el candidato tiene alta compatibilidad y realmente termina postulando.

Esto es mejor que medir solamente:

* número de usuarios
* número de traducciones
* número de jobs vistos

porque mide el verdadero resultado del producto.

---

# 46. Resultado final esperado

El objetivo de Remote Career Navigator no es:

> "Encontrar empleos."

El objetivo es:

> **Ayudar a profesionales LATAM a transformar su experiencia profesional en oportunidades internacionales mejor remuneradas.**

```text
LOCAL EXPERIENCE
       ↓
PROFESSIONAL PROFILE
       ↓
INTERNATIONAL MARKET
       ↓
AI MATCHING
       ↓
APPLICATION
       ↓
INTERVIEW
       ↓
INTERNATIONAL JOB
       ↓
HIGHER INCOME
```
