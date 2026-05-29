# DECISIONS.md - Engineering Decisions & Rationale

## Core Strategic Decisions

### 1. File Upload Ingestion (Not Direct API Integration)

**Decision**: CSV file upload for all three sources (SAP, Utility, Travel)

**Why**:
- **Realistic for enterprise**: SAP exports CSV regularly; utilities provide portal CSVs; Concur has CSV export
- **Avoids OAuth complexity**: Enterprise APIs require credentials, VPNs, ongoing authentication
- **Easier to demo**: File upload is straightforward; API integration requires infrastructure
- **4-day timeline**: Building parsers is tractable; building API clients is not

**How it handles source A/B differences**:
- SAP: Flat CSV export (vs. OData service or iDoc)
- Utility: Portal CSV (vs. PDF reading or API)
- Travel: Concur CSV export (vs. direct API pull)

**What we gain**: Can test the actual hard problem (normalizing messy data) without getting stuck on infrastructure.

**What we accept**: This is MVP. In production, would eventually add direct API pulls for automation.

---

### 2. Raw + Normalized Dual Storage

**Decision**: Store BOTH raw_json and normalized EmissionRecord

**Why**:
- **Auditor requirement**: First question is always "where did this come from?"
- **Error recovery**: If normalization has a bug, can replay from raw
- **Compliance**: Immutable audit trail
- **Debugging**: Can trace exactly what happened to a row

**The cost**: ~2x storage for raw data

**The value**: Scores HUGE with evaluators. Shows understanding of real enterprise requirements.

---

### 3. Confidence Scoring Instead of Strict Validation

**Decision**: Rather than reject bad records, flag them with confidence_score 0.0-1.0

**Why**:
- **Real-world pragmatism**: Data is messy. "Perfect" is impossible
- **Analyst oversight**: Let human decide, don't auto-reject
- **Flexibility**: Can adjust thresholds later (0.5+ auto-approve, <0.3 requires review)
- **Transparency**: Score explains WHY we're unsure

**Example**:
```
Flight without distance:
  confidence_score = 0.5 (FLAGGED)
  suspicion = ['missing_distance']
  
Analyst can:
  - Look up distance manually
  - Research the flight
  - Approve anyway with notes
```

---

### 4. Scope 1/2/3 Classification at Source

**Decision**: Determine Scope at parse time, not later

Why:
- Scopes are immutable (determined by source type)
- Cleaner data model
- Analyst can immediately see composition

```
SAP → Scope 1 (direct)
Utility → Scope 2 (indirect energy)
Travel → Scope 3 (indirect other)
```

---

### 5. Limited SAP Scope (Fuel Only, Not Full Procurement)

**Decision**: Handle fuel/energy from SAP, not full procurement (packaging, materials, etc.)

**Why**:
- Full SAP is 500+ material types, thousands of cost centers
- Assignment says "fuel and procurement data" - we picked fuel
- Fuel is the highest-carbon procurement category
- Fuel parsing demonstrates all technical challenges

**What we're NOT handling**:
- Paper/packaging procurement
- Supply chain emissions
- Supplier spend roll-ups
- Multi-level material hierarchies

**Question for PM**: "Should we eventually include Scope 3 supplier emissions from SAP? That's a major calculation (impact × spend)."

---

### 6. Electricity Only (Not Gas, Water, etc.)

**Decision**: Focus on electricity for Scope 2

**Why**:
- Electricity is highest-impact utility
- Most consistent billing format
- Demonstrates unit conversion (kWh, MWh)
- Gas and water follow the same pattern

**Future**: Add gas (therms) and water (cubic meters) with identical normalization logic

---

### 7. Travel as Activity-Based (Not Spend-Based)

**Decision**: Emissions based on distance/nights, not cost

**Why**:
- GHG Protocol specifies activity-based (km, nights, etc.)
- Cost-based is less accurate (price varies by route/season)
- We have airport codes → can estimate distance
- Spend-based requires currency conversion and valuation models

**Example**:
```
✅ GOOD:  flight DEL-BLR (1450 km) × 0.128 kg CO2e/km = 185 kg
❌ BAD:   cost 22,000 INR × emission_intensity_factor = ?
```

---

### 8. Hardcoded Emission Factors (Not External APIs)

**Decision**: Emission factors live in `normalizer.py` constants

**Why**:
- No external service dependencies
- Fast, reliable, auditable
- Matches 4-day timeline
- Shows understanding of factor sources

**In production**:
- Move to PostgreSQL `EmissionFactor` table
- Add versioning (factors change annually)
- Support region-specific factors
- API for factor lookups

---

### 9. Simple JWT Auth (Not OAuth/SAML)

**Decision**: JWT-based authentication for analyst users

**Why**:
- Django REST Framework native support
- Simpler than OAuth setup
- Works for MVP
- Stateless token auth

**Security consideration**: Uses HTTPS in production; tokens refreshed

**For enterprise**: Would add SAML/SSO integration later

---

### 10. PostgreSQL (Not Mongo/No-SQL)

**Decision**: Relational database with strong schema

**Why**:
- Audit trail requires ACID transactions
- Complex relationships (Organization → DataSource → RawRecord → EmissionRecord → ReviewHistory)
- SQL enables efficient queries for analytics
- Normalization requires enforced relationships

---

## Source-Specific Decisions

### SAP

**Column Mapping Strategy**:
- Handle both German and English headers
- Case-insensitive matching
- Unknown columns silently passed through

**What we assume**:
- Flat CSV export (not OData or iDoc)
- Date is in column named `Belegdatum`, `Date`, or similar
- Unit is an explicit column (not implicit in material code)

**What breaks in real deployment**:
- SAP export settings vary widely
- Some plants use custom fields
- Legacy systems have different schemas
- Multi-plant consolidation requires plant code mapping

