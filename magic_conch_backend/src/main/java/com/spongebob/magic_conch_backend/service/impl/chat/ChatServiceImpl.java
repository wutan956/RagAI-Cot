package com.spongebob.magic_conch_backend.service.impl.chat;

import com.spongebob.magic_conch_backend.config.AiServiceConfig; // 前面自己写的那个类，读取 AI 服务的 host/port
import com.spongebob.magic_conch_backend.service.ChatService;
import com.spongebob.magic_conch_backend.service.impl.chat.model.GenerateResponse;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.client.RestTemplate;

// 把前端传来的 prompt 透传给远程 AI 服务，并把 AI 返回的内容再返给上层
@Service
public class ChatServiceImpl implements ChatService {
    
    @Autowired
    private RestTemplate restTemplate;
    
    @Autowired
    private AiServiceConfig aiServiceConfig;

    @Override
    public String callAiForOneReply(String prompt) {
        // 获取基础URL http://localhost:8000
        String baseUrl = aiServiceConfig.getBaseUrl();
        // 构建完整的请求URL http://localhost:8000/generate?prompt=XXX
        String url = String.format("%s/generate?prompt=%s", baseUrl, prompt);
        // 发送GET请求并获取响应
        GenerateResponse response = restTemplate.getForObject(url, GenerateResponse.class);
        // 从响应中取出 generated_text 字段值返回
        return response != null ? response.getGenerated_text() : "";
    }
}
