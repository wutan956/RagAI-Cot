package com.spongebob.magic_conch_backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

//  AI 服务配置类
// * 作用：将 application.yml / application.properties 中前缀为 ai.service 的配置项
// * 自动映射到当前类的字段上，并通过 getter/setter 提供读取和修改能力。
@Configuration
@ConfigurationProperties(prefix = "ai.service")
public class AiServiceConfig {
    private String host;
    private Integer port;

    public String getHost() {
        return host;
    }

    public void setHost(String host) {
        this.host = host;
    }

    public Integer getPort() {
        return port;
    }

    public void setPort(Integer port) {
        this.port = port;
    }

    // 工具方法：根据 host 和 port 拼接出完整的 HTTP 基础地址
    // 示例：host=127.0.0.1, port=8080 → http://127.0.0.1:8080
    public String getBaseUrl() {
        return String.format("http://%s:%d", host, port);
    }
} 