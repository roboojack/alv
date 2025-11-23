import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { VerificationResponse } from './models';

const API_BASE = (window as { __ALV_API__?: string }).__ALV_API__ ?? '/api';

@Injectable({ providedIn: 'root' })
export class VerificationService {
  constructor(private readonly http: HttpClient) {}

  verify(formData: FormData): Observable<VerificationResponse> {
    return this.http
      .post<VerificationResponse>(`${API_BASE}/verify`, formData)
      .pipe(map((payload) => ({ ...payload, duration_ms: Math.round(payload.duration_ms) })));
  }
}
