import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.email import SMTPConfigurationError, validate_smtp_config

try:
    config = validate_smtp_config()
except SMTPConfigurationError as exc:
    print("smtp_config_valid= False")
    print(f"error= {exc}")
else:
    print("smtp_config_valid= True")
    print(f"host= {config.host}")
    print(f"port= {config.port}")
    print(f"username_present= {bool(config.username)}")
    print(f"password_present= {bool(config.password)}")
    print(f"from_email= {config.from_email}")
