export interface VerificationForm {
  brand_name: string;
  product_class: string;
  alcohol_content: string;
  net_contents?: string | null;
  product_type: 'spirits' | 'wine' | 'beer';
  require_gov_warning: boolean;
}

export interface FieldCheck {
  field: string;
  status: 'MATCH' | 'MISMATCH' | 'MISSING' | 'ERROR';
  message: string;
  evidence?: string;
  confidence?: number;
}

export interface VerificationResponse {
  status: 'PASS' | 'FAIL';
  duration_ms: number;
  checks: FieldCheck[];
  ocr_tokens: string[];
  raw_ocr_text: string;
}
