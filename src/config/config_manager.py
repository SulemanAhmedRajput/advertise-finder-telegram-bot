import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_NAME = os.getenv("MONGODB_NAME")
TOKEN = os.getenv("TOKEN")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

STAKE_WALLET_PRIVATE_KEY = os.getenv("STAKE_WALLET_PRIVATE_KEY")
STAKE_WALLET_PUBLIC_KEY = os.getenv("STAKE_WALLET_PUBLIC_KEY")
TRON_WALLET_PRIVATE_KEY = os.getenv("TRON_WALLET_PRIVATE_KEY")
TRON_WALLET_PUBLIC_KEY = os.getenv("TRON_WALLET_PUBLIC_KEY")

TAX_COLLECT_PRIVATE_KEY = os.getenv("TAX_COLLECT_PRIVATE_KEY")
TAX_COLLECT_PUBLIC_KEY = os.getenv("TAX_COLLECT_PUBLIC_KEY")
CLIENT = os.getenv("CLIENT")
OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID")
TRON_CLIENT_NETWORK = os.getenv("TRON_CLIENT_NETWORK")
