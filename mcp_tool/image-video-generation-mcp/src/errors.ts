export class ImageVideoGenerationError extends Error {
  constructor(
    message: string,
    public code?: string,
    public statusCode?: number
  ) {
    super(message);
    this.name = 'ImageVideoGenerationError';
  }
}

export class ConfigurationError extends ImageVideoGenerationError {
  constructor(message: string) {
    super(message, 'CONFIG_ERROR');
    this.name = 'ConfigurationError';
  }
}

export class ApiError extends ImageVideoGenerationError {
  constructor(
    message: string,
    public code: string,
    public statusCode?: number
  ) {
    super(message, code, statusCode);
    this.name = 'ApiError';
  }
}

export class NetworkError extends ImageVideoGenerationError {
  constructor(message: string) {
    super(message, 'NETWORK_ERROR');
    this.name = 'NetworkError';
  }
}

export class ValidationError extends ImageVideoGenerationError {
  constructor(message: string) {
    super(message, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
  }
}