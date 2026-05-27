from datetime import datetime
import tempfile
from apps.emissions.models import DataSource, RawRecord, EmissionRecord
from services.sap_parser import SAPParser
from services.utility_parser import UtilityParser
from services.travel_parser import TravelParser
from services.normalizer import Normalizer


def process_upload_file(file_upload, uploaded_file, user):
    """
    Process uploaded file through pipeline
    """
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    
    # Create DataSource
    data_source = DataSource.objects.create(
        organization=file_upload.organization,
        source_type=file_upload.source_type,
        uploaded_by=user,
        raw_file_name=file_upload.file_name,
        raw_file_size=file_upload.file_size
    )
    
    # Parse based on source type
    parser = get_parser(file_upload.source_type)
    parsed_records = parser.parse(tmp_path)
    
    # Normalize and create records
    normalizer = Normalizer()
    emission_records = []
    raw_records = []
    failed = 0
    
    for parsed in parsed_records:
        try:
            # Create raw record
            raw = RawRecord.objects.create(
                data_source=data_source,
                raw_json=parsed,
                processing_status='NORMALIZED'
            )
            
            # Normalize
            normalized = normalize_record(
                file_upload.source_type,
                parsed,
                normalizer
            )
            
            # Create emission record
            emission = EmissionRecord.objects.create(
                organization=file_upload.organization,
                raw_record=raw,
                data_source=data_source,
                scope=normalized['scope'],
                category=normalized['category'],
                activity_date=normalized['activity_date'],
                normalized_value=normalized['normalized_value'],
                normalized_unit=normalized['normalized_unit'],
                original_unit=normalized.get('original_unit'),
                emission_factor=normalized['emission_factor'],
                calculated_emissions=normalized['calculated_emissions'],
                confidence_score=normalized['confidence_score'],
                suspicious_flags=normalized['suspicious_flags'],
                review_status='FLAGGED' if normalized['suspicious_flags'] else 'PENDING',
            )
            emission_records.append(emission)
            
        except Exception as e:
            failed += 1
            RawRecord.objects.create(
                data_source=data_source,
                raw_json=parsed,
                processing_status='FAILED',
                error_message=str(e)
            )
    
    # Update file_upload
    file_upload.total_rows = len(parsed_records)
    file_upload.successful_rows = len(emission_records)
    file_upload.failed_rows = failed
    file_upload.is_processed = True
    file_upload.processing_completed_at = datetime.now()
    file_upload.save()
    
    return {
        'message': 'File processed successfully',
        'total_rows': file_upload.total_rows,
        'successful_rows': file_upload.successful_rows,
        'failed_rows': file_upload.failed_rows,
    }


def get_parser(source_type):
    """Get appropriate parser for source type"""
    if source_type == 'SAP':
        return SAPParser()
    elif source_type == 'UTILITY':
        return UtilityParser()
    elif source_type == 'TRAVEL':
        return TravelParser()
    raise ValueError(f'Unknown source type: {source_type}')


def normalize_record(source_type, parsed, normalizer):
    """Normalize record based on source type"""
    if source_type == 'SAP':
        return normalizer.normalize_sap_record(parsed)
    elif source_type == 'UTILITY':
        return normalizer.normalize_utility_record(parsed)
    elif source_type == 'TRAVEL':
        return normalizer.normalize_travel_record(parsed)
    raise ValueError(f'Unknown source type: {source_type}')