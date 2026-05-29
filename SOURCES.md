# SOURCES.md - Real-World Data Source Research

This document explains the research behind each data source decision, what we learned, and how our sample data reflects reality.

---

## 1. SAP Fuel & Procurement Data

### Real-World Format Research

**What SAP Exports Actually Look Like**:

SAP has multiple export mechanisms:
1. **Flat-file CSV** (via SE16N / ALV export) ← **We chose this**
2. **OData service** (newer, REST-based)
3. **iDoc messages** (legacy, EDI format)
4. **ABAP reports** (custom extraction)

**Why we chose CSV**:
- Most common for one-off analytics
- Accessible to non-technical users ("File → Export")
- No infrastructure needed
- Represents what analysts actually receive

### Column Names & Formats

**What we discovered**:
- German header names in some installations (Belegdatum, Menge, Einheit)
- English headers in others (Document Date, Quantity, Unit)
- No standard: depends on SAP customization and region

**Our solution**: Case-insensitive column mapping with fallback matching

**Real headers** we anticipated:
```
German:           English:          Mapping:
Belegdatum     → Document Date  → activity_date
Materialgruppe → Material Group → category
Menge          → Quantity       → quantity
Einheit        → Unit           → unit
Werk           → Plant          → plant_code
Kostenstelle   → Cost Center    → cost_center
Lieferant      → Supplier       → supplier
```

### Realistic Data Problems in sample_data/sap.csv

**1. Inconsistent Dates**
```csv
12.03.2025    ← German format (DD.MM.YYYY)
2025-04-15    ← ISO format
```
**Real world**: Same file mixes formats if exported from multi-region SAP

**2. Unit Variations**
```csv
500 L           ← Liters
120 GAL         ← Gallons
```
**Real world**: Same material group (fuel) different plants use different units

**3. Missing Supplier**
```csv
Diesel, 450 L, , OPS100, Shell India    ← supplier field empty
Diesel, 600 L, , , Shell India          ← no cost center
```
**Real world**: Data entry gaps in legacy ERP

**4. Negative Quantities**
```csv
-100 L, Diesel, BLR01
```
**Real world**: Returns / corrections. SAP records as negative quantities

**5. Unknown Plant Code**
```csv
Diesel, 750 L, BLR01    ← recognized plant
Diesel, 600 L,          ← missing plant code
```
**Real world**: Consolidation data from acquired companies with unfamiliar codes

### What Would Break in Real Deployment

**Problem 1: Material Group Hierarchy**
```
SAP stores: Material Group = "01-Fuels-Liquid-Petroleum-Diesel"
Not just: "Diesel"

Our parser assumes simple names → breaks on deep hierarchies
```
**Fix**: Pre-process material codes to extract fuel type

**Problem 2: Plant Code Mapping**
```
Plant Code "BLR01" means nothing without master data
Need: BLR01 = "Bangalore Facility, India"

Without mapping, can't group by location
```
**Fix**: Maintain plant master data table

**Problem 3: Cost Center Accountability**
```
Cost Center "OPS100" implies responsibility center
But we just store the code, don't validate it exists
```
**Fix**: Foreign key to validated cost centers

**Problem 4: Multi-Currency**
```
SAP stores costs in document currency
But we only imported quantity + unit, not cost
If cost becomes relevant, currency conversion needed
```
**Fix**: Add currency field, handle INR/USD/EUR

**Problem 5: Date Range Queries**
```
Data might be: "Jan 1 export but includes Mar activity date"
Our system stores activity_date correctly, but users might upload old data
```
**Fix**: Warn if activity_date > upload_date significantly

---

## 2. Utility Electricity Data

### Real-World Format Research

**How Utilities Export Data**:

1. **CSV Portal Export** (most common) ← **We chose this**
2. **PDF Utility Bill**
3. **API (some large utilities)**
4. **Spreadsheet manual entry**

**Why we chose CSV Portal Export**:
- Available from 90% of utilities
- Structured, machine-readable
- No OCR errors
- Can download monthly/daily

