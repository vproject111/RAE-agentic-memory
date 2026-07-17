from pydantic import BaseModel


class ContractCompatibility(BaseModel):
    contract_name: str
    current_version: str
    compatible_with: list[str]
