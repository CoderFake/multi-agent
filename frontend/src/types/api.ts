export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ErrorResponse {
  error_code: string;
  detail: string;
  status_code: number;
}

export interface SuccessResponse {
  message: string;
}
