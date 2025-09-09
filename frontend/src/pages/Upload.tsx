import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQueryClient } from 'react-query';
import { apiClient } from '../api/client';
import { Upload as UploadIcon, FileText, AlertCircle, CheckCircle } from 'lucide-react';

const Upload: React.FC = () => {
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation(
    (formData: FormData) => apiClient.upload('/invoices/', formData),
    {
      onSuccess: () => {
        setUploadStatus('success');
        queryClient.invalidateQueries('dashboard');
        queryClient.invalidateQueries('invoices');
        setTimeout(() => setUploadStatus(''), 3000);
      },
      onError: (error: any) => {
        setUploadStatus('error');
        console.error('Upload failed:', error);
        setTimeout(() => setUploadStatus(''), 3000);
      },
    }
  );

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadedFiles(acceptedFiles);
    setUploadStatus('uploading');
    
    acceptedFiles.forEach((file) => {
      const formData = new FormData();
      formData.append('file', file);
      uploadMutation.mutate(formData);
    });
  }, [uploadMutation]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png', '.tiff', '.bmp'],
      'application/json': ['.json'],
    },
    multiple: true,
  });

  const getStatusIcon = () => {
    switch (uploadStatus) {
      case 'uploading':
        return <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>;
      case 'success':
        return <CheckCircle className="h-8 w-8 text-green-600" />;
      case 'error':
        return <AlertCircle className="h-8 w-8 text-red-600" />;
      default:
        return <UploadIcon className="h-8 w-8 text-gray-400" />;
    }
  };

  const getStatusMessage = () => {
    switch (uploadStatus) {
      case 'uploading':
        return 'Processing invoice...';
      case 'success':
        return 'Invoice processed successfully!';
      case 'error':
        return 'Failed to process invoice. Please try again.';
      default:
        return 'Drag and drop files here, or click to select files';
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Invoices</h1>
        <p className="text-gray-600">Upload invoice files for AI-powered fraud detection</p>
      </div>

      <div className="card">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-blue-400 bg-blue-50'
              : uploadStatus === 'success'
              ? 'border-green-400 bg-green-50'
              : uploadStatus === 'error'
              ? 'border-red-400 bg-red-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center space-y-4">
            {getStatusIcon()}
            <div>
              <p className="text-lg font-medium text-gray-900">
                {getStatusMessage()}
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Supports PDF, JPG, PNG, TIFF, BMP, and JSON files
              </p>
            </div>
          </div>
        </div>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Uploaded Files</h3>
          <div className="space-y-2">
            {uploadedFiles.map((file, index) => (
              <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                <FileText className="h-5 w-5 text-gray-400" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <div className="text-sm text-gray-500">
                  {uploadStatus === 'uploading' && 'Processing...'}
                  {uploadStatus === 'success' && 'Completed'}
                  {uploadStatus === 'error' && 'Failed'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Guidelines</h3>
        <div className="space-y-3 text-sm text-gray-600">
          <div className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Ensure invoices are clear and readable</span>
          </div>
          <div className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Supported formats: PDF, JPG, PNG, TIFF, BMP, JSON</span>
          </div>
          <div className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Maximum file size: 16MB per file</span>
          </div>
          <div className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Multiple files can be uploaded simultaneously</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
