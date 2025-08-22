<template>
  <div class="ai-practice-container">
    <!-- 左侧历史对话记录 -->
    <div class="history-panel">
      <div class="new-chat-container">
        <button class="new-chat-btn" @click="newConversation">
          新建对话
          <el-icon class="plus-icon">
            <Plus/>
          </el-icon>
        </button>
      </div>
      <ul class="history-list">
        <li v-for="(item, index) in historyList" :key="index" @click="selectConversation(index)"
            :class="{ active: currentConversationIndex === index }"
            class="history-item"
        >
          <span class="title-text">{{ item.title }}</span>

          <!-- 悬停按钮和删除菜单 -->
          <el-dropdown
              trigger="click"
              placement="bottom-end"
              @command="() => handleDelete(index)"
          >
            <el-icon
                class="more-icon"
                @click.stop
            >
              <MoreFilled />
            </el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="delete">
                  <el-icon><Delete /></el-icon> 删除窗口
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </li>
      </ul>
    </div>

    <!-- 右侧对话页面 -->
    <div class="chat-wrapper">
      <div class="chat-panel">
        <!-- 上半部分聊天界面 -->
        <div class="chat-messages" ref="chatMessagesRef">
          <div v-for="(message, index) in currentConversation.messages" :key="index" :class="['message', message.role]">
            <div class="avatar">
              <div v-if="message.role !== 'user'" class="ai-avatar">
                <img src="@/assets/images/zhanzonzhushou.jpg" alt="AI Avatar">
              </div>
              <div v-else>
                <img src="@/assets/images/user.png" alt="Me">
              </div>
            </div>
            <!--            <div class="content">-->
            <!--              {{ message.content }}-->
            <!--              &lt;!&ndash;              <audio v-if="message.audioUrl" :src="message.audioUrl" controls></audio>&ndash;&gt;-->
            <!--              &lt;!&ndash; <AudioBase></AudioBase> &ndash;&gt;-->
            <!--            </div>-->
            <div class="content" :ref="(el) => setContentRef(el, index)" v-html="message.content"></div>
          </div>
        </div>

        <!-- 输入框 -->
        <div class="input-area">
          <div class="input-wrapper">
            <el-icon class="input-icon link-icon">
              <Link/>
            </el-icon>
            <input
                v-model="userInput"
                @keyup.enter="sendMessage"
                placeholder="输入消息，按回车发送..."
                type="text"
                :disabled="isInputDisabled"
            >
            <div class="button-group">
              <div class="audio-wave" v-if="isRecording" @click="finishRecording">
                <span v-for="n in 4" :key="n" :style="{ animationDelay: `${n * 0.2}s` }"></span>
              </div>
              <el-icon v-else class="input-icon microphone-icon" @click="toggleRecording">
                <Microphone/>
              </el-icon>
              <div class="separator"></div>
              <el-popover
                  placement="top"
                  :width="200"
                  trigger="hover"
                  :disabled="!!userInput.trim()"
              >
                <template #reference>
                  <el-button
                      class="send-button"
                      circle
                      @click="sendMessage"
                      :disabled="!userInput.trim()"
                  >
                    <el-icon>
                      <Top/>
                    </el-icon>
                  </el-button>
                </template>
                <span>请文字/录音/上传语音回复</span>
              </el-popover>
            </div>
          </div>
        </div>

        <div class="disclaimer">
          服务生成的所有内容均由詹总的神奇助手生成，其生成内容的准确性和完整性无法保证，不代表詹总的态度或观点
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 必须加上这个，引入css文件，不然主页面会滚动的
import '@/styles/global.css';
import katex from 'katex';
// import 'katex/dist/katex.min.css';
import {marked} from 'marked';

/* 给 marked 增加行内 & 行间公式规则 */
const renderer = new marked.Renderer();

// 行内 \\( ... \\)
renderer.text = (text) =>
    text
        .replace(/\\\((.*?)\\\)/g, (_, math) =>
            katex.renderToString(math, { throwOnError: false }))
        .replace(/\\\[(.*?)\\\]/gs, (_, math) =>
            katex.renderToString(math, { displayMode: true, throwOnError: false }));

