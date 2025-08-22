package com.spongebob.magic_conch_backend.controller.chat;

import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.spongebob.magic_conch_backend.DAO.WindowChat;
import com.spongebob.magic_conch_backend.common.enums.ResultCode;
import com.spongebob.magic_conch_backend.common.vo.Result;
import com.spongebob.magic_conch_backend.service.ChatService;

import com.spongebob.magic_conch_backend.service.windowChatService;
import io.micrometer.common.util.StringUtils;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import com.spongebob.magic_conch_backend.DAO.windowChatRepository;

import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
// 组合注解：@Controller + @ResponseBody，返回 JSON 而不是视图
// 统一前缀：所有方法访问路径都以 /chat 开头
@RestController
@RequestMapping(value = "/chat")
public class ChatController {

    @Autowired
    private ChatService chatService;
    @Autowired
    private windowChatService windowChatService;
    @Autowired
    private ChatClient chatClient;

    // 前端页面初始化时，从后端获取所有窗口的name
    @GetMapping("/list")
    public Result listWindows() {
        List<WindowChat> list = windowChatService.listAll();
        // 判空 + 控制台打印
        if (list == null || list.isEmpty()) {
            System.out.println("窗口列表为空");
        } else {
            System.out.println("窗口列表条数：" + list.size());
        }
        List<Map<String, ? extends Serializable>> vo = list.stream()
                .map(w -> Map.of("id", w.getId(), "name", w.getName()))
                .collect(Collectors.toList());
        return Result.success(vo);
    }

    // get每个窗口的name，返回它对应的text
    // 记住这种写法，参数是通过name?某某某这样传进来的，就得用这种；如果是name/123这种简单的就用小项目的那种
    @GetMapping("/text")
    public Result getText(@RequestParam String name)  {
        String text = windowChatService.getTextByName(name);
        return Result.success(text);
    }

    //新增一个post的接口，用于创建新的窗口
    // 前端传入json字串，提取里面的name
    @PostMapping("/create")
    public Result createWindow(@RequestParam String name){
        // 如果成功，那么开始在数据库创建一个新的行
        windowChatService.createNewWindow(name);
        return Result.success();
    }

    // RequestMapping没有指定 method，默认同时接受 GET、POST、PUT、DELETE、PATCH 等所有 HTTP 方法。
    // 例如使用GET方法，传入的url就是 /chat/generate?prompt=你好
    @RequestMapping("/generate")
    @ResponseBody
    public Result generate(@RequestBody Map<String, String> body) {
        String name   = body.get("name");
        String prompt = body.get("prompt");
        System.out.println(name);
        System.out.println(prompt);
        // 获得当前name对应窗口的text
        String text = windowChatService.getTextByName(name);
        System.out.println(text);
        // 创建一个统一的返回格式（Result文件里面的类，包含 code msg data）
        Result result = Result.success();
        // prompt 为空或纯空白时报错
        if(StringUtils.isBlank(prompt)) {
            return Result.error(ResultCode.PARAM_INVALID,"prompt不能为空");
        }
        try {
            // 将prompt和历史会话弄成json类型，一口气传给vllm的模型
            ObjectMapper mapper = new ObjectMapper();
            ArrayList<Message> messages = new ArrayList<>();
            JavaType type = mapper.getTypeFactory().constructCollectionType(List.class, LinkedHashMap.class);
            if (StringUtils.isNotBlank(text)) {
                List<LinkedHashMap<String,String>> list = mapper.readValue(text, type);
                for(LinkedHashMap<String,String> m : list) {
                    String role = m.get("role");
                    String content = m.get("content");
                    if("user".equals(role)) {
                        messages.add(new UserMessage(content));
                    } else if ("assistant".equals(role)) {
                        messages.add(new AssistantMessage(content));
                    }
                }
            }
            messages.add(new UserMessage(prompt));
            // 如果是vllm直接终端启动的话，就换成这个命令, vllm的回复前面有<think> </think> 得去掉
            String res = chatClient.prompt().messages(messages).call().content();
            res = res.replaceFirst("(?s)^.*?</think>\\s*", "");
            // 先拼用户问题
            if (StringUtils.isBlank(text)) {
                text = "[]";
                text = text.substring(0, text.length() - 1);
                // 注意这里没有逗号，不然格式就错了
                text += "{\"role\":\"user\",\"content\":\"" + prompt.replace("\"", "\\\"") + "\"}";
            }
            else{
                text = text.substring(0, text.length() - 1);
                text += ",{\"role\":\"user\",\"content\":\"" + prompt.replace("\"", "\\\"") + "\"}";
            }
            // 再拼 AI 回复
            String safe = res.replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r");
            text += ",{\"role\":\"assistant\",\"content\":\"" + safe + "\"}]";
            System.out.println(safe);
            // 修改数据库
            windowChatService.updateText(text, name);
            result.setData(res);
        } catch (Exception e) {
            // 打印异常堆栈（控制台）
            e.printStackTrace();
            result = Result.error();
        }
        return result;
    }
    //新增一个delete接口，用于根据name删除窗口,但是name是用json传的，所以得用RequestBody
    @DeleteMapping("/delete")
    public void deleteWindow(@RequestBody Map<String, String> body){
        String name = body.get("name");
        windowChatService.deleteWindowByName(name);
    }

    // 试一下vllm的方式，用stringAI
    @GetMapping("/vllm")
    public String vllm(@RequestParam String prompt){
        System.out.println(prompt);
        return chatClient.prompt(prompt).call().content();
    }


}
