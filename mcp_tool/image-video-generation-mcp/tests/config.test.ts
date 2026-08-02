import { describe, it, expect, beforeEach } from '@jest/globals';
import { Config } from '../src/config';

describe('Config', () => {
  beforeEach(() => {
    delete process.env.IMAGE_VIDEO_GENERATION_API_KEY;
    delete process.env.IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL;
    delete process.env.IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL;
  });

  it('should create config with API key from parameter', () => {
    const config = new Config({ apiKey: 'test-key' });
    expect(config.apiKey).toBe('test-key');
    expect(config.defaultImageModel).toBe('cogview-3-flash');
    expect(config.defaultVideoModel).toBe('cogvideox-flash');
  });

  it('should create config with API key from environment', () => {
    process.env.IMAGE_VIDEO_GENERATION_API_KEY = 'env-key';
    const config = new Config();
    expect(config.apiKey).toBe('env-key');
  });

  it('should use default values when not provided', () => {
    process.env.IMAGE_VIDEO_GENERATION_API_KEY = 'test-key';
    const config = new Config();
    expect(config.baseUrl).toBe('https://open.bigmodel.cn/api');
    expect(config.defaultImageModel).toBe('cogview-3-flash');
    expect(config.defaultVideoModel).toBe('cogvideox-flash');
    expect(config.timeout).toBe(30000);
    expect(config.maxRetries).toBe(3);
  });

  it('should update config values', () => {
    process.env.IMAGE_VIDEO_GENERATION_API_KEY = 'test-key';
    const config = new Config();

    config.updateConfig({
      defaultImageModel: 'cogview-3-flash',
      timeout: 60000,
    });

    expect(config.defaultImageModel).toBe('cogview-3-flash');
    expect(config.timeout).toBe(60000);
  });

  it('should throw error when no API key provided', () => {
    expect(() => new Config()).toThrow('API Key is required');
  });

  it('should create config with default models from environment', () => {
    process.env.IMAGE_VIDEO_GENERATION_API_KEY = 'test-key';
    process.env.IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL = 'cogview-3-flash';
    process.env.IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL = 'cogvideox-flash';

    const config = new Config();
    expect(config.defaultImageModel).toBe('cogview-3-flash');
    expect(config.defaultVideoModel).toBe('cogvideox-flash');
  });

  it('should use parameter models over environment variables', () => {
    process.env.IMAGE_VIDEO_GENERATION_API_KEY = 'test-key';
    process.env.IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL = 'cogview-3-flash';
    process.env.IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL = 'cogvideox-flash';

    const config = new Config({
      defaultImageModel: 'cogview-4',
      defaultVideoModel: 'cogvideox-3'
    });
    expect(config.defaultImageModel).toBe('cogview-4');
    expect(config.defaultVideoModel).toBe('cogvideox-3');
  });
});