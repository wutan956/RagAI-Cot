from __future__ import annotations

import logging
import os
import re
import threading
from abc import ABC
from typing import Dict, List

import pandas as pd
from langchain.chains import SequentialChain
from langchain.chains.base import Chain
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import (
    BaseMessage,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel
from sentence_transformers import CrossEncoder

from common.callback import event_manager
from document_loaders import KorLoader
from document_loaders.protocol.ner_protocol import TaskStepNode
from task_step_to_question_chain.prompts import (
    CONVERT_TASK_STEP_TO_QUESTION_PROMPT_TEMPLATE,
    TASK_STEP_QUESTION_TO_GRAPHQL_PROMPT_TEMPLATE,
)
from task_step_to_question_chain.searx.searx import searx_query
from task_step_to_question_chain.weaviate.prepare_load import exe_query
from engine.entity.task_step.task_step import TaskStepContext
from engine.storage.storage_context import BaseTaskStepStore
from engine.storage.task_step_store.types import DEFAULT_PERSIST_FNAME
from engine.utils import concat_dirs
from vector.base import CollectionService, DocumentWithVSId
import time

"""
#### 场景加载模块

编写符合计算机科学领域的 故事情境提示词，生成研究情境（story_scenario_context），替换现有的langchain会话模板，
对每个子任务指令转换为子问题
召回问题前3条,存入task_step_question_context
调用llm，生成task_step_question_answer
"""

PATTERN = re.compile(r"```graphql?([\s\S]*?)```", re.DOTALL)
"""Regex pattern to parse the output."""


class TaskStepToQuestionChain(ABC):
    start_task_context: str
    task_step_to_question_chain: Chain
    task_step_level:str
    task_step_description:str
    task_step_name:str
    aemo_representation_context:str
    task_step_question_to_graphql_chain: Chain
    collection: CollectionService
    cross_encoder: CrossEncoder
    data_base: str

    def __init__(
            self,
            task_step_level:str,
            task_step_description:str,
            task_step_name:str,
            aemo_representation_context:str,
            start_task_context: str,
            task_step_to_question_chain: Chain,
            task_step_question_to_graphql_chain: Chain,
            collection: CollectionService,
            cross_encoder: CrossEncoder,
            data_base: str,
    ):
        self.task_step_level = task_step_level
        self.task_step_description = task_step_description
        self.task_step_name = task_step_name
        self.aemo_representation_context = aemo_representation_context
        self.start_task_context = start_task_context
        self.task_step_to_question_chain = task_step_to_question_chain
        self.task_step_question_to_graphql_chain = task_step_question_to_graphql_chain
        self.collection = collection
        self.cross_encoder = cross_encoder
        self.data_base = data_base

    @classmethod
    def from_task_step_to_question_chain(
            cls,
            task_step_level: str,
            task_step_description: str,
            task_step_name: str,
            aemo_representation_context:str,
            start_task_context: str,
            llm_runable: Runnable[LanguageModelInput, BaseMessage],
            collection: CollectionService,
            cross_encoder: CrossEncoder,
            data_base: str = "search_papers",
    ) -> TaskStepToQuestionChain:
        """

        1、对当前主任务名称创建hash值，作为collection_name
        2、对当前任务步骤名称创建hash值，作为collection_name_context
        """
        # 其实就是传入这几个变量，构建一个prompt，然后用主模型得到输出
        # 模板1：把任务步骤（一个步骤，不是整个任务）转成问题
        prompt_template1 = PromptTemplate(
            input_variables=[
                "start_task_context",
                "aemo_representation_context",
                "task_step_name",
                "task_step_description",
                "task_step_level",
            ],
            template=os.environ.get(
                "CONVERT_TASK_STEP_TO_QUESTION_PROMPT_TEMPLATE",
                CONVERT_TASK_STEP_TO_QUESTION_PROMPT_TEMPLATE,
            ),
        )

        task_step_to_question_chain = prompt_template1 | llm_runable | StrOutputParser()

        def wrapper_output(_dict):
            return {
                # 中间变量全部打包输出
                "task_step_question_context": _dict["task_step_question_context"],
            }

        task_step_to_question_chain = {
                                          "task_step_question_context": task_step_to_question_chain,
                                      } | RunnableLambda(wrapper_output)

        # 这是第二个模板的，把问题转成数据库查询语句
        # 这里有个问题，就是模板需要的参数没有看到在哪里传进来的，还有模板似乎用的是主模型
        prompt_template2 = PromptTemplate(
            input_variables=["collection_name_context", "task_step_question"],
            template=os.environ.get(
                "TASK_STEP_QUESTION_TO_GRAPHQL_PROMPT_TEMPLATE",
                TASK_STEP_QUESTION_TO_GRAPHQL_PROMPT_TEMPLATE,
            ),
        )

        task_step_question_to_graphql_chain = (
                prompt_template2 | llm_runable | StrOutputParser()
        )

        def wrapper_output2(_dict):
            return {
                # 中间变量全部打包输出
                "task_step_question_graphql_context": _dict[
                    "task_step_question_graphql_context"
                ],
            }

        task_step_question_to_graphql_chain = {
                                                  "task_step_question_graphql_context": task_step_question_to_graphql_chain,
                                              } | RunnableLambda(wrapper_output2)

        return cls(
            start_task_context=start_task_context,
            task_step_to_question_chain=task_step_to_question_chain,
            task_step_question_to_graphql_chain=task_step_question_to_graphql_chain,
            collection=collection,
            cross_encoder=cross_encoder,
            data_base=data_base,
            task_step_level=task_step_level,
            task_step_description=task_step_description,
            task_step_name=task_step_name,
            aemo_representation_context=aemo_representation_context,
        )

    def invoke_task_step_to_question(self) -> str:
        """
        对开始任务进行抽取，得到任务步骤
        :return:
        """
        # 在src\dreamsboard\dreamsboard\engine\storage\task_step_store\keyval_task_step_store.py，因为task_step_store（simpletaskstep）也是继承这个类的
        # 创建的时候是长这样的，刚好就是这个链的模板需要的参数：
        # task_step_node = TaskStepNode.from_config(
        #     cfg={
        #         "start_task_context": self.start_task_context,
        #         "aemo_representation_context": result.get(
        #             "aemo_representation_context"
        #         ),
        #         "task_step_name": task_step.task_step_name,
        #         "task_step_description": task_step.task_step_description,
        #         "task_step_level": task_step.task_step_level,
        #     }
        # )

        result = self.task_step_to_question_chain.invoke({
            "start_task_context": self.start_task_context,
            "aemo_representation_context":self.aemo_representation_context,
            "task_step_name": self.task_step_name,
            "task_step_description": self.task_step_description,
            "task_step_level": self.task_step_level
        })  # 拿到主模型对当前步骤的信息综合后的问题，是一个字典里面有个task_step_question_context的值，例如：\nHow can the conflict between an AI's ability to solve complex mathematical problems like the Riemann Hypothesis and its failure to understand basic human communication, such as a deaf child's sign language, be developed to critique data inequality in a novel?"
        cleaned_text = re.sub(r'◁think▷.*?◁/think▷', '', result["task_step_question_context"], flags=re.DOTALL)
        cleaned_text = re.sub(r'<think>.*?</think>', '', cleaned_text, flags=re.DOTALL)
        # 定义要去除的前缀
        prefix = "<think>"

        # 如果字符串以指定前缀开头，则去除该前缀
        if cleaned_text.startswith(prefix):
            cleaned_text = cleaned_text[len(prefix):]
        else:
            cleaned_text = cleaned_text
        # 把第一个链的输出（也就是问题）存入
        self.task_step_question = cleaned_text
        return cleaned_text


    @staticmethod
    def _into_database_query(callback, resource_id, **kwargs) -> None:
        """
        插入数据到向量数据库,检查唯一
        :param union_id_key:  唯一标识
        :param page_content_key:  数据列表
        :param properties_list:  数据列表
        :return: None
        """
        # 提取所有数据的唯一ID
        union_ids = [
            str(item.get(kwargs.get("union_id_key")))
            for item in kwargs.get("properties_list")
        ]
        if len(union_ids) == 0:
            callback([])
            return
        if kwargs.get("properties_list") == 0:
            callback([])
            return
        # 从数据库查询已存在的ID（get_doc_by_ids），提取这些记录的ID值（exist_ids）
        response = kwargs.get("collection").get_doc_by_ids(ids=union_ids)
        exist_ids = [o.metadata[kwargs.get("union_id_key")] for o in response]

        print("********************把所有能找到的都打印：*********************")
        print("page_content_key:  ", kwargs.get("page_content_key"))
        print("union_id_key:  ", kwargs.get("union_id_key"))

        docs = []
        # 遍历检索到的每一条数据
        for item in kwargs.get("properties_list"):
            print("****************************检索到的内容列表response：")
            print(item)
            # 元数据：复制这条数据中，除了正文内容外的所有信息
            metadata = {
                key: value
                for key, value in item.items()
                if key != kwargs.get("page_content_key")
            }
            print(metadata)
            # 如果这条数据不是已经存在的，就把它封装好，放入列表中
            if item.get(kwargs.get("union_id_key")) not in exist_ids:
                doc = DocumentWithVSId(
                    id=item.get(kwargs.get("union_id_key")),
                    page_content=item.get(kwargs.get("page_content_key")),
                    metadata=metadata,
                )
                docs.append(doc)

        # 将封装好的所有数据，放入向量数据库中，会为文本自动生成嵌入向量
        kwargs.get("collection").do_add_doc(docs)
        # 保存向量存储（持久化到磁盘）
        kwargs.get("collection").save_vector_store()
        # 召回
        response = kwargs.get("collection").do_search(
            query=kwargs.get("task_step_question"), top_k=10, score_threshold=0.6
        )
        callback(response)

    # 为特定任务步骤生成问答上下文（搜索相关答案并保存），无返回值，结果直接存入存储系统
    def invoke_task_step_question_context(self) -> None:
        """
        对任务步骤进行抽取，得到任务步骤的上下文
        3、增加项目
        """

        top_k = 4  # 可选参数，默认查询返回前 4个结果
        # search_papers：学术论文库查询
        if self.data_base == "search_papers":
            # 来自src\dreamsboard\dreamsboard\dreams\task_step_to_question_chain\weaviate\prepare_load.py，这里的代码很重要
            properties_list = exe_query(self.task_step_question,
                                        top_k)  # task_step_question就是上面第二个函数，也就是第一个链的输出
        # properties_list是一个列表，里面有11个字典，每个字典有ref_id、paper_id、paper_title、chunk_id、chunk_text、original_filename
        # 插入数据到数据库
        # 设置超时时间，例如 10 秒
        timeout = 20
        start_time = time.time()
        # 通过事件管理器异步执行_into_database_query，传递参数包括：数据库连接、唯一ID键、内容键等
        event_id = event_manager.register_event(
            # 调用第二个函数，完成将检索到的内容存入向量数据库，再召回的步骤
            self._into_database_query,
            resource_id=f"resource_collection_{self.collection.kb_name}",  # 就是 resource_collection_ 拼接上当前主题的哈希值
            kwargs={
                "collection": self.collection,
                "union_id_key": "ref_id",
                "page_content_key": "chunk_text",
                "properties_list": properties_list,
                "task_step_question": self.task_step_question,
            },
        )
        # 最多等待20秒（timeout），每0.5秒检查一次结果
        results = None
        while (results is None or len(results) == 0) and (time.time() - start_time < timeout):
            # 每次循环延时 0.5 秒
            time.sleep(0.5)

            results = event_manager.get_results(event_id)
        response = results[0]
        if len(response) == 0:
            return

        chunk_texts = []
        ref_ids = []
        chunk_ids = []
        paper_titles = []
        print("****************************\n检索到的内容response：")
        print(response)
        print("***************************************************")
        for o in response:
            chunk_texts.append(o.page_content)  # 每本书的正文内容
            ref_ids.append(o.metadata["ref_id"])  # 每本书的“图书馆编号”
            chunk_ids.append(o.metadata["chunk_id"])  # 该片段的“章节编号”
            paper_titles.append(o.metadata.get("paper_title", ""))  # 书的名字
        # 使用cross_encoder模型对结果相关性排序
        rankings = self.cross_encoder.rank(
            self.task_step_question,
            chunk_texts,
            show_progress_bar=True,  # 显示进度条
            return_documents=True,  # 返回完整文本
            convert_to_tensor=True,  # 使用Tensor加速
        )

        task_step_question_context = []
        # 召回问题前3条，存入task_step_question_context
        for i, ranking in enumerate(rankings[:3]):

            task_step_question_context.append(
                TaskStepContext(
                    ref_id=str(ref_ids[i]),
                    paper_title=str(paper_titles[i]),
                    chunk_id=str(chunk_ids[i]),
                    score=ranking["score"],  # 记录匹配分数
                    text=ranking["text"],  # 记录文本内容
                )
            )
        # task_step_question_context是个3元素列表，每个元素都是查询到的内容（自定义的TaskStepContext类型），重点是里面有paper_title,score,ref_id,text,chunk_id
        # rankings corpus_id 的索引与ref_ids的索引一致
        # 把最终筛选结果存入"研究笔记"中，方便后续查看
        self.task_step_question_context = task_step_question_context


    def export_csv_file_path(self, task_step_id: str) -> str:
        """
        3、对召回内容与问题 导出csv文件
        """
        task_step_node = self.task_step_store.get_task_step(task_step_id)  # 拿到当前这个步骤的

        table_data = []
        row = [
            task_step_id,
            task_step_node.task_step_name,  # 步骤的名字
            task_step_node.task_step_level,  # 步骤的层级（比如1.1,2.1之类的）
        ]

        table_data.append(row)
        row2 = [
            task_step_id,
            task_step_node.task_step_question,  # 第一个链的输出（也就是将步骤转化为问题）
            task_step_node.task_step_level,
        ]
        table_data.append(row2)
        for context in task_step_node.task_step_question_context:  # 前面那个函数最终拿到的文本（不是字符串，是自定义的TaskStepContext类型）
            row3 = [
                    task_step_id,
                    f"ref_ids: {context['ref_id']}, chunk_ids: {context['chunk_id']}, Score: {context['score']:.4f}, Text: {context['text']}",
                    task_step_node.task_step_level,
                    ]
            table_data.append(row3)

        table = pd.DataFrame(table_data, columns=["角色", "内容", "分镜"])

        table.to_csv(
            f"{self.base_path}/storage/{task_step_id}.csv", index=False, escapechar="\\"
        )

        return f"{self.base_path}/storage/{task_step_id}.csv"