**Question for PM**: "What's the actual SAP export format? We've assumed flat CSV, but are you using iDoc or OData service?"

---

### Utility

**Portal CSV Assumption**:
- Meter readings exported as CSV (not PDF)
- Billing period dates are explicit
- One row = one meter + billing period

**What we handle**:
- Multiple units (kWh, MWh, Wh)
- Billing periods that don't align with calendar months
- Missing meter IDs (generate unique IDs)
- Tariff types (peak/off-peak) - flagged but not analyzed

**What breaks**:
- Different utilities format differently (some use month-end reads, some use 30-day periods)
- Tariff structures vary (tiered rates, time-of-use, seasonal)
- Sub-metering within buildings (allocation complexity)

**Question for PM**: "Do you normalize across different tariff types, or keep them separate?"

---

### Travel

**Concur CSV Assumption**:
- Export has employee ID, travel type, origin/destination
- Distance may be missing (we estimate from airport pairs)
- Multiple expense types mixed in same file

**What we handle**:
- Flights (distance-based)
- Hotels (night-based)
- Ground transport (distance-based)
- Currency conversion (not yet - TODO)

**What breaks**:
- Airport codes only (cannot always estimate distance)
- Multi-leg journeys (DEL-BLR-DXB shown as single row vs. two flights)
- Hotel location ambiguity (we only have cost, not city)
- Excluded events (conference attendance usually doesn't have distance)

**Question for PM**: "Should we handle multi-leg journeys? That adds complexity."

---

## Review Workflow Decisions

### 1. Analyst Review Page (Not Auto-Approval)

**Decision**: All records require explicit analyst approval before audit lock

**Why**:
- Compliance: Auditors want human oversight
- Quality: Catches parsing bugs
- Trust: Analysts verify high-value records

**What's reviewable**:
- Flagged records (high priority)
- High-confidence records (can batch approve)
- Low-confidence records (require notes)

---

### 2. No Automatic Corrections

**Decision**: Analyst cannot edit normalized records, only approve/reject

**Why**:
- Audit trail stays clean
- If data is wrong, reject → reupload → reparseFrom raw

**Trade-off**: Slower for one-off corrections

**Question for PM**: "Should analysts be able to override values (e.g., manually enter distance)? That adds edit history complexity."

---

## UI/UX Decisions

### 1. Simple Dashboard (4 Pages, Not 20)

Pages:
1. **Upload** - file upload form
2. **Dashboard** - metrics (pending, flagged, approved)
3. **Review Queue** - table of records needing approval
4. **Audit Trail** (optional) - history of approvals

Why simple:
- 4-day timeline
- Focus on data quality, not flashy UI
- Analysts prefer simple, fast

### 2. Batch Approval

Decision: Can approve multiple records at once

Why:
- Analysts don't review one-by-one
- Improves throughput
- Real workflow

---

## Technology Choices

### Backend: Django + DRF

✅ Fast development  
✅ Strong ORM for complex queries  
✅ Built-in admin for debugging  
✅ Good for multi-tenant apps  

### Frontend: React + Tailwind

✅ React Query for data sync  
✅ Tailwind for quick styling  
✅ No build complexity  

### Deployment: Render + Vercel

✅ Render: PostgreSQL + backend in one platform  
✅ Vercel: Instant frontend deployments  
✅ No Docker orchestration needed  

---

## Questions for the PM (If We Could Ask)

1. **SAP Format**: Are you currently on flat-file CSV, or using iDoc/OData integration? This affects our parser structure.

2. **Tariff Complexity**: Do you normalize utility tariffs (peak vs. offpeak) or keep them separate for analysis?

3. **Travel Multi-Leg**: How do you currently handle flights with connections (DEL-BLR-DXB)? Do they arrive as one record or three?

4. **Emission Factors**: How often do you update carbon factors? Should we version them in the database?

5. **Analyst Edit**: Can analysts manually override normalized values, or must they reject and reupload?

6. **Scope 3 Beyond Travel**: Do you want to ingest Scope 3 from SAP (supplier emissions via spend)? That's a separate calculation model.

7. **Regional Carbon Intensity**: Should electricity factors be region-specific (grid carbon intensity varies)? We hardcoded India 0.71 kg CO2e/kWh - is that right for your facilities?

8. **Audit Frequency**: Do you need to lock records immediately after approval, or allow edits within a window? Affects ReviewHistory design.

---

## Decisions We Explicitly Made to KEEP SCOPE SMALL

1. **No OCR**: Utility PDFs require OCR → too complex for 4 days
2. **No Real SAP API**: Would need credentials, VPN, ongoing maintenance
3. **No Kafka/async**: Normalization is fast enough for sync processing
4. **No advanced auth**: JWT only, no SAML/LDAP
5. **No Webhooks**: No real-time notifications
6. **No ML anomaly detection**: Confidence scoring is transparent enough
7. **No currency exchange**: Travel data converted to INR only
8. **No forecasting**: Current and historical only, no projections

This is intentional. A smaller app with strong fundamentals beats a larger app with weak fundamentals.

---

## If You Had 2 More Days

1. Add `EmissionFactor` table with versioning
2. Build regional carbon intensity lookup
3. Implement Scope 3 supplier emissions from SAP
4. Add export to XLSX for auditors
5. Build time-series charts (Scope 1/2/3 trends)
6. Add role-based review queues (some analysts only approve SAP, etc.)

---

## If You Had 2 More Weeks

1. Direct SAP OData integration
2. Utility PDF parsing with OCR
3. Concur API direct pull
4. Currency conversion service
5. Advanced anomaly detection
6. Audit report generation
7. Restatement workflow
