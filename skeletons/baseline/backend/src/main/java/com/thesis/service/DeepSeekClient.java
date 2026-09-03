package com.thesis.service;

import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.deepseek.DeepSeekChatModel;
import org.springframework.ai.deepseek.DeepSeekChatOptions;
import org.springframework.ai.deepseek.api.DeepSeekApi;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * DeepSeek 对话入口（Spring AI {@link DeepSeekChatModel}）。
 * Key 仅读环境变量 / 系统属性；无 Key 或调用失败由上层回落 FAQ。
 * 禁止另写一套 HTTP 客户端或第二套 LLM 调用。
 */
public final class DeepSeekClient {

    private DeepSeekClient() {}

    public static boolean configured() {
        String key = apiKey();
        return key != null && !key.isBlank();
    }

    public static String apiKey() {
        String k = System.getenv("DEEPSEEK_API_KEY");
        if (k == null || k.isBlank()) {
            k = System.getProperty("DEEPSEEK_API_KEY", "");
        }
        return k == null ? "" : k.trim();
    }

    public static String baseUrl() {
        String u = System.getenv("DEEPSEEK_BASE_URL");
        if (u == null || u.isBlank()) {
            u = System.getProperty("DEEPSEEK_BASE_URL", "https://api.deepseek.com");
        }
        u = u.trim();
        while (u.endsWith("/")) u = u.substring(0, u.length() - 1);
        return u.isBlank() ? "https://api.deepseek.com" : u;
    }

    public static String model() {
        String m = System.getenv("DEEPSEEK_MODEL");
        if (m == null || m.isBlank()) {
            m = System.getProperty("DEEPSEEK_MODEL", "deepseek-chat");
        }
        m = m.trim();
        return m.isBlank() ? "deepseek-chat" : m;
    }

    /**
     * @param messages 每项含 role/content（system|user|assistant）
     * @return 助手文本；失败返回 null
     */
    public static String chat(List<Map<String, String>> messages) {
        if (!configured() || messages == null || messages.isEmpty()) return null;
        try {
            DeepSeekApi api = DeepSeekApi.builder()
                    .apiKey(apiKey())
                    .baseUrl(baseUrl())
                    .build();
            DeepSeekChatOptions options = DeepSeekChatOptions.builder()
                    .model(model())
                    .temperature(0.7)
                    .build();
            DeepSeekChatModel chatModel = DeepSeekChatModel.builder()
                    .deepSeekApi(api)
                    .defaultOptions(options)
                    .build();

            List<Message> promptMessages = new ArrayList<>();
            for (Map<String, String> m : messages) {
                if (m == null) continue;
                String role = m.getOrDefault("role", "user");
                String content = m.getOrDefault("content", "");
                if (content == null || content.isBlank()) continue;
                switch (role == null ? "user" : role) {
                    case "system" -> promptMessages.add(new SystemMessage(content));
                    case "assistant" -> promptMessages.add(new AssistantMessage(content));
                    default -> promptMessages.add(new UserMessage(content));
                }
            }
            if (promptMessages.isEmpty()) return null;

            ChatResponse response = chatModel.call(new Prompt(promptMessages));
            if (response == null || response.getResult() == null || response.getResult().getOutput() == null) {
                return null;
            }
            String text = response.getResult().getOutput().getText();
            return text == null || text.isBlank() ? null : text.trim();
        } catch (Exception e) {
            return null;
        }
    }
}