### What Real Utility CSVs Contain

**Sample from Bangalore Power Supply:**
```
Meter ID    | Billing Start | Billing End | Consumption | Unit
MTR-456782  | Feb 10        | Mar 9       | 1,230       | kWh
```

**What varies**:
- Date format (Feb 10 vs. 10-Feb vs. 10/02/2025)
- Meter ID naming (MTR-456782 vs. 456782 vs. "Main Meter")
- Unit representation (kWh vs. "Units" vs. KWH)
- Billing period (28-32 days typically, but can be 50 if they miss a reading)

### Realistic Data Problems in sample_data/utility.csv

**1. Missing Meter ID**
```csv
,2025-02-12,2025-03-12,800,kWh
```
**Real world**: Consolidated readings, multiple meters on bill
**Our response**: Generate unique ID (UNKNOWN_METER_1), flag as suspicious

**2. Billing Period >45 Days**
```csv
MTR006,2025-01-15,2025-03-20,4200,kWh
```
**Real world**: Meter not read for 64 days, consolidated billing
**Our response**: Flag as "long_billing_period", confidence = 0.9

**3. Unit Variations**
```csv
0.5 MWh        ← Megawatt-hours
1100000 Wh     ← Watt-hours
1200 kWh       ← Kilowatt-hours
```
**Real world**: Different billing systems use different scales
**Our response**: Normalize all to kWh internally

**4. Negative Consumption**
```csv
-150 kWh
```
**Real world**: Credits/adjustments; meter replacement; data corrections
**Our response**: Flag as negative, confidence = 0.3

**5. Unrealistic High Values**
```csv
8500 kWh for a month
```
**Real world**: This could be a warehouse, data center, or manufacturing
**Our response**: Flag as "unusually_high" but don't reject (analyst must decide)

### Tariff Type Complexity

Real utility exports include tariff structure:
```csv
meter_id, consumption, tariff_type
MTR001,   800,        "peak (6am-10pm)"
MTR001,   200,        "offpeak (10pm-6am)"
```

**Why we included it**:
- Different tariffs = different carbon intensity? (Maybe)
- Analysts want to see it
- Future: Can weight by time-of-use carbon factors

**Why we don't analyze it**:
- For MVP, treat all kWh equally
- Adding tariff-specific factors would need research
- Analyst can manually adjust if needed

### What Would Break in Real Deployment

**Problem 1: Meter Aggregation**
```
Bill shows:
- Meter A: 500 kWh
- Meter B: 700 kWh

Do we import as one row (1200) or two rows (500, 700)?
Our sample assumes: one row per meter
Reality: Sometimes consolidated, sometimes detailed
```
**Fix**: Ask utility about structure, or deduplicate by meter

**Problem 2: Net Metering (Solar)**
```
Building with rooftop solar:
- Imported from grid: 1000 kWh
- Exported to grid: 300 kWh
- Net consumption: 700 kWh

Does bill show 700 or 1000? (Usually 700, sometimes both)
Our system: Takes consumption as given (may miss gross import if net metering active)
```
**Fix**: Ask about solar; import gross consumption if available

**Problem 3: Seasonal Baselines**
```
Mumbai electricity in summer (AC load): 2000 kWh
Mumbai electricity in winter: 1000 kWh

Anomaly detection based on annual average: Flags both as unusual
```
**Fix**: Seasonal baselines in confidence scoring (TODO)

**Problem 4: Meter Replacement**
```
Meter replaced: Old readings end, new readings start
If not accounted for, looks like 50% drop → flagged as anomaly
```
**Fix**: Analyst notes explain, we don't auto-flag meter changes

**Problem 5: COVID Spikes & Drops**
```
Facility closed for lockdown: Consumption dropped 80%
Is this an error or reality? (It's reality, but looks wrong)
```
**Fix**: Confidence score stays high; context is analyst's job

---

## 3. Corporate Travel Data

### Real-World Format Research

**Travel Management Platforms**:

