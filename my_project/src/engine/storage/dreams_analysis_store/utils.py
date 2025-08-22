from engine.constants import DATA_KEY, TYPE_KEY
from engine.entity.dreams_personality.dreams_personality import DreamsPersonalityNode
from engine.schema import (
    BaseNode,
)


def analysis_to_json(doc: BaseNode) -> dict:
    return {
        DATA_KEY: doc.dict(),
        TYPE_KEY: doc.get_type(),
    }


def json_to_analysis(analysis_dict: dict) -> DreamsPersonalityNode:
    analysis_type = analysis_dict[TYPE_KEY]
    data_dict = analysis_dict[DATA_KEY]
    doc: DreamsPersonalityNode

    if analysis_type == DreamsPersonalityNode.get_type():
        doc = DreamsPersonalityNode.model_validate(data_dict)
    else:
        raise ValueError(f"Unknown doc type: {analysis_type}")

    return doc
