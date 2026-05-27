from rest_framework import serializers
from .models import FileUpload


class FileUploadSerializer(serializers.ModelSerializer):
    uploader_name = serializers.CharField(source='uploader.username', read_only=True)
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'source_type', 'file_name', 'file_size',
            'uploaded_at', 'uploader', 'uploader_name',
            'is_processed', 'total_rows', 'successful_rows', 'failed_rows'
        ]
        read_only_fields = [
            'uploaded_at', 'is_processed', 'total_rows',
            'successful_rows', 'failed_rows'
        ]


class FileUploadDetailSerializer(serializers.ModelSerializer):
    uploader = serializers.CharField(source='uploader.username', read_only=True)
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'organization', 'source_type', 'file_name', 'file_size',
            'uploaded_at', 'uploader', 'is_processed',
            'processing_started_at', 'processing_completed_at',
            'total_rows', 'successful_rows', 'failed_rows'
        ]