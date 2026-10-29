# 101 live adversarial browser plan

## Application Overview

Real 101 commerce application on disposable PostgreSQL. Native browser scenarios exercise actual HTTP, delayed or dropped real responses, operator capability boundaries and missing recovery features. No external destinations or mocked API bodies.

## Test Scenarios

### 1. Live catalog and adversarial checkout

**Seed:** `tests/seed.spec.ts`

#### 1.1. catalog cart text remains available

**File:** `tests/agent-catalog.spec.ts`

**Steps:**
  1. Open the live seeded catalog
    - expect: The application renders available products from its actual API
  2. Click Agregar for Papas de la casa
    - expect: Cart contains the product
    - expect: No order has been submitted

#### 1.2. failure and permission scenarios

**File:** `tests/reliability.spec.ts`

**Steps:**
  1. Execute the eleven exact live failure/permission scenarios in specs/adversarial.md, plus the seed catalog readiness check
    - expect: No duplicates, stale destinations, unauthorized business access or lost durable intent
    - expect: Missing recovery and staff isolation stay failures rather than skipped tests
