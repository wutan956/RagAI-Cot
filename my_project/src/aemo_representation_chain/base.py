from __future__ import annotations

import logging
import os
import re
from abc import ABC
from typing import Any, Dict, List

from kor.extraction.parser import KorParser
from kor.nodes import Number, Object, Text
from langchain.chains import LLMChain, SequentialChain
from langchain.chains.base import Chain
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import (
    BaseMessage,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel

from document_loaders import KorLoader
from document_loaders.protocol.ner_protocol import TaskStepNode
from aemo_representation_chain.prompts import (
    AEMO_REPRESENTATION_PROMPT_TEMPLATE,
)




class AEMORepresentationChain(ABC):
    aemo_representation_chain: Chain
    kor_dreams_task_step_chain: LLMChain
    kor_schema: Object

    def __init__(
            self,
            start_task_context: str,
            kor_dreams_task_step_chain: LLMChain,
            kor_schema: Object,
            aemo_representation_chain: Chain,
    ):
        self.start_task_context = start_task_context
        self.kor_dreams_task_step_chain = kor_dreams_task_step_chain
        self.kor_schema = kor_schema
        self.aemo_representation_chain = aemo_representation_chain

    @classmethod
    def from_aemo_representation_chain(
            cls,
            llm_runable: Runnable[LanguageModelInput, BaseMessage],  # 主模型
            start_task_context: str,  # 从命令行获取的主题
            kor_dreams_task_step_llm: Runnable[LanguageModelInput, BaseMessage] = None,  # 辅助模型
    ) -> AEMORepresentationChain:
        # 00-判断情感表征是否符合.txt
        prompt_template1 = PromptTemplate(
            input_variables=["start_task_context"],
            template=os.environ.get(
                "AEMO_REPRESENTATION_PROMPT_TEMPLATE",
                AEMO_REPRESENTATION_PROMPT_TEMPLATE,
            ),
        )
        # 通过这个模板和主题，得到模型的输出
        aemo_representation_chain = prompt_template1 | llm_runable | StrOutputParser()

        def wrapper_output(_dict):
            return {
                # 其实这里就是返回一个字典，里面有个aemo_representation_context的键，值是主模型的输出文本
                "aemo_representation_context": _dict["aemo_representation_context"],
            }

        aemo_representation_chain = {
                                        "aemo_representation_context": aemo_representation_chain,
                                    } | RunnableLambda(wrapper_output)

        # 具体看这个py文件里的example，我们传入的就是里面的那段长文本，然后用kor_dreams_task_step_chain去invoke，就能提取出长文本后面的那个字典，
        # 就是模型会自动从长文本里面进行提取归纳
        (
            kor_dreams_task_step_chain,
            schema,
        ) = KorLoader.form_kor_dreams_task_step_builder(
            # src\dreamsboard\dreamsboard\document_loaders\kor_loader.py，传入辅助模型
            llm_runable=llm_runable
            if kor_dreams_task_step_llm is None
            else kor_dreams_task_step_llm
        )
        return cls(
            start_task_context=start_task_context,
            kor_dreams_task_step_chain=kor_dreams_task_step_chain,
            kor_schema=schema,
            aemo_representation_chain=aemo_representation_chain,
        )

    def invoke_kor_dreams_task_step_context(
            self, aemo_representation_context: str
    ) -> List[TaskStepNode]:  # 返回自定义的任务步骤节点，点Ctrl进去就知道了，就是一个由各种str组成的类
        """
        对开始任务进行抽取，得到任务步骤
        :return:
        """
        # aemo_representation_context是情感分析或任务描述文本，是主模型对主题的输出
        # 然后用kor_dreams_task_step_chain去invoke，就能提取出长文本后面的那个字典，具体看上面那个函数
        response = self.kor_dreams_task_step_chain.invoke(aemo_representation_context)
        print("这是kor返回的response：")
        print(response)
        # 是一个字典，里面重点是data这个键，这个键里面的值是一个列表script，script里面每个元素都是一个字典，如下所示，但是可能有20几个元素
        # {
        #     "data": {
        #         "script": [
        #             {"task_step_name": "调研", "task_step_description": "查找相关资料", "task_step_level": "0"},
        #             {"task_step_name": "写代码", "task_step_description": "实现功能", "task_step_level": "1"}
        #         ]
        #     }
        # }
        task_step_list = []
        try:
            step_list = response.get("data").get("script")
            for step in step_list:
                task_step = {
                    "start_task_context":self.start_task_context,  # 任务的初始描述
                    "aemo_representation_context":aemo_representation_context,  # 输入的情感/语义表征文本（主模型对主题的输出）
                    "task_step_name":step.get("task_step_name"),
                    "task_step_description":step.get("task_step_description"),
                    "task_step_level":step.get("task_step_level")
                }
                task_step_list.append(task_step)
        except Exception as e:
            print("对开始任务进行抽取，得到任务步骤，失败, 重新尝试", e)

        return task_step_list

    # 就是调用aemo_representation_chain也就是主模型对当前主题的输出
    def invoke_aemo_representation_context(self) -> Dict[str, Any]:
        return self.aemo_representation_chain.invoke(
            {"start_task_context": self.start_task_context}
        )
