import { CommonModule } from '@angular/common';
import { Component, OnDestroy, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { FieldCheck, VerificationForm, VerificationResponse } from './models';
import { VerificationService } from './verification.service';

interface SubmissionHistoryItem {
  timestamp: Date;
  status: 'PASS' | 'FAIL';
  brand: string;
  duration: number;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnDestroy {
  readonly title = 'Alcohol Label Verifier';
  private readonly fb = inject(FormBuilder);

  readonly form = this.fb.group({
    brand_name: ['', [Validators.required, Validators.minLength(2)]],
    product_class: ['', [Validators.required]],
    alcohol_content: ['', [Validators.required, Validators.pattern(/^[0-9]+(\.[0-9]+)?%?$/)]],
    net_contents: [''],
    product_type: ['spirits'],
    require_gov_warning: [true]
  });

  selectedFile?: File;
  previewUrl?: string;
  isDragging = false;
  isSubmitting = false;
  status?: 'PASS' | 'FAIL';
  durationMs?: number;
  checks: FieldCheck[] = [];
  ocrTokens: string[] = [];
  rawOcrText = '';
  errorMessage?: string;
  history: SubmissionHistoryItem[] = [];

  private readonly successAudio = new Audio('assets/audio/success-chime.wav');
  private readonly failureAudio = new Audio('assets/audio/failure-buzzer.wav');
  private objectUrl?: string;

  readonly fixtures: Record<string, Partial<VerificationForm> & { image: string }> = {
    trey: {
      brand_name: "Trey Herring's",
      product_class: 'Carolina Bourbon Whiskey',
      alcohol_content: '45%',
      image: 'trey_herring.png'
    },
    ringside: {
      brand_name: 'Quality Distillers',
      product_class: 'Kentucky Straight Bourbon Whiskey',
      alcohol_content: '45%',
      image: 'ringside_bourbon.jpg'
    },
    sylphide: {
      brand_name: 'La Sylphide',
      product_class: 'Bourbon Whiskey',
      alcohol_content: '45%',
      image: 'la_sylphide.jpg'
    },
    bacardi: {
      brand_name: 'Bacardi Gold',
      product_class: 'Rum',
      alcohol_content: '40%',
      image: 'bacardi_gold.jpg'
    },
    mogen: {
      brand_name: 'Mogen David',
      product_class: 'Blackberry Wine',
      alcohol_content: '10%',
      image: 'mogen_david.jpg'
    },
    eandj: {
      brand_name: 'E & J',
      product_class: 'American Brandy',
      alcohol_content: '40%',
      image: 'e_and_j_brandy.jpg'
    },
    cactus: {
      brand_name: 'Cactus Jack',
      product_class: 'Tequila',
      alcohol_content: '40%',
      image: 'cactus_jack.jpg'
    },
    canadian: {
      brand_name: 'Canadian Mist',
      product_class: 'Canadian Whisky',
      alcohol_content: '40%',
      image: 'canadian_mist.jpg'
    },
    dekuyper: {
      brand_name: 'DeKuyper Anisette',
      product_class: 'Anisette Liqueur',
      alcohol_content: '30%',
      image: 'dekuyper_anisette.jpg'
    }
  };

  constructor(private readonly verifier: VerificationService) {}

  ngOnDestroy(): void {
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
    }
  }

  get canSubmit(): boolean {
    return this.form.valid && !!this.selectedFile && !this.isSubmitting;
  }

  handleFileChange(event: Event): void {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) {
      this.selectedFile = undefined;
      this.previewUrl = undefined;
      return;
    }
    this.selectedFile = file;
    this.previewFile(file);
  }

  dropFile(file: File): void {
    this.selectedFile = file;
    this.previewFile(file);
  }

  handleDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = true;
  }

  handleDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
  }

  handleDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      this.dropFile(file);
    }
  }

  private previewFile(file: File): void {
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
    }
    this.objectUrl = URL.createObjectURL(file);
    this.previewUrl = this.objectUrl;
  }

  clearAttachment(): void {
    this.selectedFile = undefined;
    this.previewUrl = undefined;
  }

  resetForm(): void {
    this.form.reset({
      brand_name: '',
      product_class: '',
      alcohol_content: '',
      net_contents: '',
      product_type: 'spirits',
      require_gov_warning: true
    });
    this.status = undefined;
    this.durationMs = undefined;
    this.checks = [];
    this.ocrTokens = [];
    this.rawOcrText = '';
    this.errorMessage = undefined;
    this.clearAttachment();
  }

  submit(): void {
    if (!this.form.valid) {
      this.form.markAllAsTouched();
      this.errorMessage = 'Please fill in all required fields.';
      return;
    }
    if (!this.selectedFile) {
      this.errorMessage = 'Attach a label image to continue.';
      return;
    }
    this.errorMessage = undefined;
    this.isSubmitting = true;
    const payload: VerificationForm = {
      ...(this.form.getRawValue() as VerificationForm),
      net_contents: this.form.value.net_contents?.trim() || null
    };
    const formData = new FormData();
    formData.append('form_payload', JSON.stringify(payload));
    formData.append('image', this.selectedFile, this.selectedFile.name);

    this.verifier.verify(formData).subscribe({
      next: (response) => this.handleSuccess(response, payload.brand_name),
      error: (err) => {
        this.errorMessage = err?.error?.detail ?? 'Verification failed. Please retry.';
        this.isSubmitting = false;
        this.playAudio('FAIL');
      }
    });
  }

  private handleSuccess(response: VerificationResponse, brand: string): void {
    this.isSubmitting = false;
    this.status = response.status;
    this.durationMs = response.duration_ms;
    this.checks = response.checks;
    this.ocrTokens = response.ocr_tokens;
    this.rawOcrText = response.raw_ocr_text;
    this.history.unshift({ timestamp: new Date(), status: response.status, brand, duration: response.duration_ms });
    this.history = this.history.slice(0, 5);
    this.playAudio(response.status);
  }

  private playAudio(state: 'PASS' | 'FAIL'): void {
    const audio = state === 'PASS' ? this.successAudio : this.failureAudio;
    audio.currentTime = 0;
    void audio.play();
  }

  badgeClassFor(check: FieldCheck): string {
    switch (check.status) {
      case 'MATCH':
        return 'pill pill--pass';
      case 'MISMATCH':
        return 'pill pill--fail';
      case 'MISSING':
        return 'pill pill--warn';
      default:
        return 'pill';
    }
  }

  classForStatus(): string {
    return this.status === 'PASS' ? 'status-chip status-chip--pass' : 'status-chip status-chip--fail';
  }

  async useFixture(key: string): Promise<void> {
    const fixture = this.fixtures[key];
    if (!fixture) return;

    this.form.patchValue(fixture);

    if (fixture.image) {
      try {
        const response = await fetch(`assets/fixtures/${fixture.image}`);
        const blob = await response.blob();
        const file = new File([blob], fixture.image, { type: blob.type });
        this.dropFile(file);
      } catch (error) {
        console.error('Failed to load fixture image', error);
      }
    }
  }
}
