# Breathe ESG - Emissions Data Ingestion Platform

A Django REST + React application for ingesting, normalizing, and reviewing corporate emissions data from multiple sources (SAP, Utility, Travel).

**Demo**: [Live URL will be provided on deployment]

---

## Overview

This system solves a real enterprise problem: carbon data lives in different systems with different formats. The platform:

1. **Ingests** messy data from SAP, utility portals, and travel platforms
2. **Normalizes** everything to standard units and formats
3. **Flags** suspicious or incomplete data automatically
4. **Lets analysts review** and approve before audit lock
5. **Maintains** complete audit trail for compliance

**Key Design Principle**: Never lose raw data. Every normalized record is traceable to its source.

---

## Architecture

### Backend
- **Django 4.2** + Django REST Framework
- **PostgreSQL** for relational data + audit trail
- **Pandas** for CSV parsing
- **JWT** authentication

### Frontend
- **React 18** with Vite
- **React Router** for navigation
- Custom CSS styling
- Simple, analyst-friendly UX

### Deployment
- **Backend**: Render
- **Frontend**: Vercel
- **Database**: PostgreSQL (Render)

---

## Local Setup (Development)

### Prerequisites
- Python 3.10+
- Node.js 16+
- PostgreSQL 13+

### Backend Setup

```bash
# Clone repository
git clone <repo-url>
cd breathe-esg/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost:5432/breathe_esg
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
EOF

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Sample CSV files are available in backend/sample_data/ for testing

# Run server
python manage.py runserver
```

Backend runs at `http://localhost:8000`

### Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env.local
cat > .env.local << EOF
VITE_API_URL=http://localhost:8000
EOF

# Run development server
npm run dev
```

Frontend runs at `http://localhost:5173`

### Test with Sample Data

1. Navigate to `http://localhost:5173/upload`
2. Select data source (SAP, Utility, or Travel)
3. Download sample file
4. Upload and process
5. View results in `/review` queue

---

## Deployment (Production)

### Prerequisites
- GitHub repository (push code first)
- Render account (free tier works)
- Vercel account (free tier works)

### Deploy Backend to Render

1. **Create PostgreSQL Database**:
   - Render → Databases → Create → PostgreSQL
   - Copy database connection URL

2. **Create Web Service**:
   - Render → Web Services → Create → GitHub
   - Select `breathe-esg` repository
   - Set environment:
     ```
     SECRET_KEY=<generate-random-string>
     DEBUG=False
     DATABASE_URL=<postgres-url-from-above>
     ALLOWED_HOSTS=*.onrender.com
     CORS_ALLOWED_ORIGINS=https://<vercel-frontend-url>
     ```
   - Build: `pip install -r backend/requirements.txt`
   - Start: `cd backend && python manage.py migrate && gunicorn config.wsgi:application`

3. **Verify**:
   - Open `https://<backend-url>/api/` → should see API root

### Deploy Frontend to Vercel

1. **Connect GitHub**:
   - Vercel → New Project → Import GitHub repo
   - Root directory: `frontend`

2. **Set environment**:
   ```
   VITE_API_URL=https://<backend-url>
   ```

3. **Deploy**:
   - Click "Deploy"
   - Vercel builds and deploys automatically

4. **Verify**:
   - Open deployment URL → should see login page

### Post-Deployment

```bash
# SSH into Render backend
render-cli exec breathe-esg-backend

# Create superuser
python manage.py createsuperuser

# Test with sample data via frontend
```

---

## Data Model

See `MODEL.md` for complete documentation.

**Core Tables**:

- **Organization**: Multi-tenant root
- **DataSource**: Tracks uploads (who, when, what file)
- **RawRecord**: Preserves original data exactly (audit trail)
- **EmissionRecord**: Normalized, analyst-friendly view
- **ReviewHistory**: Complete audit trail of approvals

**Key Design**: 1:1 relationship between RawRecord and EmissionRecord ensures traceability.

---

## API Endpoints

### Authentication
- `POST /api/token/` - Get JWT token

### Emissions Records
- `GET /api/emissions/` - List records (filterable)
- `GET /api/emissions/{id}/` - Record detail
- `POST /api/emissions/{id}/approve/` - Approve/reject/flag
- `POST /api/emissions/batch_approve/` - Batch actions
- `GET /api/emissions/dashboard_stats/` - Metrics

