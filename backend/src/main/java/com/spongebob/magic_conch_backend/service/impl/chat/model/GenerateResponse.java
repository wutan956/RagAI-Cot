package com.spongebob.magic_conch_backend.service.impl.chat.model;

// 用于存放“单句生成”接口返回的数据模型
// 当后端调用外部 AI 接口时，AI 返回的 JSON 形如：
// *    {
// *      "generated_text": "你好，世界！"
// *    }
// * Spring 的 HttpMessageConverter（如 Jackson）会自动把 JSON 字段
// *    "generated_text" 绑定到同名 Java 属性 generated_text 上。
// * 类名 GenerateResponse 只在本服务内部使用，与外部字段名无关。
public class GenerateResponse {
    private String generated_text;

    public String getGenerated_text() {
        return generated_text;
    }

    public void setGenerated_text(String generated_text) {
        this.generated_text = generated_text;
    }
}
