import os
import queue
import threading
import re
from typing import List, Dict
from langchain_openai import ChatOpenAI
from your_module import StructuredTaskStepStoryboard, TaskEngineBuilder  # 替换为你的实际模块

# 初始化模型（放在函数外部，避免重复初始化）
llm = ChatOpenAI(
    openai_api_base="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-R1",
    openai_api_key="sk-qbijmznflgshilamptjqmeonrgkvnixgeqbxtpkwcldksfma",
    verbose=True,
    temperature=0.1,
    top_p=0.9,
)

guiji_llm = ChatOpenAI(
    openai_api_base="https://api.siliconflow.cn/v1",
    model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
    openai_api_key="sk-qbijmznflgshilamptjqmeonrgkvnixgeqbxtpkwcldksfma",
    verbose=True,
    temperature=0.1,
    top_p=0.9,
)

cross_encoder_path = os.path.join(os.path.dirname(__file__), "jina-reranker-v2-base-multilingual")
embed_model_path = os.path.join(os.path.dirname(__file__), "m3e-base")


def process_user_question(user_question: str) -> str:
    """
    处理用户问题并返回最终的answer
    """
    # 初始化构建器
    builder = StructuredTaskStepStoryboard.form_builder(
        llm_runable=llm,
        kor_dreams_task_step_llm=guiji_llm,
        start_task_context=user_question,  # 使用用户问题作为起始上下文
        cross_encoder_path=cross_encoder_path,
        embed_model_path=embed_model_path,
        data_base='search_papers'
    )

    # 获取任务引擎构建器
    task_engine_builder = builder.loader_task_step_iter_builder()

    # 工作线程函数
    def worker(step: int, task_engine: TaskEngineBuilder, buffer_queue):
        thread_id = threading.get_ident()
        try:
            task_engine.llm_runable = llm
            task_engine.init_task_engine()
            task_engine.generate_step_answer()

            answer = task_engine.task_step_to_question_chain.task_step_question_answer

            return {
                "step": step,
                "task_step_name": task_engine.task_step_name,
                "task_step_description": task_engine.task_step_description,
                "task_step_level": task_engine.task_step_level,
                "answer": answer
            }

        except Exception as e:
            print(f"步骤{step}执行失败: {e}")
            return {
                "step": step,
                "task_step_name": f"步骤{step}",
                "task_step_description": "执行失败",
                "task_step_level": "error",
                "answer": f"执行失败: {str(e)}"
            }
        finally:
            try:
                buffer_queue.get()
                buffer_queue.task_done()
            except Exception:
                pass

    # 处理所有任务
    buffer_queue = queue.Queue(maxsize=6)
    threads = []
    step = 0
    results = []

    while not task_engine_builder.empty():
        task_engine = task_engine_builder.get()
        step += 1

        buffer_queue.put(1)
        t = threading.Thread(target=lambda: results.append(worker(
            step=step,
            task_engine=task_engine,
            buffer_queue=buffer_queue
        )), daemon=True)
        t.start()
        threads.append(t)

    # 等待所有线程完成
    for t in threads:
        t.join()

    # 排序结果
    results.sort(key=lambda x: x["step"])

    # 拼接结果字符串
    result_string = ""
    for result in results:
        result_string += f"步骤 {result['step']}: {result['task_step_name']}\n"
        result_string += f"描述: {result['task_step_description']}\n"
        result_string += f"层级: {result['task_step_level']}\n"
        result_string += f"答案: {result['answer']}\n"
        result_string += "-" * 50 + "\n"

    # 生成总结
    summary = StructuredTaskStepStoryboard.generate_summary(
        llm_runable=llm,
        content=result_string
    )

    # 清理总结文本
    cleaned_text = re.sub(r'◁think▷.*?◁/think▷', '', summary, flags=re.DOTALL)
    cleaned_text = re.sub(r'<think>.*?</think>', '', cleaned_text, flags=re.DOTALL)

    if cleaned_text.startswith("<think>"):
        cleaned_text = cleaned_text[len("<think>"):]

    return cleaned_text