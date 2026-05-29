import pandas as pd
from datetime import datetime
from decimal import Decimal


class UtilityParser:
    """
    Parses utility electricity data from portal CSV exports.
    
    Real utility data has:
    - Billing periods (not calendar months)
    - Multiple units: kWh, MWh
    - Missing meter IDs
    - Peak/off-peak tariffs
    - Multiple tariff types
    """
    
    COLUMN_MAPPINGS = {
        'meter_id': 'meter_id',
        'Meter ID': 'meter_id',
        'Meter': 'meter_id',
        'meter': 'meter_id',
        
        'billing_start': 'billing_start',
        'Billing Start': 'billing_start',
        'start_date': 'billing_start',
        'Period Start': 'billing_start',
        
        'billing_end': 'billing_end',
        'Billing End': 'billing_end',
        'end_date': 'billing_end',
        'Period End': 'billing_end',
        
        'consumption': 'consumption',
        'Consumption': 'consumption',
        'Usage': 'consumption',
        'energy_usage': 'consumption',
        
        'unit': 'unit',
        'Unit': 'unit',
        'UOM': 'unit',
        
        'tariff_type': 'tariff_type',
        'Tariff': 'tariff_type',
        'Tariff Type': 'tariff_type',
        
        'location': 'location',
        'Location': 'location',
        'Site': 'location',
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def parse(self, file_path):
        """Parse a utility CSV export."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='latin-1')
        
        # Normalize column names
        df.columns = self._map_columns(df.columns)
        
        records = []
        
        for idx, row in df.iterrows():
            try:
                record = self._parse_row(row, idx)
                records.append(record)
            except Exception as e:
                self.errors.append({
                    'row_number': idx + 2,
                    'error': str(e)
                })
        
        return records
    
    def _map_columns(self, columns):
        """Map incoming column names to standard names."""
        mapped = []
        for col in columns:
            if col in self.COLUMN_MAPPINGS:
                mapped.append(self.COLUMN_MAPPINGS[col])
            else:
                for util_col, standard_col in self.COLUMN_MAPPINGS.items():
                    if col.lower() == util_col.lower():
                        mapped.append(standard_col)
                        break
                else:
                    mapped.append(col.lower().replace(' ', '_'))
        
        return mapped
    
    def _parse_row(self, row, row_idx):
        """Parse a single utility row."""
        
        # Meter ID (may be missing)
        meter_id = str(row.get('meter_id', '')).strip()
        if not meter_id or meter_id == 'nan':
            meter_id = f"UNKNOWN_METER_{row_idx}"
        
        # Billing period
        billing_start = self._parse_date(row.get('billing_start'))
        if not billing_start:
            raise ValueError("Missing billing start date")
        
        billing_end = self._parse_date(row.get('billing_end'))
        if not billing_end:
            raise ValueError("Missing billing end date")
        
        # Use the END date of billing period as activity_date
        # (electricity consumption is typically recorded at end of period)
        activity_date = billing_end
        
        # Consumption
        consumption = row.get('consumption')
        if pd.isna(consumption):
            raise ValueError("Missing consumption value")
        
        consumption = float(consumption)
        
        if consumption < 0:
            raise ValueError(f"Negative consumption: {consumption}")
        
        # Unit (default to kWh)
        unit = str(row.get('unit', 'kWh')).strip()
        if not unit or unit == 'nan':
            unit = 'kWh'
        
        # Normalize unit
        unit = self._normalize_unit(unit)
        
        # Tariff type (optional - peak/off-peak)
        tariff_type = str(row.get('tariff_type', '')).strip()
        if not tariff_type or tariff_type == 'nan':
            tariff_type = 'standard'
        
        # Location (optional)
        location = str(row.get('location', '')).strip()
        if not location or location == 'nan':
            location = None
        
        return {
            'activity_date': activity_date.isoformat() if activity_date else None,
            'category': 'ELECTRICITY',
            'scope': 'SCOPE_2',
            'quantity': consumption,
            'unit': unit,
            'meter_id': meter_id,
            'billing_start': billing_start.isoformat() if billing_start else None,
            'billing_end': billing_end.isoformat() if billing_end else None,
            'tariff_type': tariff_type,
            'location': location,
            'source_type': 'UTILITY',
            'row_index': row_idx,
        }
    
    def _parse_date(self, date_val):
        """Parse date flexibly."""
        if pd.isna(date_val):
            return None
        
        date_str = str(date_val).strip()
        if not date_str or date_str == 'nan':
            return None
        
        formats = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%d.%m.%Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _normalize_unit(self, unit):
        """Normalize energy units."""
        unit = unit.upper().strip()
        
        # Map variations to canonical
        if 'MWH' in unit or 'MW' in unit:
            return 'MWh'
        elif 'KWH' in unit or 'KW' in unit:
            return 'kWh'
        elif 'WH' in unit:
            return 'Wh'
        
        # Default
        return 'kWh'