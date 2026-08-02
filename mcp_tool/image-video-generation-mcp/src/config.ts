export interface ImageVideoGenerationConfig {
  apiKey: string;
  baseUrl?: string;
  defaultImageModel?: string;
  defaultVideoModel?: string;
  timeout?: number;
  maxRetries?: number;
}

export interface ImageGenerationParams {
  model?: string;
  prompt: string;
  quality?: 'standard' | 'hd';
  size?: string;
  watermark_enabled?: boolean;
  user_id?: string;
}

export interface VideoGenerationParams {
  model?: string;
  prompt: string;
  image_url?: string | string[];
  quality?: 'speed' | 'quality';
  size?: string;
  fps?: 30 | 60;
  duration?: 5 | 10;
  with_audio?: boolean;
  watermark_enabled?: boolean;
}

export interface AsyncResult {
  id?: string;                  // 视频生成时的任务ID，用于查询结果
  request_id?: string;
  task_status: 'PROCESSING' | 'SUCCESS' | 'FAIL';
  video_result?: Array<{
    url: string;
    cover_image_url?: string;
  }>;
  video_results?: Array<{
    url: string;
    cover_image_url?: string;
  }>;
  error?: string;
  choices?: Array<any>;
  created?: number;
  model?: string;
  usage?: {
    completion_tokens?: number;
    prompt_tokens?: number;
    total_tokens?: number;
  };
}

export interface ImageGenerationResponse {
  created: number;
  data: Array<{
    url: string;
    revised_prompt?: string;
  }>;
  content_filter: {
    role: string;
    level: number;
  };
}

export interface BatchImageGenerationParams {
  prompts: string[];
  model?: string;
  quality?: 'standard' | 'hd';
  size?: string;
  watermark_enabled?: boolean;
  user_id?: string;
  batch_size?: number;
  parallel?: boolean;
  max_concurrent?: number;
  delay_between_batches?: number;
}

export interface BatchImageGenerationResult {
  total_prompts: number;
  successful_generations: number;
  failed_generations: number;
  results: Array<{
    prompt: string;
    success: boolean;
    images?: Array<{
      url: string;
      revised_prompt?: string;
    }>;
    error?: string;
    created?: number;
  }>;
  batch_summary: {
    total_batches: number;
    processing_time: number;
    average_time_per_batch: number;
  };
}

export class Config {
  private config: ImageVideoGenerationConfig;

  constructor(config?: Partial<ImageVideoGenerationConfig>) {
    this.config = {
      apiKey: config?.apiKey || this.getEnvVar('IMAGE_VIDEO_GENERATION_API_KEY') || '',
      baseUrl: config?.baseUrl || 'https://open.bigmodel.cn/api',
      defaultImageModel: config?.defaultImageModel || this.getEnvVar('IMAGE_VIDEO_GENERATION_DEFAULT_IMAGE_MODEL') || 'cogview-3-flash',
      defaultVideoModel: config?.defaultVideoModel || this.getEnvVar('IMAGE_VIDEO_GENERATION_DEFAULT_VIDEO_MODEL') || 'cogvideox-flash',
      timeout: config?.timeout || 30000,
      maxRetries: config?.maxRetries || 3,
      ...config,
    };

    if (!this.config.apiKey) {
      console.error('❌ MCP Server Configuration Error:');
      console.error('   API Key is required but not provided.');
      console.error('   Please set the IMAGE_VIDEO_GENERATION_API_KEY environment variable.');
      console.error('   Example: IMAGE_VIDEO_GENERATION_API_KEY=your_api_key npx image-video-generation-mcp');
      throw new Error('API Key is required. Set IMAGE_VIDEO_GENERATION_API_KEY environment variable or pass in config.');
    }
  }

  private getEnvVar(key: string): string | undefined {
    return process.env[key];
  }

  get apiKey(): string {
    return this.config.apiKey;
  }

  get baseUrl(): string {
    return this.config.baseUrl!;
  }

  get defaultImageModel(): string {
    return this.config.defaultImageModel!;
  }

  get defaultVideoModel(): string {
    return this.config.defaultVideoModel!;
  }

  get timeout(): number {
    return this.config.timeout!;
  }

  get maxRetries(): number {
    return this.config.maxRetries!;
  }

  updateConfig(updates: Partial<ImageVideoGenerationConfig>): void {
    this.config = { ...this.config, ...updates };
  }
}