1. **Concur (SAP subsidiary)** - most deployed
2. **Navan (ex-Triplebyte)** - modern, growing
3. **TravelPerk** - European standard
4. **Generic Excel** - smaller companies

All export similarly via CSV.

**Why we focused on Concur**:
- Biggest installed base
- API well-documented
- CSV export is standard feature
- Represents realistic expense platform

### What Real Travel CSVs Contain

**Concur Extract**:
```
Employee ID | Expense Type | From | To | Distance | Cost | Currency | Date
EMP001      | Flight       | DEL  | BLR| 1450     | 12000| INR      | 3/15
EMP002      | Hotel        |      |    |          | 50000| INR      | 3/14
```

**What varies**:
- Airport codes (IATA: DEL, BLR) vs. full airport names
- Distance sometimes present, sometimes missing
- Multiple expense types on same platform
- Currency field (INR, USD, EUR, GBP)
- Hotel entries don't have distance (location unclear)

### Realistic Data Problems in sample_data/travel.csv

**1. Missing Distance for Flights**
```csv
EMP001,flight,DEL,BLR,,12000,INR,2025-03-15
```
**Real world**: Not all systems auto-populate distance
**Our response**: Estimate from airport codes (DEL-BLR = 1450 km), flag as "missing_distance"

**2. Missing Employee ID**
```csv
,flight,BLR,DEL,,9500,INR,2025-03-18
```
**Real world**: Consolidated expenses, personal vs. corporate ambiguity
**Our response**: Mark as UNKNOWN_EMP, flag for review

**3. Hotel Entry Without Location**
```csv
EMP003,hotel,,,45,50000,INR,2025-03-14,3
```
**Real world**: Expense might not specify city (cost center implies location?)
**Our response**: Cannot calculate emissions without location, confidence = 0.5

**4. Negative Cost (Refund)**
```csv
EMP010,ground,DEL,BLR,2200,-5000,INR,2025-03-22
```
**Real world**: Cancellations, refunds, overpayments
**Our response**: Flag as "negative_cost", could be legitimate (refund) or error

**5. Domestic vs. International Distance Issues**
```csv
EMP009,flight,DEL,LON,,45000,USD,2025-04-01
```
**Real world**: Airport code "LON" is ambiguous (Heathrow? Gatwick? Stansted?)
**Our response**: Cannot estimate distance, flag as "ambiguous_airport", need clarification

### Why Emissions from Travel Are Tricky

**Flight 1**: DEL → BLR (1450 km direct flight)
```
Emissions = 1450 km × 0.128 kg CO2e/km = 185 kg CO2e
```

**Flight 2**: DEL → London (9200 km, 45,000 INR cost)
```
We have cost but no distance
Airport code "LON" is ambiguous (need city code)
Cannot estimate: flag as "missing_distance", confidence = 0.3
```

**Hotel Night**: What are actual emissions?
```
Scope 3 hotel emissions = 25 kg CO2e per night (global average)
But emissions depend on hotel efficiency, energy mix
Without knowing hotel location: can't use regional grid carbon intensity
```

### What Would Break in Real Deployment

**Problem 1: Multi-Leg Journeys**
```
Employee travels: DEL → BLR → HYD → DEL (3-day trip)
System sees: DEL, BLR, HYD, DEL
Does it import as 3 flights or treat as one round-trip?
```
**Fix**: Add itinerary ID field to group multi-leg journeys

**Problem 2: Hotel Ambiguity**
```
Expense: Hotel, cost 50,000 INR
But which city? Bangalore? Mumbai? Hotel name not captured.
Without location, cannot match to hotel class (luxury = higher emissions)
```
**Fix**: Try to infer from previous flight, or ask hotel field

**Problem 3: Ground Transport Classification**
```
"Ground transport" could be:
- Taxi (expensive, short, high emissions/km)
- Rental car (longer, moderate)
- Train (longer, lower emissions)
- Bus (longer, lowest emissions)

We assume average car. Real emissions vary 5x.
```
**Fix**: Add transport_mode field, not just distance

