#!/usr/bin/env node

// 简单的批量生成测试脚本
import { Config } from './dist/config.js';
import { ImageVideoGenerationClient } from './dist/image-video-generation-client.js';

// 确保设置了API密钥
if (!process.env.IMAGE_VIDEO_GENERATION_API_KEY) {
  console.error('❌ 请设置 IMAGE_VIDEO_GENERATION_API_KEY 环境变量');
  console.log('   export IMAGE_VIDEO_GENERATION_API_KEY="your_api_key"');
  process.exit(1);
}

async function testBatchGeneration() {
  try {
    console.log('🚀 开始测试批量图像生成功能...\n');

    const config = new Config();
    const client = new ImageVideoGenerationClient(config);

    // 测试用例1: 小批量并行生成
    console.log('📝 测试用例1: 小批量并行生成 (3个提示词)');
    const batchParams1 = {
      prompts: [
        '一只可爱的小猫在花园里玩耍',
        '现代城市的夜景，灯火辉煌',
        '一个程序员在电脑前工作'
      ],
      model: 'cogview-3-flash',
      quality: 'standard',
      size: '1024x1024',
      batch_size: 3,
      parallel: true,
      max_concurrent: 2,
      watermark_enabled: false,
      user_id: 'test_user_123456'
    };

    const result1 = await client.generateBatchImages(batchParams1);

    console.log(`✅ 测试1完成!`);
    console.log(`   总提示词: ${result1.total_prompts}`);
    console.log(`   成功生成: ${result1.successful_generations}`);
    console.log(`   生成失败: ${result1.failed_generations}`);
    console.log(`   处理时间: ${(result1.batch_summary.processing_time / 1000).toFixed(2)}秒`);
    console.log(`   成功率: ${((result1.successful_generations / result1.total_prompts) * 100).toFixed(1)}%\n`);

    // 显示成功的图像URL
    const successfulResults = result1.results.filter(r => r.success);
    if (successfulResults.length > 0) {
      console.log('🖼️ 生成的图像URL:');
      successfulResults.forEach((result, index) => {
        if (result.images && result.images.length > 0) {
          console.log(`   ${index + 1}. ${result.prompt.substring(0, 30)}...`);
          result.images.forEach((img, imgIndex) => {
            console.log(`      图像${imgIndex + 1}: ${img.url}`);
          });
        }
      });
      console.log('');
    }

    // 显示失败的提示词
    const failedResults = result1.results.filter(r => !r.success);
    if (failedResults.length > 0) {
      console.log('❌ 失败的提示词:');
      failedResults.forEach((result, index) => {
        console.log(`   ${index + 1}. ${result.prompt}: ${result.error}`);
      });
      console.log('');
    }

    console.log('🎉 批量图像生成功能测试完成！');

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    if (error.code) {
      console.error('   错误代码:', error.code);
    }
    process.exit(1);
  }
}

// 运行测试
testBatchGeneration();