# MODEL.md - Data Model Documentation

## Overview

This document describes the normalized data model for the Breathe ESG carbon emissions ingestion system.

**Core Design Principle**: Never lose raw data. Every normalized record is traceable back to its source.

---

## Multi-Tenancy

### Organization

The root entity. Each client company is an `Organization`.

```
Organization
├── id (PK)
├── name (string)
├── created_at (timestamp)
├── updated_at (timestamp)
```

All downstream entities are scoped to an `Organization`. This enables:
- Multi-client deployments
- Data isolation for compliance
- Separate audit trails per client

---

## Data Ingestion & Audit Trail

### DataSource

Tracks **where data came from** - critical for auditors.

```
DataSource
├── id (PK)
├── organization (FK)
├── source_type (enum: SAP, UTILITY, TRAVEL)
├── uploaded_by (FK → User)
├── uploaded_at (timestamp)
├── raw_file_name (string)
├── raw_file_size (int, bytes)
├── total_rows (int)
├── successful_rows (int)
├── failed_rows (int)
├── is_processed (boolean)
```

One `DataSource` = one uploaded file.

This allows us to answer:
- "Which file did row X come from?"
- "Who uploaded it and when?"
- "How many rows failed to normalize?"

### RawRecord

**CRITICAL**: Preserves the original data EXACTLY.

```
RawRecord
├── id (PK)
├── data_source (FK)
├── raw_json (JSON)          ← Store exact original row
├── processing_status (enum: PENDING, NORMALIZED, FAILED, APPROVED, REJECTED)
├── error_message (text, nullable)
├── created_at (timestamp)
├── processed_at (timestamp, nullable)
```

Why store both raw and normalized?
- **Auditor requirement**: "Show me the source of this number"
- **Error correction**: If normalization has a bug, we can re-normalize from raw
- **Compliance**: Never alter the audit trail

Every `EmissionRecord` has a 1:1 relationship to exactly one `RawRecord`.

---

## Scope Classification

All emissions are categorized using GHG Protocol Scopes:

| Scope | Definition | Example |
|-------|-----------|---------|
| **Scope 1** | Direct emissions | Company vehicles, on-site generators |
| **Scope 2** | Indirect (Energy) | Purchased electricity |
| **Scope 3** | Indirect (Other) | Business travel, supplier emissions |

Mapping in the system:

| Source Type | Scope |
|---|---|
| SAP (Fuel) | Scope 1 |
| Utility (Electricity) | Scope 2 |
| Travel (Flights/Hotels) | Scope 3 |

---

## The Main Working Table: EmissionRecord

This is where all analytics happen.

```
EmissionRecord
├── id (PK)
├── organization (FK)
├── raw_record (FK → RawRecord, 1:1)
├── data_source (FK → DataSource)
│
├── === CLASSIFICATION ===
├── scope (enum: SCOPE_1, SCOPE_2, SCOPE_3)
├── category (enum: 20+ categories)
│
├── === ACTIVITY DATA (NORMALIZED) ===
├── activity_date (date)
├── normalized_value (decimal)
├── normalized_unit (string: "liters", "kWh", "km", "nights")
├── original_unit (string: preserved for reference)
│
├── === EMISSIONS CALCULATION ===
├── emission_factor (decimal: kg CO2e per unit)
├── calculated_emissions (decimal: kg CO2e)
│
├── === DATA QUALITY ===
├── confidence_score (float: 0.0-1.0)
├── suspicious_flags (JSON: dict of flags & reasons)
│
├── === REVIEW WORKFLOW ===
├── review_status (enum: PENDING, FLAGGED, APPROVED, REJECTED)
├── review_notes (text, nullable)
├── approved_by (FK → User, nullable)
├── approved_at (timestamp, nullable)
│
├── created_at (timestamp)
├── updated_at (timestamp)
```

### Categories

The system supports 20+ emissions categories:

**Scope 1 (Fuel)**:
- `FUEL_DIESEL`
- `FUEL_PETROL`
- `FUEL_CNG`
- `FUEL_LPG`

**Scope 2 (Electricity)**:
- `ELECTRICITY`

**Scope 3 (Travel)**:
- `TRAVEL_FLIGHT`
- `TRAVEL_HOTEL`
- `TRAVEL_GROUND`

---

## Unit Normalization

All measurements are normalized to **canonical internal units**:

| Category | Canonical Unit | Conversions |
|----------|---|---|
| Fuel | Liters | 1 gallon = 3.78541 L |
| Electricity | kWh | 1 MWh = 1000 kWh |
| Distance | km | 1 mile = 1.60934 km |
| Hotel | nights | (no conversion) |