/* 让 marked 使用我们的扩展 */
marked.use({ renderer });

import renderMathInElement from 'katex/dist/contrib/auto-render.js';  // 渲染器
import { renderMarkdown } from '@/utils/markdown';
import {ref, computed, nextTick, onMounted, onUnmounted} from 'vue';
import {Link, Microphone} from '@element-plus/icons-vue';
import {ElMessage} from 'element-plus';
// import AudioBase from "@/components/AudioBase.vue";
import {get, post} from '@/utils/request'
import {API, BASE_URL} from '@/api/config'
import axios from "axios";

// delete
import { Delete, MoreFilled } from '@element-plus/icons-vue';
import { ElMessageBox } from 'element-plus';



const historyList = ref([
  { title: '欢迎使用', messages: [] }
  // {
  //   title: '詹总助手咨询',
  //   messages: [
  //     {role: 'assistant', content: '您好！我是詹总的神奇助手，有什么需要帮助的吗？'},
  //     {role: 'user', content: '是的，我听说詹总很牛逼，特意来请教一下。'},
  //     {
  //       role: 'assistant',
  //       content: '是的，您问对地方了！'
  //     }
  //   ]
  // },
  // {
  //   title: '功能还未开发',
  // },
  // {
  //   title: '功能还未开发',
  // },
  // {
  //   title: '功能还未开发',
  // }
]);
/* 页面初始化时加载所有窗口 */
const loadWindows = async () => {
  try {
    const res = await get('/chat/list')   // GET /chat/list
    if (res.code === 100) {
      // 后端返回 [{ id, name }, ...]
      historyList.value = res.data.map(w => ({
        id: w.id,
        name: w.name,  // 保留name
        title: w.name,
        messages: []   // 对话内容留空，点击时再按需加载
      }))
      // 只为第一个窗口拉 text
      const first = historyList.value[0]
      const textRes = await get(`/chat/text?name=${encodeURIComponent(first.name)}`)
      if (textRes.code === 100) {
        first.messages = JSON.parse(textRes.data)
      }
    }
  } catch (e) {
    console.error('加载窗口失败', e)
  }
}


const currentConversationIndex = ref(0);
const userInput = ref('');
const isListening = ref(false);
const chatMessagesRef = ref(null);
const isRecording = ref(false);
let mediaRecorder = null;
let audioChunks = [];
const mediaStream = ref(null);
const isInputDisabled = ref(false);

const currentConversation = computed(() => historyList.value[currentConversationIndex.value]);

const selectConversation = async (index) => {
  if (index === -1) {
    // // 让 historyList 为空（如果你确实想清空）
    // historyList.value= [
    //   { title: '欢迎使用', messages: [] }];
    return;
  }

  currentConversationIndex.value = index;
  contentRefs.length = 0; // 清空旧引用
  // 2. 如果该窗口还没加载过对话，就拉一次
  const win = historyList.value[index]
  if (win.messages.length === 0) {
    try {
      const res = await get(`/chat/text?name=${encodeURIComponent(win.name)}`)
      if (res.code === 100) {
        win.messages = JSON.parse(res.data)   // 反序列化
        // ② 打印到控制台
        console.log(win.messages);
      }
    } catch (e) {
      console.error('加载对话失败', e)
    }
  }
  nextTick(() => {
    scrollToBottom();
  });
};
/* 工具：自动生成窗口名 */
function generateWindowName() {
  const now = new Date()
  return `咨询 ${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`
};

