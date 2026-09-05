import { Component } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterOutlet } from '@angular/router';
import { finalize } from 'rxjs';

import { CandidateProfile } from './candidate-profile.model';
import { CandidateProfileService } from './candidate-profile.service';

@Component({
  selector: 'rcn-root',
  imports: [ReactiveFormsModule, RouterOutlet],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  readonly profileForm = this.formBuilder.nonNullable.group({
    full_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(160)]],
    headline: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(220)]],
    country: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]],
    years_experience: [5, [Validators.required, Validators.min(0), Validators.max(60)]],
    english_level: ['Intermediate', [Validators.required, Validators.minLength(2), Validators.maxLength(40)]],
  });

  profiles: CandidateProfile[] = [];
  loadingProfiles = true;
  savingProfile = false;
  errorMessage = '';

  constructor(
    private readonly formBuilder: FormBuilder,
    private readonly candidateProfileService: CandidateProfileService,
  ) {
    this.loadProfiles();
  }

  loadProfiles(): void {
    this.loadingProfiles = true;
    this.errorMessage = '';

    this.candidateProfileService
      .list()
      .pipe(finalize(() => (this.loadingProfiles = false)))
      .subscribe({
        next: (profiles) => {
          this.profiles = profiles;
        },
        error: () => {
          this.errorMessage = 'No se pudieron cargar los perfiles.';
        },
      });
  }

  createProfile(): void {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }

    this.savingProfile = true;
    this.errorMessage = '';

    this.candidateProfileService
      .create(this.profileForm.getRawValue())
      .pipe(finalize(() => (this.savingProfile = false)))
      .subscribe({
        next: (profile) => {
          this.profiles = [profile, ...this.profiles];
          this.profileForm.reset({
            full_name: '',
            headline: '',
            country: '',
            years_experience: 5,
            english_level: 'Intermediate',
          });
        },
        error: () => {
          this.errorMessage = 'No se pudo guardar el perfil.';
        },
      });
  }
}
