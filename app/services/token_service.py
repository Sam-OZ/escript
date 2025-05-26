# app/services/token_service.py
from get_token import get_access_token

class TokenService:
    def get_token(self) -> str:
        return get_access_token()

token_service = TokenService()