const newConversation = async () => {
  const name = generateWindowName();
  // 1️⃣ 如果列表只剩「欢迎使用」，先移除它
  if (
      historyList.value.length === 1 &&
      historyList.value[0].title === '欢迎使用'
  ) {
    historyList.value = [];
  }

  historyList.value.unshift({
    title: name,     // 1. 自动起名,
    // 实际上这里要和后端交互的话，messages 最好用 map 格式，key 是对应的 id，这样方便后端根据 id 来操作消息
    messages: []
  });
  currentConversationIndex.value = 0;
  /* 2. 发 PUT 请求把 name 同步到后端 */
  try {
    // 用 GET 或 POST 都行，只要 name 挂在查询串
    const res = await post(`/chat/create?name=${encodeURIComponent(name)}`);
    if (res.code === 100) {
      console.log('窗口创建成功');
    } else {
      ElMessage.error(res.msg || '创建窗口失败');
    }
  } catch (e) {
    console.error(e);
    ElMessage.error('网络异常');
  }
};

const sendMessage = async () => {
  if (userInput.value.trim()) {
    // 添加用户消息
    // currentConversation.value.messages.push({role: 'user', content: userInput.value});
    const win = currentConversation.value;        // 当前窗口
    win.messages.push({ role: 'user', content: userInput.value }); // 1. 先把用户消息塞进本地列表

    // 2. 构造 JSON 串
    const payload = JSON.stringify({
      'name': win.title,            // 当前窗口名字
      'prompt': userInput.value    // 用户输入的纯文本
    });

    // 发送完毕，清空输入框
    userInput.value = '';
    nextTick(() => {
      scrollToBottom();
    });

    const loadingMessage = ref({
      role: 'assistant',
      content: '詹总助手竭诚为您服务中...',
      loading: true // 标记为加载状态
    });
    currentConversation.value.messages.push(loadingMessage.value);
    nextTick(() => {
      scrollToBottom();
    });


    // 3. 发 POST，获取AI回复，body 为 JSON
    // 获取AI回复
    try {
      // 前端发送出去的不是json串，而是用户输入的纯文本
      // 这个post搞了半天，发现必须得要axios格式才能正确，而且axios还得配置基础路由，不然会发给前端本人导致后端接收不到
      // 创建axios实例
      const apiClient = axios.create({
        baseURL: BASE_URL, // 设置基础URL
        timeout: 500000, // 请求超时时间
      });
      const res = await apiClient.post('/chat/generate',
          payload,
          { headers: { 'Content-Type': 'application/json' } }
      )

      // 立即打印
      console.log('完整响应:', res)
      console.log('响应数据:', res.data)
      // axios 默认把整条 JSON 包在 res.data 里。因此真正要取的是res.data
      const { code, msg, data } = res.data   // ← 注意 .data
      if (code == 100) {
        // 更新加载中的消息为实际回复
        loadingMessage.value.content = data;
        loadingMessage.value.loading = false; // 更新为非加载状态
        nextTick(() => {
          scrollToBottom();
        });
      } else {
        ElMessage.error(msg);
        loadingMessage.value.content = '获取回复失败，请稍后重试';
        loadingMessage.value.loading = false;
        nextTick(() => {
          scrollToBottom();
        });
      }
    } catch (error) {
      console.error('sendMessage error', error);
      ElMessage.error('获取回复失败，请稍后重试');
      loadingMessage.value.content = '获取回复失败，请稍后重试';
      loadingMessage.value.loading = false;
      nextTick(() => {
        scrollToBottom();
      });
    }
  }
};

// 新增一个删除窗口的逻辑
const handleDelete = async (index) => {
  const target = historyList.value[index];
  if (!target) return;

  try {
    await ElMessageBox.confirm(
        `确定要删除窗口「${target.title}」吗？`,
        '确认删除',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        }
    );

    // 调后端删除接口（DELETE 请求）
    const apiClient = axios.create({
      baseURL: BASE_URL, // 设置基础URL
      timeout: 100000, // 请求超时时间
    });
    await apiClient.delete('/chat/delete', {
      data: { name: target.title }
    });

    // 删除本地数据
    historyList.value.splice(index, 1);

    /* 判断是否删空了 */
    if (historyList.value.length === 0) {
      currentConversationIndex.value = 0;

      // 2️⃣ 立即把列表重置为只有「欢迎使用」
      historyList.value = [
        { title: '欢迎使用', name: '欢迎使用', messages: [] }
      ];
    }
    else{
      // 如果删除的是当前激活的窗口，切换到第一个
      if (currentConversationIndex.value === index) {
        currentConversationIndex.value = 0;
      } else if (currentConversationIndex.value > index) {
        currentConversationIndex.value -= 1;
      }
      // ✅ 如果新窗口没有内容，就自动加载
      const newTarget = historyList.value[currentConversationIndex.value];
      if (newTarget && newTarget.messages.length === 0) {
        await selectConversation(currentConversationIndex.value);
      }
    }

    ElMessage.success('删除成功');
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除窗口失败', error);
      ElMessage.error('删除失败');
    }
  }
};