### Data Sources
- `POST /api/data-sources/` - Create upload
- `POST /api/data-sources/{id}/process/` - Upload & process file
- `GET /api/data-sources/` - List uploads

### Organizations
- `GET /api/organizations/` - List organizations

---

## Usage Flow

### For Analysts

1. **Upload Data**:
   - Go to `/upload`
   - Select source type (SAP, Utility, Travel)
   - Upload CSV file
   - System processes and shows preview

2. **Review Queue**:
   - Go to `/review`
   - Filter by status/scope/source
   - Select records needing review
   - Batch approve/reject with notes
   - System logs every action

3. **Dashboard**:
   - See metrics (total records, pending, approved, etc.)
   - View emissions by Scope (1/2/3)
   - Track data quality

### For Auditors

- All approved records are locked (cannot edit)
- Complete audit trail shows who approved what and when (via ReviewHistory model)
- Raw data preserved for verification
- Can drill into any record to see source

---

## Data Sources

### SAP (Fuel & Procurement)

**What we ingest**: CSV export from SAP SE16N
- **Columns**: Date, Material Group, Quantity, Unit, Plant Code, Cost Center
- **Example**: 500 liters of diesel, 12.03.2025, Plant BLR01
- **Issues handled**:
  - German date formats (DD.MM.YYYY)
  - Inconsistent units (L vs. GAL)
  - Missing supplier info
  - Negative quantities (returns)

See `SOURCES.md` for details.

### Utility (Electricity)

**What we ingest**: CSV export from utility portal
- **Columns**: Meter ID, Billing Start/End, Consumption, Unit
- **Example**: MTR001, 1200 kWh, Feb 10 - Mar 9
- **Issues handled**:
  - Different units (kWh vs. MWh vs. Wh)
  - Billing periods >45 days
  - Missing meter IDs
  - Negative readings (adjustments)

### Travel (Flights, Hotels, Ground)

**What we ingest**: CSV export from Concur/Navan
- **Columns**: Employee ID, Type, Origin/Destination, Distance, Cost
- **Example**: Flight DEL-BLR, 1450 km, 12000 INR
- **Issues handled**:
  - Missing distances (estimated from airport codes)
  - Negative costs (refunds)
  - Hotel location ambiguity
  - Unknown employees

---

## Configuration

### Emission Factors

Located in `backend/services/normalizer.py`:

```python
FUEL_EMISSION_FACTORS = {
    'FUEL_DIESEL': Decimal('2.68'),      # kg CO2e/liter
    'FUEL_PETROL': Decimal('2.31'),      # kg CO2e/liter
    # ...
}

ELECTRICITY_EMISSION_FACTOR = Decimal('0.71')  # kg CO2e/kWh (India grid)

TRAVEL_EMISSION_FACTORS = {
    'TRAVEL_FLIGHT': Decimal('0.128'),   # kg CO2e/km
    'TRAVEL_HOTEL': Decimal('25.0'),     # kg CO2e/night
    'TRAVEL_GROUND': Decimal('0.089'),   # kg CO2e/km
}
```

**To customize**:
1. Edit `services/normalizer.py`
2. Update factors for your region/company
3. Deploy

### Unit Conversions

All internal units are canonical:
- **Fuel**: Liters
- **Electricity**: kWh
- **Distance**: km

Conversions happen at parse time. See `Normalizer` class for mappings.

---

## Troubleshooting

### File Upload Fails

**Problem**: "No file provided"
- **Solution**: Make sure file is selected and is .csv format

### Processing Errors

**Problem**: "Normalization Failed"
- **Solution**: Check `RawRecord` for error message. Common issues:
  - Missing required column
  - Date format unrecognized
  - Quantity is non-numeric

**Debug**:
```bash
# Check raw record
python manage.py shell
>>> from apps.emissions.models import RawRecord
>>> RawRecord.objects.filter(processing_status='FAILED')[0].raw_json
>>> # Shows exactly what was parsed
```

### API 401 Unauthorized

**Problem**: "Authentication failed"
- **Solution**: Token expired or missing. Re-login.
- **Fix**: `localStorage.clear()` in browser console, refresh

