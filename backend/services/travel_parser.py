import pandas as pd
from datetime import datetime
from decimal import Decimal


class TravelParser:
    """
    Parses corporate travel data from Concur/Navan CSV exports.
    
    Real travel data has:
    - Airport codes only (need distance lookup)
    - Missing distance data
    - Mixed categories (flight/hotel/ground)
    - Multiple currencies
    """
    
    # Airport code to approximate distances (simplified)
    # In production: use actual distance calculation
    DISTANCE_APPROXIMATION = {
        'DEL-BLR': 2200,  # Delhi to Bangalore (km)
        'BOM-BLR': 1100,  # Mumbai to Bangalore
        'DEL-BOM': 1450,  # Delhi to Mumbai
        'DEL-HYD': 1730,  # Delhi to Hyderabad
        'BLR-HYD': 580,   # Bangalore to Hyderabad
        'DEL-PNQ': 1670,  # Delhi to Pune
    }
    
    COLUMN_MAPPINGS = {
        'employee_id': 'employee_id',
        'Employee ID': 'employee_id',
        'Emp ID': 'employee_id',
        
        'travel_type': 'travel_type',
        'Travel Type': 'travel_type',
        'Category': 'travel_type',
        'Expense Type': 'travel_type',
        
        'origin': 'origin',
        'Origin': 'origin',
        'From': 'origin',
        'departure_airport': 'origin',
        
        'destination': 'destination',
        'Destination': 'destination',
        'To': 'destination',
        'arrival_airport': 'destination',
        
        'distance': 'distance',
        'Distance': 'distance',
        'distance_km': 'distance',
        'Distance (km)': 'distance',
        
        'cost': 'cost',
        'Cost': 'cost',
        'Amount': 'cost',
        'expense_amount': 'cost',
        
        'currency': 'currency',
        'Currency': 'currency',
        'CUR': 'currency',
        
        'travel_date': 'travel_date',
        'Travel Date': 'travel_date',
        'Date': 'travel_date',
        'Expense Date': 'travel_date',
        
        'hotel_nights': 'hotel_nights',
        'Hotel Nights': 'hotel_nights',
        'Nights': 'hotel_nights',
    }
    
    # Travel type mapping to emission category
    TRAVEL_TYPE_MAPPING = {
        'flight': 'TRAVEL_FLIGHT',
        'flights': 'TRAVEL_FLIGHT',
        'air': 'TRAVEL_FLIGHT',
        
        'hotel': 'TRAVEL_HOTEL',
        'accommodation': 'TRAVEL_HOTEL',
        
        'cab': 'TRAVEL_GROUND',
        'taxi': 'TRAVEL_GROUND',
        'ground': 'TRAVEL_GROUND',
        'transport': 'TRAVEL_GROUND',
        'car': 'TRAVEL_GROUND',
    }
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def parse(self, file_path):
        """Parse a travel CSV export."""
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
                for travel_col, standard_col in self.COLUMN_MAPPINGS.items():
                    if col.lower() == travel_col.lower():
                        mapped.append(standard_col)
                        break
                else:
                    mapped.append(col.lower().replace(' ', '_'))
        
        return mapped
    
    def _parse_row(self, row, row_idx):
        """Parse a single travel row."""
        
        # Travel type
        travel_type = str(row.get('travel_type', '')).strip()
        if not travel_type or travel_type == 'nan':
            raise ValueError("Missing travel type")
        
        category = self._map_travel_type(travel_type)
        
        # Travel date
        travel_date = self._parse_date(row.get('travel_date'))
        if not travel_date:
            raise ValueError("Missing travel date")
        
        activity_date = travel_date
        
        # Employee ID
        employee_id = str(row.get('employee_id', '')).strip()
        if not employee_id or employee_id == 'nan':
            employee_id = 'UNKNOWN'
        
        # Cost and currency
        cost = row.get('cost')
        if pd.isna(cost):
            raise ValueError("Missing cost")
        
        cost = float(cost)
        
        currency = str(row.get('currency', 'USD')).strip()
        if not currency or currency == 'nan':
            currency = 'USD'
        
        currency = currency.upper()
        
        # Travel details depend on category
        origin = None
        destination = None
        distance = None
        hotel_nights = None
        
        if category == 'TRAVEL_FLIGHT':
            origin = str(row.get('origin', '')).strip().upper()
            destination = str(row.get('destination', '')).strip().upper()
            
            if not origin or origin == 'NAN':
                raise ValueError("Missing origin airport")
            if not destination or destination == 'NAN':
                raise ValueError("Missing destination airport")
            
            # Get distance
            distance = self._get_distance(origin, destination, row.get('distance'))
        
        elif category == 'TRAVEL_HOTEL':
            # Hotel nights
            hotel_nights = row.get('hotel_nights')
            if pd.isna(hotel_nights):
                hotel_nights = 1  # Assume 1 night if missing
            else:
                hotel_nights = int(hotel_nights)
            
            # Location (optional)
            destination = str(row.get('destination', '')).strip()
        
        elif category == 'TRAVEL_GROUND':
            origin = str(row.get('origin', '')).strip().upper()
            destination = str(row.get('destination', '')).strip().upper()
            distance = self._get_distance(origin, destination, row.get('distance'))
        
        return {
            'activity_date': activity_date.isoformat() if activity_date else None,
            'category': category,
            'scope': 'SCOPE_3',
            'employee_id': employee_id,
            'cost': cost,
            'currency': currency,
            'origin': origin,
            'destination': destination,
            'distance': distance,
            'hotel_nights': hotel_nights,
            'source_type': 'TRAVEL',
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
    
    def _map_travel_type(self, travel_type):
        """Map travel type string to category."""
        travel_lower = travel_type.lower().strip()
        
        for key, category in self.TRAVEL_TYPE_MAPPING.items():
            if key in travel_lower:
                return category
        
        # Default to flight if unclear
        return 'TRAVEL_FLIGHT'
    
    def _get_distance(self, origin, destination, distance_col):
        """Get distance in km, from column or approximation."""
        
        # Try to use provided distance
        if not pd.isna(distance_col):
            try:
                return float(distance_col)
            except:
                pass
        
        # Try to look up
        if origin and destination:
            key1 = f"{origin}-{destination}"
            key2 = f"{destination}-{origin}"
            
            if key1 in self.DISTANCE_APPROXIMATION:
                return self.DISTANCE_APPROXIMATION[key1]
            elif key2 in self.DISTANCE_APPROXIMATION:
                return self.DISTANCE_APPROXIMATION[key2]
        
        # Return None if cannot determine
        # This will be flagged in validation
        return None