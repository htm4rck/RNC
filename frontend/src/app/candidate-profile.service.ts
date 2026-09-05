import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { apiUrl } from './api-url';
import { CandidateProfile, CandidateProfileCreate } from './candidate-profile.model';

@Injectable({ providedIn: 'root' })
export class CandidateProfileService {
  constructor(private readonly http: HttpClient) {}

  list(): Observable<CandidateProfile[]> {
    return this.http.get<CandidateProfile[]>(apiUrl('/candidate-profiles'));
  }

  create(payload: CandidateProfileCreate): Observable<CandidateProfile> {
    return this.http.post<CandidateProfile>(apiUrl('/candidate-profiles'), payload);
  }
}
