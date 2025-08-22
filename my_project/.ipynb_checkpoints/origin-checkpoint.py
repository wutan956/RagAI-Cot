import threading
import queue
# 默认持久化文件名
from engine.storage.task_step_store.types import DEFAULT_PERSIST_FNAME
# 任务引擎构建器
from task_engine_builder.base import TaskEngineBuilder

import time
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import VLLM
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate, \
    MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
import os
from langchain_core.runnables import RunnablePassthrough
# import uvicorn
import json
# 替换原来的 PyPDFLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationSummaryMemory
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_community.document_loaders import PyMuPDFLoader
from concurrent.futures import ThreadPoolExecutor  # 多线程处理
import concurrent
import re
from builder_task_step.base import StructuredTaskStepStoryboard
from langchain_community.chat_models import ChatOpenAI

LLM_MODEL_PATH = "/root/autodl-tmp/Hugging-Face/hub/models--SciPhi--SciPhi-Mistral-7B-32k/snapshots/8abed8a547b7c60bb29edc87da4423cef67acea5"
# LLM_MODEL_PATH = "/root/autodl-tmp/Hugging-Face/hub/models--deepseek-ai--DeepSeek-R1-Distill-Qwen-1.5B/snapshots/ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_CACHE_DIR = "/root/autodl-tmp/Hugging-Face/embedding_model1"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RETRIEVER_K = 5
PERSIST_DIRECTORY = "./autodl-tmp/chroma_db"
MAX_NEW_TOKENS = 2048
TEMPERATURE = 0.3
GPU_MEMORY_UTILIZATION = 0.9
PDF_DIRECTORY = "/root/autodl-tmp/lenwen_PDF"
PDF_GLOB = "**/*.pdf"

llm = ChatOpenAI(
    openai_api_base="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-R1",
    openai_api_key="sk-qbijmznflgshilamptjqmeonrgkvnixgeqbxtpkwcldksfma",
    verbose=True,
    temperature=0.1,
    top_p=0.9,
)
cross_encoder_path = os.path.join(os.path.dirname(__file__), "jina-reranker-v2-base-multilingual")  # 交叉编码器
embed_model_path = os.path.join(os.path.dirname(__file__), "m3e-base")  # 嵌入模型
builder = StructuredTaskStepStoryboard.form_builder(
    llm_runable=llm,
    kor_dreams_task_step_llm=llm,
    start_task_context="把大象装冰箱需要怎么做",
    cross_encoder_path=cross_encoder_path,
    embed_model_path=embed_model_path,
    data_base='search_papers' # 数据库名称
)
# 完成主题-主模型-辅助模型抽取-获得每个步骤了
task_engine_builder = builder.loader_task_step_iter_builder( )


# 工作线程函数（核心逻辑，处理的是一个主题里抽取出来的单个步骤）
def worker(
        step: int,
        task_engine: TaskEngineBuilder,
        buffer_queue,
):
    thread_id = threading.get_ident()
    try:
        task_engine.llm_runable = llm  # 主模型

        # 初始化三大组件
        # 完成单个步骤变成问题-数据库检索召回
        task_engine.init_task_engine()

        # 把初始化三大组件第一步获得的task_step_question丢给ai，获得ai的回复task_step_question_answer，# 此时在task_step_store.json里面增加task_step_question_answer ，对应task_step_question
        task_engine.generate_step_answer()


        # 不使用MCTS，耗时太久了
        answer = task_step.task_step_question_answer
        print(answer)
        task_step.task_step_question_answer = answer
        task_step_id = task_engine.task_step_id
        # 5. 持久化存储
        task_engine.task_step_store.add_task_step([task_step])
        task_step_store_path = concat_dirs(
            dirname=f"{builder.base_path}/storage/{task_step_id}",
            basename=DEFAULT_PERSIST_FNAME,
        )
        task_engine.task_step_store.persist(persist_path=task_step_store_path)

        task_step_store.add_task_step([task_step])
        task_step_store_path = concat_dirs(
            dirname=f"{builder.base_path}/storage", basename=DEFAULT_PERSIST_FNAME
        )
        task_step_store.persist(persist_path=task_step_store_path)

    except Exception as e:
        logger.error("场景加载失败", e)
    finally:
        # 清理操作：释放 buffer_queue 中的资源（如果需要的话）
        try:
            # After completing the task, remove an item from the buffer queue
            buffer_queue.get()
            buffer_queue.task_done()
        except Exception:
            pass

        try:
            # 清理当前线程中所有的子进程
            for proc in process_registry.get(thread_id, []):
                try:
                    proc.kill()  # 或者使用 proc.kill() 更为强制

                    print(f"子进程 {proc.pid} 已终止")
                except Exception as ex:
                    print(f"终止子进程 {proc.pid} 时出错: {ex}")
        except Exception:
            pass
        logger.info(f"{owner}，任务结束")

