import pandas as pd
from datetime import datetime
import json
from decimal import Decimal

class SAPParser:
    """
    Parses SAP flat-file exports for fuel and procurement.
    
    Real SAP exports have:
    - German column headers (sometimes)
    - Inconsistent date formats
    - Plant codes without context
    - Multiple units for same category
    - Missing supplier info
    """
    
    # Column name mappings - handle German headers
    COLUMN_MAPPINGS = {
        'Belegdatum': 'date',
        'Date': 'date',
        'document_date': 'date',
        
        'Materialgruppe': 'material_group',
        'Material Group': 'material_group',
        'material_group': 'material_group',
        
        'Menge': 'quantity',
        'Quantity': 'quantity',
        'amount': 'quantity',
        
        'Einheit': 'unit',
        'Unit': 'unit',
        'UOM': 'unit',
        
        'Werk': 'plant_code',
        'Plant': 'plant_code',
        'plant_code': 'plant_code',
        
        'Kostenstelle': 'cost_center',
        'Cost Center': 'cost_center',
        'cost_center': 'cost_center',
        
        'Lieferant': 'supplier',
        'Supplier': 'supplier',
        'supplier': 'supplier',
    }
    
    # Material group to emission scope mapping
    MATERIAL_TO_SCOPE = {
        'Diesel': ('FUEL_DIESEL', 'SCOPE_1'),
        'Petrol': ('FUEL_PETROL', 'SCOPE_1'),
        'CNG': ('FUEL_CNG', 'SCOPE_1'),
        'LPG': ('FUEL_LPG', 'SCOPE_1'),
        'Electricity': ('ELECTRICITY', 'SCOPE_2'),
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def parse(self, file_path):
        """
        Parse a SAP CSV export.
        Returns list of dicts with normalized field names and metadata.
        """
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            # SAP sometimes exports in other encodings
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
                    'row_number': idx + 2,  # +2 because header is row 1, 0-indexed
                    'error': str(e)
                })
        
        return records
    
    def _map_columns(self, columns):
        """Map incoming column names to standard names."""
        mapped = []
        for col in columns:
            # Try exact match first
            if col in self.COLUMN_MAPPINGS:
                mapped.append(self.COLUMN_MAPPINGS[col])
            else:
                # Try case-insensitive match
                for sap_col, standard_col in self.COLUMN_MAPPINGS.items():
                    if col.lower() == sap_col.lower():
                        mapped.append(standard_col)
                        break
                else:
                    # Unknown column - keep as is
                    mapped.append(col.lower().replace(' ', '_'))
        
        return mapped
    
    def _parse_row(self, row, row_idx):
        """Parse a single SAP row."""
        
        # Parse date (handle German format DD.MM.YYYY and ISO)
        date_str = str(row.get('date', '')).strip()
        if not date_str or date_str == 'nan':
            raise ValueError("Missing date")
        
        activity_date = self._parse_date(date_str)
        
        # Quantity and unit
        quantity = row.get('quantity')
        if pd.isna(quantity):
            raise ValueError("Missing quantity")
        
        quantity = float(quantity)
        
        unit = str(row.get('unit', '')).strip()
        if not unit or unit == 'nan':
            raise ValueError("Missing unit")
        
        # Material group
        material = str(row.get('material_group', '')).strip()
        if not material or material == 'nan':
            raise ValueError("Missing material group")
        
        # Plant code
        plant_code = str(row.get('plant_code', '')).strip()
        if not plant_code or plant_code == 'nan':
            plant_code = 'UNKNOWN'
        
        # Supplier (optional)
        supplier = str(row.get('supplier', '')).strip()
        supplier = supplier if supplier and supplier != 'nan' else None
        
        # Cost center (optional)
        cost_center = str(row.get('cost_center', '')).strip()
        cost_center = cost_center if cost_center and cost_center != 'nan' else None
        
        # Map material to category and scope
        category, scope = self._map_material(material)
        
        return {
            'activity_date': activity_date,
            'category': category,
            'scope': scope,
            'quantity': quantity,
            'unit': unit,
            'plant_code': plant_code,
            'supplier': supplier,
            'cost_center': cost_center,
            'source_type': 'SAP',
            'row_index': row_idx,
        }
    
    def _parse_date(self, date_str):
        """Handle multiple date formats from SAP."""
        formats = [
            '%d.%m.%Y',  # German: 12.03.2025
            '%Y-%m-%d',  # ISO: 2025-03-12
            '%m/%d/%Y',  # US: 03/12/2025
            '%d/%m/%Y',  # UK: 12/03/2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f"Cannot parse date: {date_str}")
    
    def _map_material(self, material):
        """Map SAP material to category and scope."""
        for key, (category, scope) in self.MATERIAL_TO_SCOPE.items():
            if key.lower() in material.lower():
                return category, scope
        
        # Default fallback
        return 'FUEL_DIESEL', 'SCOPE_1'