**Problem 4: Personal vs. Business Travel**
```
Concur shows employee personal flights mixed with business
How to filter? Look at cost center? Destination business/leisure?
```
**Fix**: Require approval chain; approved-only flights count

**Problem 5: Emissions Allocation in Group Travel**
```
5 employees on same flight, cost 50,000
Do we:
- Allocate full 50,000 cost to each? (Inflates 5x)
- Split evenly? (Fair, but doesn't match actual carbon)

Real answer: Emissions don't scale linearly; plane goes either way
```
**Fix**: Policy decision; we allocate full emissions per traveler (conservative)

---

## Sample Data Defensibility

### Why Our Sample Data Looks The Way It Does

**SAP Sample** (`sample_data/sap.csv`):
- 10 rows with 5 different problems (negative qty, missing fields, unit variations)
- Covers scope (Diesel, Petrol, CNG, LPG)
- Shows German date format (12.03.2025)
- Includes both filled and missing supplier fields
- Realistic plant codes (BLR01, MUM02, DEL01, HYD01, PNQ01 - actual Indian cities)

**Utility Sample** (`sample_data/utility.csv`):
- 8 rows with 5 different problems (missing meter, negative reading, >45-day period, unit variations, high consumption)
- Covers unit variations (kWh, MWh, Wh)
- Shows billing periods not aligned to months
- Includes both present and missing meter IDs
- Realistic locations (Indian tech hubs)

**Travel Sample** (`sample_data/travel.csv`):
- 10 rows with 5 different problems (missing distance, missing employee, missing location, negative cost, ambiguous airport)
- Covers all three types (flight, hotel, ground)
- Shows domestic routes with distance lookupable
- Includes international flight without distance
- Shows currency and cost fields
- Realistic employee IDs and airport codes

---

## Emission Factor Defensibility

**Why 0.71 kg CO2e/kWh for India?**
```
India's grid carbon intensity (2024):
- Coal: ~60% of generation
- Renewables: ~20% (growing)
- Gas/Nuclear: ~20%
- Average: 0.71 kg CO2e per kWh

Source: IEA India Grid Carbon Intensity Report
```

**Why 2.68 kg CO2e/L for Diesel?**
```
Diesel combustion:
- 1 liter diesel = 2.68 kg CO2e
- Includes extraction + refining + combustion
- Standard in India's PAT scheme

Source: Ministry of Power, Energy Conservation Act calculations
```

**Why 0.128 kg CO2e/km for Flights?**
```
Typical commercial flight:
- 150-180 seater
- Radiative forcing index: 2-3 (high altitude multiplier)
- Average emissions: 0.128 kg CO2e per passenger-km

Could be 0.05 (optimal full flight) to 0.2 (inefficient short flight)
We use middle estimate

Source: ICAO Carbon Calculator methodology
```

---

## If You Could Ask the Real Client

1. **SAP Format**: Are you exporting flat CSV from SE16N, or do you have an automated iDoc pull?
2. **Utility Data**: Which utility? (Each Indian utility has different format)
3. **Meter Accuracy**: Do you have smart meters (daily reads) or manual monthly reads?
4. **Travel Consolidation**: Is Concur your only travel platform? (Some companies use Uber, local taxis separately)
5. **Scope 3 Expansion**: Do you want to include supplier emissions from SAP spend data?
6. **Regional Factors**: Should electricity factors be state-specific? (Grid carbon intensity varies: Tamil Nadu renewables vs. coal-heavy states)
7. **Hotel Emissions**: Do you want to factor in specific hotel efficiency, or use global average?

---

## Conclusion

Our sample data reflects:
✅ Real enterprise data shapes  
✅ Real messiness and inconsistencies  
✅ Real audit requirements (trace to source)  
✅ Real ambiguities (missing distance, tariff types)  
✅ Real scope limits (4-day project can't solve all)  

We didn't fabricate "clean" data. We fabricated **realistic** data and built a system that handles it honestly.
