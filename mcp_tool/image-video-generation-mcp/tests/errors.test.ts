import { describe, it, expect } from '@jest/globals';
import {
  ImageVideoGenerationError,
  ConfigurationError,
  ApiError,
  NetworkError,
  ValidationError
} from '../src/errors';

describe('Errors', () => {
  it('should create ImageVideoGenerationError with message', () => {
    const error = new ImageVideoGenerationError('Test error');
    expect(error.message).toBe('Test error');
    expect(error.name).toBe('ImageVideoGenerationError');
  });

  it('should create ImageVideoGenerationError with code and status', () => {
    const error = new ImageVideoGenerationError('Test error', 'TEST_CODE', 400);
    expect(error.message).toBe('Test error');
    expect(error.code).toBe('TEST_CODE');
    expect(error.statusCode).toBe(400);
    expect(error.name).toBe('ImageVideoGenerationError');
  });

  it('should create ConfigurationError', () => {
    const error = new ConfigurationError('Config error');
    expect(error.message).toBe('Config error');
    expect(error.code).toBe('CONFIG_ERROR');
    expect(error.name).toBe('ConfigurationError');
  });

  it('should create ApiError', () => {
    const error = new ApiError('API error', 'API_ERROR', 500);
    expect(error.message).toBe('API error');
    expect(error.code).toBe('API_ERROR');
    expect(error.statusCode).toBe(500);
    expect(error.name).toBe('ApiError');
  });

  it('should create NetworkError', () => {
    const error = new NetworkError('Network failed');
    expect(error.message).toBe('Network failed');
    expect(error.code).toBe('NETWORK_ERROR');
    expect(error.name).toBe('NetworkError');
  });

  it('should create ValidationError', () => {
    const error = new ValidationError('Invalid input');
    expect(error.message).toBe('Invalid input');
    expect(error.code).toBe('VALIDATION_ERROR');
    expect(error.name).toBe('ValidationError');
  });
});