package com.spongebob.magic_conch_backend.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;
import org.springframework.boot.web.client.RestTemplateBuilder;

// 功能：后端经常需要调用另一个 AI 服务（比如 ChatGPT 接口）。在 Java/Spring 里，
// 最常用的小工具就是 RestTemplate，它专门用来发 HTTP 请求（类似 Postman，但写在代码里）
// service可以通过调用它（比如参数可以传入url和要问的问题）向AI服务的接口发送HTTP请求
@Configuration
public class RestTemplateConfig {

    // 使用 Spring Boot 提供的 RestTemplateBuilder 可以自动继承全局超时、消息转换器等配置。
    @Bean
    public RestTemplate restTemplate(RestTemplateBuilder builder) {
        return builder.build();
    }
} 