// 手动渲染：把含有 LaTeX 的字符串转成 HTML
function renderLatex(str) {
  return str
      .replace(/\\\\/g, '\\')                                   // 剥二次转义
      .replace(/\\\((.*?)\\\)/g, (_, math) =>                   // 行内
          katex.renderToString(math, { throwOnError: false }))
      .replace(/\\\[(.*?)\\\]/gs, (_, math) =>                  // 行间
          katex.renderToString(math, { displayMode: true, throwOnError: false }));
}
/* 存放每条消息 DOM 的引用 */
const contentRefs = [];
const setContentRef = (el, idx) => {
  if (!el) return;
  const raw = String(currentConversation.value.messages[idx].content);
  el.innerHTML = renderLatex(String(raw));
};










const finishRecording = () => {
  if (isRecording.value && mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    isRecording.value = false;
    isInputDisabled.value = false;
  }
};

const sendAudioMessage = (audioBlob) => {
  const audioUrl = URL.createObjectURL(audioBlob);
  currentConversation.value.messages.push({
    role: 'user',
    content: '发送了一条语音消息',
    audioUrl: audioUrl
  });
  nextTick(() => {
    scrollToBottom();
  });

};

const toggleRecording = async () => {
};

const stopMediaStream = () => {
  if (mediaStream.value) {
    mediaStream.value.getTracks().forEach(track => track.stop());
    mediaStream.value = null;
  }
};

const scrollToBottom = () => {
  const chatMessages = chatMessagesRef.value;
  chatMessages.scrollTop = chatMessages.scrollHeight;
};


onMounted(() => {
  loadWindows()
});

onUnmounted(() => {
  finishRecording();
  stopMediaStream();
});
</script>

<style scoped>
/* 样式保持不变 */
.ai-practice-container {
  display: flex;
  height: 100vh;
  font-family: Arial, sans-serif;
  overflow: hidden; /* 禁止页面级滚动 */
}

.history-panel {
  width: 280px;
  height:100vh;
  background: linear-gradient(135deg, rgba(230, 240, 255, 0.01), rgba(240, 230, 255, 0.01));
  background-color: #ffffff;
  padding: 20px;
  overflow-y: auto;
}

.new-chat-container {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 13px; /* 略微增加内边距 */
  margin-top: 10px;
  margin-bottom: 5px;
  background: linear-gradient(to right, #0069e0, #0052bc); /* 改用更深的蓝色渐变 */
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.3s;
  font-size: 14px; /* 加大字号 */
  font-weight: bold; /* 加粗字体 */
}

.new-chat-btn:hover {
  opacity: 0.9;
}

.history-list {
  list-style-type: none;
  padding: 0;
}

.history-list li {
  padding: 10px;
  margin-bottom: 10px;
  background-color: #ffffff;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.history-list li:hover,
.history-list li.active {
  background-color: rgba(0, 105, 224, 0.15);
  color: #0052bc;
}
/* 新增这几段 */
.history-item {
  position: relative;
  padding: 10px;
  margin-bottom: 10px;
  background-color: #ffffff;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.history-item:hover,
.history-item.active {
  background-color: rgba(0, 105, 224, 0.15);
  color: #0052bc;
}
.more-icon {
  opacity: 0;
  transition: opacity 0.2s;
  cursor: pointer;
  color: #666;
}
.history-item:hover .more-icon {
  opacity: 1;
}

.chat-wrapper {
  height: 100vh;
  overflow: hidden;
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg,
  rgba(0, 105, 224, 0.08),
  rgba(0, 56, 148, 0.08)
  );
}

.chat-panel {
  width: 100%;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: transparent;
  box-shadow: none;
  padding-top: 12px; /* 添加顶部内边距 */
  /* padding-left: 10%;
  padding-right: 10%; */
}

.visitor-info {
  background-color: transparent; /* 背透明 */
  padding: 15px 20px; /* 增加内边距 */
  margin-bottom: 20px; /* 增加与第一条对话的距离 */
  font-weight: bold;
  color: #333;
  text-align: left;
  font-size: 18px; /* 增大字体大小 */
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding-top: 20px;
  padding-left: 10%;
  padding-right: 10%;
  background-color: transparent;
  /* 修改滚动条颜色 */
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 105, 224, 0.3) transparent;
}

/* 为 Webkit 浏览器（如 Chrome、Safari）自定义滚动条样式 */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background-color: rgba(0, 105, 224, 0.3);
  border-radius: 3px;
}

