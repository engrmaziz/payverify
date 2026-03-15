from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SMS_WEBHOOK_SECRET: str
    RESEND_API_KEY: str = ""
    ADMIN_EMAIL: str = ""
    ADMIN_WHATSAPP: str = ""  # optional, for dead-SMS alerts
    SCHOOL_NAME: str = "School"
    FEE_CHECK_ENABLED: bool = True  # cross-check SMS amount vs expected fee

    class Config:
        env_file = ".env"


settings = Settings()
