"""Index registry."""

from typing import Dict, Type

from engine.data_structs.data_structs import (
    IndexDict,
    IndexStruct,
)
from engine.data_structs.struct_type import IndexStructType

INDEX_STRUCT_TYPE_TO_INDEX_STRUCT_CLASS: Dict[IndexStructType, Type[IndexStruct]] = {
    IndexStructType.CODE_GENERATOR: IndexDict,
}
