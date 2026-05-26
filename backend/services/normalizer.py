from decimal import Decimal
from datetime import datetime, date


class Normalizer:
    """
    Converts parsed data into normalized EmissionRecord format.
    
    Key responsibilities:
    1. Convert all units to canonical internal units
    2. Apply consistent naming
    3. Calculate emissions using emission factors
    4. Detect suspicious data patterns
    5. Score confidence in the data
    """
    
    # ========== UNIT CONVERSIONS ==========
    
    # To liters
    VOLUME_TO_LITERS = {
        'L': Decimal('1.0'),
        'LITER': Decimal('1.0'),
        'LITERS': Decimal('1.0'),
        'GAL': Decimal('3.78541'),
        'GALLON': Decimal('3.78541'),
        'GALLONS': Decimal('3.78541'),
        'ML': Decimal('0.001'),
        'MILLILITER': Decimal('0.001'),
    }
    
    # To kWh
    ENERGY_TO_KWH = {
        'KWH': Decimal('1.0'),
        'KW': Decimal('1.0'),
        'MWH': Decimal('1000.0'),
        'MW': Decimal('1000.0'),
        'WH': Decimal('0.001'),
        'W': Decimal('0.001'),
    }
    
    # To km
    DISTANCE_TO_KM = {
        'KM': Decimal('1.0'),
        'MILE': Decimal('1.60934'),
        'MILES': Decimal('1.60934'),
        'M': Decimal('0.001'),
        'METER': Decimal('0.001'),
    }
    
    # ========== EMISSION FACTORS (kg CO2e per unit) ==========
    
    # Fuel emission factors (kg CO2e per liter)
    FUEL_EMISSION_FACTORS = {
        'FUEL_DIESEL': Decimal('2.68'),
        'FUEL_PETROL': Decimal('2.31'),
        'FUEL_CNG': Decimal('1.75'),
        'FUEL_LPG': Decimal('1.60'),
    }
    
    # Electricity emission factor (kg CO2e per kWh)
    # Using India average grid carbon intensity
    ELECTRICITY_EMISSION_FACTOR = Decimal('0.71')  # kg CO2e/kWh
    
    # Travel emission factors
    TRAVEL_EMISSION_FACTORS = {
        'TRAVEL_FLIGHT': Decimal('0.128'),  # kg CO2e per km
        'TRAVEL_HOTEL': Decimal('25.0'),    # kg CO2e per night
        'TRAVEL_GROUND': Decimal('0.089'),  # kg CO2e per km (average car)
    }
    
    def __init__(self):
        self.warnings = []
        self.suspicious_flags = {}
    
    def normalize_sap_record(self, parsed_record):
        """Normalize SAP fuel data."""
        
        # Convert quantity to liters
        normalized_qty = self._convert_volume(
            parsed_record['quantity'],
            parsed_record['unit']
        )
        
        # Get emission factor
        category = parsed_record['category']
        emission_factor = self.FUEL_EMISSION_FACTORS.get(category, Decimal('2.31'))
        
        # Calculate emissions
        calculated_emissions = normalized_qty * emission_factor
        
        # Check for suspicious patterns
        flags = self._check_sap_suspicious(parsed_record, normalized_qty)
        
        return {
            'activity_date': parsed_record['activity_date'],
            'category': category,
            'scope': parsed_record['scope'],
            'normalized_value': normalized_qty,
            'normalized_unit': 'liters',
            'original_unit': parsed_record['unit'],
            'emission_factor': emission_factor,
            'calculated_emissions': calculated_emissions,
            'suspicious_flags': flags,
            'confidence_score': self._calculate_confidence(flags),
        }
    
    def normalize_utility_record(self, parsed_record):
        """Normalize electricity data."""
        
        # Convert to kWh
        normalized_qty = self._convert_energy(
            parsed_record['quantity'],
            parsed_record['unit']
        )
        
        # Electricity always uses same factor
        emission_factor = self.ELECTRICITY_EMISSION_FACTOR
        
        # Calculate emissions
        calculated_emissions = normalized_qty * emission_factor
        
        # Check for suspicious patterns
        flags = self._check_utility_suspicious(parsed_record, normalized_qty)
        
        return {
            'activity_date': parsed_record['activity_date'],
            'category': parsed_record['category'],
            'scope': parsed_record['scope'],
            'normalized_value': normalized_qty,
            'normalized_unit': 'kWh',
            'original_unit': parsed_record['unit'],
            'emission_factor': emission_factor,
            'calculated_emissions': calculated_emissions,
            'suspicious_flags': flags,
            'confidence_score': self._calculate_confidence(flags),
        }
    
    def normalize_travel_record(self, parsed_record):
        """Normalize travel data."""
        
        category = parsed_record['category']
        emission_factor = self.TRAVEL_EMISSION_FACTORS.get(category, Decimal('0.128'))
        
        # Activity quantity depends on category
        if category == 'TRAVEL_FLIGHT' or category == 'TRAVEL_GROUND':
            # Distance-based
            if not parsed_record.get('distance'):
                normalized_qty = Decimal('0')
                flags = {'missing_distance': True}
            else:
                normalized_qty = Decimal(str(parsed_record['distance']))
                flags = self._check_travel_suspicious(parsed_record)
            
            normalized_unit = 'km'
        
        elif category == 'TRAVEL_HOTEL':
            # Hotel nights
            nights = parsed_record.get('hotel_nights', 1)
            normalized_qty = Decimal(str(nights))
            normalized_unit = 'nights'
            flags = self._check_travel_suspicious(parsed_record)
        
        else:
            normalized_qty = Decimal('0')
            normalized_unit = 'unknown'
            flags = {'unknown_travel_type': True}
        
        # Calculate emissions
        calculated_emissions = normalized_qty * emission_factor
        
        return {
            'activity_date': parsed_record['activity_date'],
            'category': category,
            'scope': parsed_record['scope'],
            'normalized_value': normalized_qty,
            'normalized_unit': normalized_unit,
            'original_unit': None,
            'emission_factor': emission_factor,
            'calculated_emissions': calculated_emissions,
            'suspicious_flags': flags,
            'confidence_score': self._calculate_confidence(flags),
        }
    
    # ========== UNIT CONVERSION HELPERS ==========
    
    def _convert_volume(self, quantity, unit):
        """Convert any volume to liters."""
        unit_upper = str(unit).upper().strip()
        
        if unit_upper not in self.VOLUME_TO_LITERS:
            # Unknown unit, assume liters
            return Decimal(str(quantity))
        
        factor = self.VOLUME_TO_LITERS[unit_upper]
        return Decimal(str(quantity)) * factor
    
    def _convert_energy(self, quantity, unit):
        """Convert any energy to kWh."""
        unit_upper = str(unit).upper().strip()
        
        if unit_upper not in self.ENERGY_TO_KWH:
            # Unknown unit, assume kWh
            return Decimal(str(quantity))
        
        factor = self.ENERGY_TO_KWH[unit_upper]
        return Decimal(str(quantity)) * factor
    
    def _convert_distance(self, quantity, unit):
        """Convert any distance to km."""
        unit_upper = str(unit).upper().strip()
        
        if unit_upper not in self.DISTANCE_TO_KM:
            # Unknown unit, assume km
            return Decimal(str(quantity))
        
        factor = self.DISTANCE_TO_KM[unit_upper]
        return Decimal(str(quantity)) * factor
    
    # ========== SUSPICIOUS DATA DETECTION ==========
    
    def _check_sap_suspicious(self, record, normalized_qty):
        """Check for suspicious SAP records."""
        flags = {}
        
        # Negative quantity
        if record['quantity'] < 0:
            flags['negative_quantity'] = True
        
        # Very large quantity (>10000 liters)
        if normalized_qty > 10000:
            flags['unusually_large'] = True
        
        # Missing supplier
        if not record.get('supplier'):
            flags['missing_supplier'] = True
        
        # Unknown plant code
        if record.get('plant_code') == 'UNKNOWN':
            flags['unknown_plant'] = True
        
        return flags
    
    def _check_utility_suspicious(self, record, normalized_qty):
        """Check for suspicious utility records."""
        flags = {}
        
        # Negative consumption
        if record['quantity'] < 0:
            flags['negative_consumption'] = True
        
        # Very high consumption (>5000 kWh)
        if normalized_qty > 5000:
            flags['unusually_high_consumption'] = True
        
        # Missing meter ID
        if record['meter_id'].startswith('UNKNOWN_METER'):
            flags['missing_meter_id'] = True
        
        # Billing period >45 days (unusual)
        delta = (record['billing_end'] - record['billing_start']).days
        if delta > 45:
            flags['long_billing_period'] = True
        
        return flags
    
    def _check_travel_suspicious(self, record):
        """Check for suspicious travel records."""
        flags = {}
        
        # Missing distance for flights/ground
        if 'distance' in record and not record['distance']:
            flags['missing_distance'] = True
        
        # Very long flight (>10000 km unusual for typical business travel)
        if record.get('distance') and record['distance'] > 10000:
            flags['extremely_long_distance'] = True
        
        # Unknown employee
        if record['employee_id'] == 'UNKNOWN':
            flags['unknown_employee'] = True
        
        return flags
    
    def _calculate_confidence(self, flags):
        """
        Calculate confidence score 0.0-1.0 based on flags.
        Each flag reduces confidence.
        """
        score = 1.0
        
        # Critical flags reduce to 0.5
        critical_flags = [
            'missing_distance',
            'missing_meter_id',
            'unknown_plant',
        ]
        
        for flag in critical_flags:
            if flag in flags and flags[flag]:
                score = 0.5
                break
        
        # Warning flags reduce by 0.1 each
        warning_flags = [
            'negative_quantity',
            'negative_consumption',
            'missing_supplier',
            'unusually_large',
            'unusually_high_consumption',
            'long_billing_period',
            'unknown_employee',
            'extremely_long_distance',
        ]
        
        for flag in warning_flags:
            if flag in flags and flags[flag]:
                score -= 0.1
        
        return max(0.0, score)