#
# def load_pdf(filename):
#     file_path = os.path.join(PDF_DIRECTORY, filename)
#     print(f"Processing: {file_path}")
#     try:
#         # loader = UnstructuredPDFLoader(file_path,languages=["chi_sim", "eng"],  # 同时支持中英文
#         #     mode="elements",  # 按语义元素分割
#         #     # strategy="hi_res",  # 高精度模式（适合复杂PDF）
#         #     post_processors=["remove_inline_links", "clean_extra_whitespace"]  # 清理无用内容
#         #     )
#         loader = PyMuPDFLoader(file_path)
#         return loader.load()
#     except Exception as e:
#         print(f"Error loading {file_path}: {str(e)}")
#         return []
#
#
# def initialize_vectorstore(embedding_model):
#     # 1. 加载 PDF
#     all_pdf_data = []  # 存储所有 PDF 的内容
#     # 使用线程池（建议线程数为CPU核心数*2~5）
#     with ThreadPoolExecutor(max_workers=8) as executor:
#         # 提交所有任务
#         futures = [
#             executor.submit(load_pdf, filename)
#             for filename in os.listdir(PDF_DIRECTORY)
#             if filename.lower().endswith(".pdf")
#         ]
#         # 获取结果
#         for future in concurrent.futures.as_completed(futures):
#             all_pdf_data.extend(future.result())
#     print(f"Loaded {len(all_pdf_data)} PDF documents.")
#
#     # 3. 分阶段分割
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
#                                                    separators=["\n\n", "\n", "(?<=。)", ""])  # 按段落和句子分割)
#     final_splits = []  # 存储所有分块后的内容
#     # 对每个文档进行分块处理
#     for doc in all_pdf_data:
#         chunks = text_splitter.split_documents([doc])  # 注意: split_documents 需要列表输入
#         final_splits.extend(chunks)
#     # 3. 存入 ChromaDB
#     vectorstore = Chroma.from_documents(
#         documents=final_splits,
#         embedding=embedding_model,
#         # persist_directory=PERSIST_DIRECTORY  # 调试过程千万别持久化存储，不然会重复存储的
#         persist_directory=None  # 不保存到磁盘
#     )
#     retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})
#     return vectorstore, retriever
#
#
# def format_docs(docs):
#     formatted = []
#     # print("********************打印原检索列表*******************")
#     # print(docs)
#     # print("****************************************************")
#     for doc in docs:
#         metadata = doc.metadata
#         source = os.path.basename(metadata.get("source", "未知来源"))
#         page = metadata.get("page", 0) + 1
#         content = doc.page_content
#         formatted.append(f"内容: {content}\n来源: {source} (第{page}页)")
#     # # 打印出来看看
#     # print("********************打印文档看看*************************")
#     # for test_i in formatted:
#     #     print(test_i)
#     # print("*********************************************************")
#     return "\n\n".join(formatted)
#
#
# # 将历史对话转成message格式，才能加入prompt中
# def prepare_history(raw_history):
#     memory = ConversationSummaryMemory(
#         llm=llm,
#         max_token_limit=50,  # 控制总结长度
#         memory_key="chat_history",
#         return_messages=True  # 返回 LangChain 消息格式
#     )
#     # 把历史写入 memory
#     memory.clear()  # 清空旧记录
#     for msg in raw_history:
#         if msg["role"] == "user":
#             memory.chat_memory.add_user_message(msg["content"])
#         else:
#             memory.chat_memory.add_ai_message(msg["content"])
#             # 强制生成总结，并替换为单条系统消息
#     summary = memory.predict_new_summary(memory.chat_memory.messages, {})
#     return [SystemMessage(content=summary)] if summary else []
#     # return memory.load_memory_variables({})["chat_history"]
#
#
# def build_rag_chain(retriever, llm):
#     # 1. 定义提示模板
#     system_template = """你是一个严谨的学术研究助手，需要以自然对话的方式回答用户问题。请遵循以下规则：
# 1. 基于提供的论文内容回答，并且以自然对话的方式回答
# 2. 禁止自问自答
# 3. 不能直接回答目录与编号
# 4. 不能无限重复自己讲的话
# 5. 禁止语句不完整
# 6. 禁止照搬原话，请你用自己的话对内容进行总结
# 7. 要求句子逻辑畅通
# 8. 不出现语句重复的情况
# 9. 如果检索到的内容是英文，先将其翻译为中文，再用中文回答
# 提供的论文内容：
# {context}
# 相关历史对话摘要：
# {chat_history}
# """
#     # 添加CoT推理步骤的中间模板
#     cot_template = """请按照以下步骤思考并回答问题：
#
# [问题分析]
# 首先，我需要理解这个问题的核心是：{question_analysis}
#
# [检索内容分析]
# 从提供的论文内容中，我找到以下相关证据：
# {relevant_evidence}
#
# [推理过程]
# 基于以上分析，我的思考过程是：
# {reasoning_steps}
#
# [最终答案]
# 综上所述，答案是："""
#     human_template = """请根据上述规范回答以下问题：
# 1. 如果内容是英文，先翻译再总结
# 2. 用中文回答，专业术语保留英文
# 3. 保持回答简洁
# 问题：{question}
# """
#     prompt = ChatPromptTemplate.from_messages([
#         SystemMessagePromptTemplate.from_template(system_template),
#         MessagesPlaceholder(variable_name="chat_history"),  # 历史对话插入点
#         HumanMessagePromptTemplate.from_template(cot_template),
#         HumanMessagePromptTemplate.from_template(human_template)
#     ])
#
#     # 定义各步骤的处理函数
#     def analyze_question(inputs):
#         return {"question_analysis": f"这个问题是关于{inputs['question']}的，主要需要解决..."}
#
#     def extract_evidence(inputs):
#         docs = retriever.invoke(inputs["question"])
#         return {"relevant_evidence": format_docs(docs)}
#
#     def generate_reasoning(inputs):
#         return {"reasoning_steps": f"1. 首先...\n2. 其次...\n3. 最后..."}
#
#     def debug_pro(input_prompt):
#         print("***********************打印prompt***********************")
#         print(input_prompt)
#         print("********************************************************")
#         return input_prompt
#
#     # 2. 构建 RAG 链
#     rag_chain = (
#             {
#                 "question": lambda x: x["question"],
#                 "chat_history": lambda x: prepare_history(x["history"]),
#                 "context": lambda x: format_docs(retriever.invoke(x["question"])),
#                 "question_analysis": analyze_question,
#                 "relevant_evidence": extract_evidence,
#                 "reasoning_steps": generate_reasoning
#             }
#             | prompt
#             | debug_pro
#             | llm
#             | StrOutputParser()
#     )
#     return rag_chain
#
#
# # 后处理逻辑函数
# def postprocess_answer(answer):
#     # 移除来源标记和页码
#     answer = re.sub(r'来源:.*?(第\d+页)', '', answer)
#     # 合并多余空行
#     answer = re.sub(r'\n{3,}', '\n\n', answer)
#     # 移除重复内容
#     sentences = answer.split('。')
#     unique_sentences = []
#     seen = set()
#     for s in sentences:
#         simplified = re.sub(r'\W+', '', s).strip()
#         if simplified and simplified not in seen:
#             seen.add(simplified)
#             unique_sentences.append(s)
#     answer = '。'.join(unique_sentences).strip()
#     # 确保回答以句号结尾
#     if answer and not answer.endswith(('.', '!', '?')):
#         answer += '。'
#     return answer
#
#
# app = FastAPI(title="RAG API with Local LLM")
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
#
#
# @app.post("/generate/v1/chat/completions")
# async def chat_completion(request: ChatRequest):
#     # 准备历史的对话数据
#     messages = [msg.dict() for msg in request.messages]
#     if len(messages) > 1:
#         history = messages[:-1]
#     else:
#         history = []
#
#     print("___________________________________________")
#     print(history)
#     print("_________________________________________")
#     # 提取当前用户问题
#     last_user_msg = next((msg.content for msg in reversed(request.messages) if msg.role == "user"), None)
#     print(last_user_msg)
#     print("___________________________________________")
#     if not last_user_msg:
#         raise HTTPException(400, detail="No user message found")
#
#     # 调用后处理函数
#     answer = postprocess_answer(rag_chain.invoke({
#         "question": last_user_msg,
#         "history": history  # 传入原始历史数据
#     }))  # 调用 RAG 链
#     print("模型回答：", answer)
#
#     retrieved_docs = retriever.get_relevant_documents(last_user_msg)
#     print("\n===== 检索到的文档内容 ======")
#     for i, doc in enumerate(retrieved_docs):
#         print(f"\n文档 {i + 1}:")
#         print(f"来源: {os.path.basename(doc.metadata.get('source', '未知'))}")
#         print(f"内容: {doc.page_content[:500]}...")  # 只打印前500字符避免过长
#     print("============================\n")
#     sources = list(set([os.path.basename(doc.metadata.get("source")) for doc in retrieved_docs]))
#
#     return {
#         "id": f"chatcmpl-{int(time.time())}", "object": "chat.completion",
#         "created": int(time.time()), "model": "deepseek-r1-distill-qwen-1.5b",
#         "choices": [{
#             "index": 0,
#             "message": {
#                 "role": "assistant",
#                 "content": answer,
#                 "sources": sources,
#                 "tool_calls": None
#             },
#             "finish_reason": "stop"
#         }],
#         "usage": {
#             "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0
#         }
#     }
#
#
# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}


