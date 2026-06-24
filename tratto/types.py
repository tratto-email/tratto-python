from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class SendEmailOptions:
    from_: str
    to: Union[str, list[str]]
    subject: str
    html: Optional[str] = None
    text: Optional[str] = None
    reply_to: Optional[str] = None
    cc: Optional[Union[str, list[str]]] = None
    bcc: Optional[Union[str, list[str]]] = None
    headers: Optional[dict[str, str]] = None
    tags: Optional[dict[str, str]] = None
    idempotency_key: Optional[str] = None


@dataclass
class Email:
    id: str
    from_: str
    to: list[str]
    subject: str
    status: str
    created_at: str
    delivered_at: Optional[str] = None


class TrattoError(Exception):
    def __init__(self, message: str, code: str, status_code: int):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
