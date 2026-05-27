from decimal import Decimal
from django.db.models import Sum
from apps.emissions.models import EmissionRecord


class EmissionCalculator:
    """Calculate and aggregate emissions"""
    
    # Emission factors (kg CO2e per unit)
    FACTORS = {
        'FUEL_DIESEL': Decimal('2.68'),
        'FUEL_PETROL': Decimal('2.31'),
        'FUEL_CNG': Decimal('1.75'),
        'FUEL_LPG': Decimal('1.60'),
        'ELECTRICITY': Decimal('0.71'),
        'TRAVEL_FLIGHT': Decimal('0.128'),
        'TRAVEL_HOTEL': Decimal('25.0'),
        'TRAVEL_GROUND': Decimal('0.089'),
    }
    
    @staticmethod
    def calculate_record_emissions(category, value, unit):
        """Calculate emissions for a single value"""
        factor = EmissionCalculator.FACTORS.get(category, Decimal('0'))
        return value * factor
    
    @staticmethod
    def total_emissions_by_scope(organization):
        """Calculate total emissions by scope"""
        scopes = {}
        
        for scope in ['SCOPE_1', 'SCOPE_2', 'SCOPE_3']:
            total = EmissionRecord.objects.filter(
                organization=organization,
                scope=scope,
                review_status='APPROVED'
            ).aggregate(
                total=Sum('calculated_emissions')
            )['total'] or Decimal('0')
            
            scopes[scope] = float(total)
        
        return scopes
    
    @staticmethod
    def total_emissions_by_category(organization):
        """Calculate total emissions by category"""
        categories = {}
        
        for record in EmissionRecord.objects.filter(
            organization=organization,
            review_status='APPROVED'
        ).values('category').annotate(
            total=Sum('calculated_emissions')
        ):
            categories[record['category']] = float(record['total'])
        
        return categories
    
    @staticmethod
    def total_emissions_by_date_range(organization, start_date, end_date):
        """Calculate emissions for date range"""
        queryset = EmissionRecord.objects.filter(
            organization=organization,
            activity_date__gte=start_date,
            activity_date__lte=end_date,
            review_status='APPROVED'
        )
        
        total = queryset.aggregate(
            total=Sum('calculated_emissions')
        )['total'] or Decimal('0')
        
        by_date = {}
        for record in queryset.values('activity_date').annotate(
            total=Sum('calculated_emissions')
        ):
            by_date[str(record['activity_date'])] = float(record['total'])
        
        return {
            'total': float(total),
            'by_date': by_date
        }
    
    @staticmethod
    def emissions_intensity(organization):
        """Calculate emissions per unit activity"""
        # This would depend on business context
        # E.g., emissions per employee, per facility, per revenue unit
        pass
    
    @staticmethod
    def carbon_reduction_potential(organization):
        """Identify reduction opportunities"""
        # Analyze high-emission categories
        # Identify inefficient records
        # Suggest optimization areas
        pass
    
    @staticmethod
    def baseline_comparison(organization, baseline_date):
        """Compare current vs baseline emissions"""
        # Calculate emissions before baseline
        # Calculate emissions after baseline
        # Return variance
        pass