### Database Connection Error

**Problem**: "could not connect to server"
- **Solution**: Check DATABASE_URL in .env
- **Local**: Make sure PostgreSQL is running: `pg_isready`
- **Production**: Verify Render database URL and IP whitelist

---

## Testing

### Sample Data

Three realistic sample CSV files in `backend/sample_data/`:

```bash
# SAP: fuel with inconsistent units, missing suppliers
# Utility: electricity with billing periods, high consumption
# Travel: flights without distances, missing employees
```

Use these for testing without real data.

### Unit Tests

```bash
python manage.py test
```

### Manual Testing Checklist

- [ ] Upload SAP data → records parsed
- [ ] Upload utility data → units normalized to kWh
- [ ] Upload travel data → distance estimated from codes
- [ ] Filter by scope/status → correct records shown
- [ ] Batch approve → records locked, history logged
- [ ] Reject record → moved to REJECTED status
- [ ] Dashboard stats → totals correct
- [ ] Audit trail → shows all actions with timestamps

---

## Project Structure

```
breathe-esg/
├── backend/
│   ├── config/              # Django settings
│   ├── apps/
│   │   ├── audits/          # Audit-related models
│   │   ├── emissions/       # Core models & views
│   │   └── ingestion/       # Upload handling
│   ├── services/
│   │   ├── emission_calculator.py  # Emissions calculation
│   │   ├── normalizer.py    # Unit conversion & emissions calc
│   │   ├── sap_parser.py    # SAP CSV parsing
│   │   ├── utility_parser.py
│   │   └── travel_parser.py
│   ├── sample_data/         # Test CSV files
│   └── manage.py
│
├── frontend/
│   ├── src/
│   │   ├── api/             # API client utilities
│   │   ├── components/      # Reusable UI components
│   │   │   ├── MetricCard.jsx
│   │   │   ├── ReviewTable.jsx
│   │   │   ├── StatusBadge.jsx
│   │   │   └── UploadCard.jsx
│   │   ├── pages/           # Page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Upload.jsx
│   │   │   └── Review.jsx
│   │   ├── styles/          # CSS modules
│   │   ├── utils/           # Utility functions
│   │   ├── App.css
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── MODEL.md                 # Data model documentation
├── DECISIONS.md             # Engineering decisions
├── TRADEOFFS.md             # What we didn't build
├── SOURCES.md               # Data source research
└── README.md                # This file
```

---

## Performance

### Query Optimization

- Indexes on `(organization, review_status)` for review queue
- Indexes on `(organization, activity_date)` for time-series
- Prefetch relations to avoid N+1 queries

### Upload Performance

- Streaming file upload (doesn't load entire file into memory)
- Batch insert for raw records (1000 records in ~2 seconds)
- Asynchronous normalization (TODO: add Celery for real-time feedback)

### Expected Scale

- **Handles**: 100k records/month
- **Response time**: <500ms for list queries
- **Storage**: ~1GB/year (with raw data preservation)

---

## Security

### In Production

✅ HTTPS only (Render/Vercel enforce)  
✅ CSRF tokens enabled  
✅ JWT tokens with short expiry  
✅ Database encrypted at rest  
✅ User authentication required  
✅ No passwords in git (use .env)  

### Not Implemented (TODO)

- OAuth/SSO (SAML integration)
- Rate limiting
- API key rotation
- Encryption at column level

---

## Contributing

### Code Style

- Follow PEP 8 (Python)
- Use meaningful variable names
- Document complex logic

### Before Submitting

```bash
# Backend tests
cd backend
python manage.py test

# Frontend build
cd frontend
npm run build
```

---

## Support

For issues:
1. Check `MODEL.md` and `DECISIONS.md` for context
2. Review sample data in `SOURCES.md`
3. Look at error messages in RawRecord
4. Check browser console for API errors

---

## License

Proprietary - Breathe ESG internal use only

---

## Acknowledgments

Built as a 4-day take-home assignment for Breathe ESG.

Design prioritizes:
- **Auditability** (never lose data)
- **Transparency** (analysts understand every decision)
- **Simplicity** (less code = fewer bugs)
- **Scalability** (normalized data model)

See `DECISIONS.md` for detailed engineering rationale.
