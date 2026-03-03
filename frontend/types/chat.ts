export interface UploadedDoc {
  doc_id: string;
  file_name: string;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  engine?: string;
}