Example: If SAP exports fuel in gallons and utility sends electricity in MWh, internally we always store liters and kWh. This ensures:
- Consistent comparisons
- No conversion errors in calculations
- Single source of truth for emission factors

---

## Emission Factors

Currently hardcoded in `services/normalizer.py`. In production, these would be externalized to a factor service.

### Fuel (kg CO2e per liter)

```
Diesel: 2.68
Petrol: 2.31
CNG: 1.75
LPG: 1.60
```

### Electricity (kg CO2e per kWh)

```
India Grid Average: 0.71
```

Uses India's grid carbon intensity as default. Configurable per region.

### Travel (kg CO2e per unit)

```
Flight: 0.128 kg CO2e per km
Hotel: 25.0 kg CO2e per night
Ground (car): 0.089 kg CO2e per km
```

Calculations are transparent and can be verified:

```
emissions = normalized_value × emission_factor

Example:
  Activity: 500 liters of diesel
  Factor: 2.68 kg CO2e/liter
  Emissions: 500 × 2.68 = 1,340 kg CO2e
```

---

## Data Quality & Suspicious Detection

### Confidence Score

Each record gets a `confidence_score` (0.0-1.0) based on data quality.

**Critical flags** (reduce score to 0.5):
- Missing distance for flights/ground travel
- Missing meter ID for electricity
- Unknown plant code for SAP

**Warning flags** (reduce by 0.1 each):
- Negative quantities
- Unusually large values (>10x average)
- Missing supplier information
- Very long billing periods

Example:
```
Base score: 1.0
Missing supplier: -0.1
Unknown plant: → 0.5 (critical)
Final: 0.5
```

Analysts can use confidence score to prioritize review work.

### Suspicious Flags

Each record stores WHY it was flagged:

```json
{
  "missing_supplier": true,
  "unknown_plant": true
}
```

The `review_queue` UI highlights these for analyst attention.

---

## Review Workflow

### Review Statuses

```
PENDING    → Newly normalized, awaiting review
FLAGGED    → Marked suspicious, needs attention
APPROVED   → Analyst approved, locked for audit
REJECTED   → Analyst rejected the record
```

Workflow:
```
RawRecord
  ↓
Parsed
  ↓
Normalized EmissionRecord (PENDING)
  ↓ [Analyst Review]
  ├→ APPROVED (locked for audit)
  └→ REJECTED (data returned to source)
```

### ReviewHistory

Every state change is logged:

```
ReviewHistory
├── emission_record (FK)
├── action (enum: CREATED, FLAGGED, APPROVED, REJECTED, EDITED)
├── performed_by (FK → User)
├── performed_at (timestamp)
├── notes (text: "Why did you do this?")
├── changes (JSON: what changed)
```

This creates a complete audit trail for compliance.

---

## Indexes & Performance

Key queries are indexed:

```python
# Find records needing review
INDEX: (organization, review_status)
INDEX: (organization, scope, review_status)

# Time-series queries
INDEX: (organization, activity_date)

# Raw record lookup
INDEX: (data_source, processing_status)
```

This allows fast queries for:
- Dashboard: "How many pending approvals?"
- Analytics: "Total emissions by scope in Q1?"
- Audit: "All records from source X?"

---

## Data Lineage Example

**Question**: "Show me where emissions value 1,340 kg CO2e came from."

**Answer**:
```
EmissionRecord #42
├── normalized_value: 500
├── normalized_unit: liters
├── emission_factor: 2.68
├── calculated_emissions: 1,340 kg CO2e
│
└── raw_record (OneToOne)
    ├── raw_json: {
    │     "Belegdatum": "12.03.2025",
    │     "Materialgruppe": "Diesel",
    │     "Menge": 500,
    │     "Einheit": "L",
    │     "Werk": "BLR01"
    │   }
    └── data_source (FK)
        ├── source_type: "SAP"
        ├── uploaded_by: User(id=5, name="Alice")
        ├── uploaded_at: 2025-03-15 10:30 AM
```

Complete chain of custody from upload → normalization → approval → audit.

---

## Summary: Why This Model

✅ **Multi-tenant**: Multiple clients, data isolation  
✅ **Auditable**: Raw data never deleted, complete history  
✅ **Normalized**: All units standardized internally  
✅ **Quality-aware**: Confidence scores, suspicious flags  
✅ **Reviewable**: Analyst workflow with approval gates  
✅ **Performant**: Strategic indexes for common queries  
✅ **Compliant**: Scope 1/2/3 classification standard  
✅ **Transparent**: Every number is traceable to source  
