import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { Config } from './config.js';
import {
  ImageGenerationParams,
  VideoGenerationParams,
  AsyncResult,
  ImageGenerationResponse,
  BatchImageGenerationParams,
  BatchImageGenerationResult
} from './config.js';
import { ApiError, NetworkError } from './errors.js';

export class ImageVideoGenerationClient {
  private client: AxiosInstance;
  private config: Config;

  constructor(config: Config) {
    this.config = config;
    this.client = axios.create({
      baseURL: config.baseUrl,
      timeout: config.timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.client.interceptors.request.use((request) => {
      request.headers.Authorization = `Bearer ${this.config.apiKey}`;
      return request;
    });
  }

  private async retryRequest<T>(
    requestFn: () => Promise<T>,
    maxRetries: number = this.config.maxRetries
  ): Promise<T> {
    let lastError: Error;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await requestFn();
      } catch (error) {
        lastError = error as Error;

        if (attempt === maxRetries) {
          break;
        }

        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError!;
  }

  private handleApiError(error: any): never {
    if (error.response) {
      const { status, data } = error.response;
      const message = data?.error?.message || data?.message || 'API request failed';
      throw new ApiError(message, data?.error?.code || 'UNKNOWN_ERROR', status);
    } else if (error.request) {
      throw new NetworkError('Network error: No response received');
    } else {
      throw new NetworkError(`Network error: ${error.message}`);
    }
  }

  async generateImage(params: ImageGenerationParams): Promise<ImageGenerationResponse> {
    const requestConfig: AxiosRequestConfig = {
      method: 'POST',
      url: '/paas/v4/images/generations',
      data: {
        model: params.model || this.config.defaultImageModel,
        prompt: params.prompt,
        quality: params.quality || 'standard',
        size: params.size || '1024x1024',
        watermark_enabled: params.watermark_enabled !== undefined ? params.watermark_enabled : true,
        ...(params.user_id && { user_id: params.user_id }),
      },
    };

    return this.retryRequest(async () => {
      try {
        const response = await this.client.request<ImageGenerationResponse>(requestConfig);
        return response.data;
      } catch (error) {
        this.handleApiError(error);
      }
    });
  }

  async generateVideo(params: VideoGenerationParams): Promise<AsyncResult> {
    const requestConfig: AxiosRequestConfig = {
      method: 'POST',
      url: '/paas/v4/videos/generations',
      data: {
        model: params.model || this.config.defaultVideoModel,
        prompt: params.prompt,
        ...(params.image_url && { image_url: params.image_url }),
        ...(params.quality && { quality: params.quality }),
        ...(params.size && { size: params.size }),
        ...(params.fps && { fps: params.fps }),
        ...(params.duration && { duration: params.duration }),
        ...(params.with_audio !== undefined && { with_audio: params.with_audio }),
        ...(params.watermark_enabled !== undefined && { watermark_enabled: params.watermark_enabled }),
      },
    };

    return this.retryRequest(async () => {
      try {
        const response = await this.client.request<AsyncResult>(requestConfig);
        return response.data;
      } catch (error) {
        this.handleApiError(error);
      }
    });
  }

  async queryAsyncResult(taskId: string): Promise<AsyncResult> {
    const requestConfig: AxiosRequestConfig = {
      method: 'GET',
      url: `/paas/v4/async-result/${taskId}`,
    };

    return this.retryRequest(async () => {
      try {
        const response = await this.client.request<AsyncResult>(requestConfig);
        return response.data;
      } catch (error) {
        this.handleApiError(error);
      }
    });
  }

  async waitForVideoResult(
    taskId: string,
    maxWaitTime: number = 300000,
    pollInterval: number = 5000
  ): Promise<AsyncResult> {
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTime) {
      const result = await this.queryAsyncResult(taskId);

      if (result.task_status === 'SUCCESS') {
        return result;
      }

      if (result.task_status === 'FAIL') {
        throw new ApiError(
          result.error || 'Video generation failed',
          'GENERATION_FAILED'
        );
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new ApiError(
      'Video generation timed out',
      'TIMEOUT_ERROR'
    );
  }

  async generateBatchImages(params: BatchImageGenerationParams): Promise<BatchImageGenerationResult> {
    const {
      prompts,
      model,
      quality,
      size,
      watermark_enabled,
      user_id,
      batch_size = 4,
      parallel = true,
      max_concurrent = 3,
      delay_between_batches = 1000
    } = params;

    if (!prompts || prompts.length === 0) {
      throw new ApiError('At least one prompt is required for batch generation', 'INVALID_PARAMS');
    }

    if (prompts.length > 100) {
      throw new ApiError('Maximum 100 prompts allowed per batch', 'TOO_MANY_PROMPTS');
    }

    const startTime = Date.now();
    const results: BatchImageGenerationResult['results'] = [];
    const batches: string[][] = [];

    // 将提示词分批
    for (let i = 0; i < prompts.length; i += batch_size) {
      batches.push(prompts.slice(i, i + batch_size));
    }

    let successfulGenerations = 0;
    let failedGenerations = 0;

    // 处理批次
    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
      const currentBatch = batches[batchIndex];

      if (parallel) {
        // 并行处理当前批次
        const batchPromises = currentBatch.map(async (prompt) => {
          try {
            const imageParams: ImageGenerationParams = {
              prompt,
              model: model || this.config.defaultImageModel,
              quality: quality || 'standard',
              size: size || '1024x1024',
              watermark_enabled: watermark_enabled !== undefined ? watermark_enabled : true,
              user_id,
            };

            const response = await this.generateImage(imageParams);
            successfulGenerations++;

            return {
              prompt,
              success: true,
              images: response.data,
              created: response.created,
            };
          } catch (error) {
            failedGenerations++;
            return {
              prompt,
              success: false,
              error: error instanceof Error ? error.message : String(error),
            };
          }
        });

        // 限制并发数
        const limitedPromises = [];
        for (let i = 0; i < batchPromises.length; i += max_concurrent) {
          const concurrentBatch = batchPromises.slice(i, i + max_concurrent);
          limitedPromises.push(Promise.all(concurrentBatch));
        }

        const batchResults = await Promise.all(limitedPromises);
        results.push(...batchResults.flat());
      } else {
        // 串行处理
        for (const prompt of currentBatch) {
          try {
            const imageParams: ImageGenerationParams = {
              prompt,
              model: model || this.config.defaultImageModel,
              quality: quality || 'standard',
              size: size || '1024x1024',
              watermark_enabled: watermark_enabled !== undefined ? watermark_enabled : true,
              user_id,
            };

            const response = await this.generateImage(imageParams);
            successfulGenerations++;

            results.push({
              prompt,
              success: true,
              images: response.data,
              created: response.created,
            });
          } catch (error) {
            failedGenerations++;
            results.push({
              prompt,
              success: false,
              error: error instanceof Error ? error.message : String(error),
            });
          }
        }
      }

      // 批次间延迟（除了最后一批）
      if (batchIndex < batches.length - 1 && delay_between_batches > 0) {
        await new Promise(resolve => setTimeout(resolve, delay_between_batches));
      }
    }

    const endTime = Date.now();
    const processingTime = endTime - startTime;

    return {
      total_prompts: prompts.length,
      successful_generations: successfulGenerations,
      failed_generations: failedGenerations,
      results,
      batch_summary: {
        total_batches: batches.length,
        processing_time: processingTime,
        average_time_per_batch: processingTime / batches.length,
      },
    };
  }

  updateConfig(updates: any): void {
    this.config.updateConfig(updates);

    if (updates.timeout) {
      this.client.defaults.timeout = updates.timeout;
    }
  }
}