if __name__ == "__main__":
    # 1. 创建缓冲队列（最大6线程）
    buffer_queue = queue.Queue(maxsize=6)  # Create the buffer queue with max size of 2
    threads = []
    step = 0

    # 2. 处理所有任务引擎
    while not task_engine_builder.empty():
        # 循环从队列中逐个取出任务，直到队列为空。这里取出的是当前主题的每个步骤
        task_engine = task_engine_builder.get()
        step += 1

        ## 现在是调试，所以先不要并发
        worker(step=step,
               task_engine=task_engine,
               buffer_queue=None)  # 因为不使用并发，buffer_queue可以传None或去掉这个参数

        # # 3. 控制并发（通过缓冲队列）
        # # 当队列已满时，buffer_queue.put() 会阻塞，直到有空闲位置
        # buffer_queue.put(1)  # This will block if the buffer is full (i.e., 2 threads are active)
        # # 4. 创建工作线程
        # # Create and start a new worker thread
        # t = threading.Thread(target=worker,
        #                      kwargs={"step": step,
        #                              "task_engine": task_engine,
        #                              # task_step_store里面存放了一个主题对应的每个步骤，但是task_engine里面还放了单个步骤的id，所以它对应单个步骤
        #                              "task_step_store": task_step_store,
        #                              "buffer_queue": buffer_queue},  # 用于线程完成后释放位置。
        #                      daemon=True)  # 设置为守护线程，主程序退出时会自动终止这些线程
        # t.start()
        # threads.append(t)
    # 5. 等待所有线程完成
    # Wait for all threads to finish
    for t in threads:
        t.join()


    # # 初始化模型
    # embedding_model = initialize_embedding_model()
    # vectorstore, retriever = initialize_vectorstore(embedding_model)

    # rag_chain = build_rag_chain(retriever, llm)
    #
    # # 启动 FastAPI
    # uvicorn.run(app, host="0.0.0.0", port=8000)