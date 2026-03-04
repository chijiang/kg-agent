import common_pb2 as _common_pb2
import survey_pb2 as _survey_pb2
import time_period_pb2 as _time_period_pb2
import location_pb2 as _location_pb2
import product_pb2 as _product_pb2
import so_information_pb2 as _so_information_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WorkTicket(_message.Message):
    __slots__ = ("responseid", "osat", "why_osat_en_mask", "first_time_resolution", "ease_use", "survey", "time_period", "location", "product", "so_information")
    RESPONSEID_FIELD_NUMBER: _ClassVar[int]
    OSAT_FIELD_NUMBER: _ClassVar[int]
    WHY_OSAT_EN_MASK_FIELD_NUMBER: _ClassVar[int]
    FIRST_TIME_RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    EASE_USE_FIELD_NUMBER: _ClassVar[int]
    SURVEY_FIELD_NUMBER: _ClassVar[int]
    TIME_PERIOD_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    PRODUCT_FIELD_NUMBER: _ClassVar[int]
    SO_INFORMATION_FIELD_NUMBER: _ClassVar[int]
    responseid: str
    osat: int
    why_osat_en_mask: str
    first_time_resolution: int
    ease_use: int
    survey: _survey_pb2.Survey
    time_period: _time_period_pb2.TimePeriod
    location: _location_pb2.Location
    product: _product_pb2.Product
    so_information: _so_information_pb2.SOInformation
    def __init__(self, responseid: _Optional[str] = ..., osat: _Optional[int] = ..., why_osat_en_mask: _Optional[str] = ..., first_time_resolution: _Optional[int] = ..., ease_use: _Optional[int] = ..., survey: _Optional[_Union[_survey_pb2.Survey, _Mapping]] = ..., time_period: _Optional[_Union[_time_period_pb2.TimePeriod, _Mapping]] = ..., location: _Optional[_Union[_location_pb2.Location, _Mapping]] = ..., product: _Optional[_Union[_product_pb2.Product, _Mapping]] = ..., so_information: _Optional[_Union[_so_information_pb2.SOInformation, _Mapping]] = ...) -> None: ...

class GetWorkTicketRequest(_message.Message):
    __slots__ = ("responseid",)
    RESPONSEID_FIELD_NUMBER: _ClassVar[int]
    responseid: str
    def __init__(self, responseid: _Optional[str] = ...) -> None: ...

class ListWorkTicketsRequest(_message.Message):
    __slots__ = ("query", "pagination")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    query: str
    pagination: _common_pb2.PaginationRequest
    def __init__(self, query: _Optional[str] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListWorkTicketsResponse(_message.Message):
    __slots__ = ("items", "pagination")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[WorkTicket]
    pagination: _common_pb2.PaginationResponse
    def __init__(self, items: _Optional[_Iterable[_Union[WorkTicket, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...
