# app/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field, AnyHttpUrl, ConfigDict

class Settings(BaseSettings):
    # Identity server token endpoint (direct)
    token_url: AnyHttpUrl = Field(..., env="TOKEN_URL")
    # API version
    app_name: str = "Televita API"
    description: str = "Telehealth prescription & pricing service"
    version: str = "0.1.0"

    # OAuth2 client credentials
    client_id: str = Field(..., env="CLIENT_ID")
    client_secret: str = Field(..., env="CLIENT_SECRET")
    scope: str = Field(..., env="SCOPE")

    # APIM subscription key for both token and FHIR calls
    ocp_apim_subscription_key: str = Field(..., env="OCP_APIM_SUBSCRIPTION_KEY")

    # FHIR API base (behind the APIM façade)
    fhir_api_base: AnyHttpUrl = Field(..., env="FHIR_API_BASE")

    # Path to your RSA private key for client_assertion (if used)
    private_key_path: str = Field("converted_private_key.pem", env="PRIVATE_KEY_PATH")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore any other vars
    )

settings = Settings()