.message {
  display: flex;
  margin-bottom: 20px;
}

.message .avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  overflow: hidden;
}

.message .avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #ffffff;
}

.message .content {
  background-color: rgba(255, 255, 255, 1);
  padding: 12px 18px; /* 增加内边距 */
  border-radius: 10px;
  max-width: 80%;
  font-size: 16px; /* 增加字体大小 */
  line-height: 1.8; /* 增加行高 */
}

.message.user {
  flex-direction: row-reverse;
}

.message.user .avatar {
  margin-right: 0;
  margin-left: 10px;
}

.message.user .content {
  background-color: rgba(0, 105, 224, 0.12);
  color: black;
}

.input-area {
  position: sticky;
  bottom:0;
  padding: 20px 10% 0 10%;
  border-top: 0px solid #e0e0e0;
  background-color: transparent;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

input {
  width: 100%;
  padding: 12px 110px 12px 50px; /* 调整右侧padding以适应新的按钮组 */
  border: 1px solid rgba(204, 204, 204, 0.5);
  border-radius: 25px;
  font-size: 16px;
  background-color: rgba(255, 255, 255, 0.7);
  transition: border-color 0.3s;
  height: 55px;
}

input:focus {
  outline: none;
  border-color: #0069e0;
}

input::placeholder {
  color: #969696;
}

.button-group {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
}

.input-icon {
  color: #0069e0;
  font-size: 24px;
  cursor: pointer;
}

.link-icon {
  position: absolute;
  left: 18px;
  top: 50%;
  transform: translateY(-50%);
}

.microphone-icon {
  margin-right: 0; /* 将右侧边距改为0 */
}

.separator {
  width: 1px;
  height: 25px;
  background-color: rgba(204, 204, 204, 0.5);
  margin: 0 10px;
}

.send-button {
  width: 40px;
  height: 40px;
  background: linear-gradient(to right, #0069e0, #0052bc); /* 保持一致的蓝色渐变 */
  border: none;
  color: white;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.send-button:disabled {
  background: rgba(0, 105, 224, 0.1);
  color: rgba(0, 82, 188, 0.3);
  cursor: default;
}

.send-button :deep(.el-icon) {
  font-size: 24px;
}

.send-button:not(:disabled):hover {
  opacity: 0.9;
}

/* 新增的免责声明样式 */
.disclaimer {
  font-size: 10px;
  color: #999;
  text-align: center;
  margin-top: 12px;
  margin-bottom: 12px;
}

.audio-wave {
  display: flex;
  align-items: center;
  height: 24px;
  width: 24px;
}

.audio-wave span {
  display: inline-block;
  width: 3px;
  height: 100%;
  margin-right: 1px;
  background: #0069e0;
  animation: audio-wave 0.8s infinite ease-in-out;
}

@keyframes audio-wave {
  0%, 100% {
    transform: scaleY(0.3);
  }
  50% {
    transform: scaleY(1);
  }
}

.message .content audio {
  margin-top: 10px;
  width: 100%;
}
</style>