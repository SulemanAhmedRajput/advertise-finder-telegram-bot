from typing import List
from models.user_model import User


async def get_user_lang(user_id: int) -> str:
    """Get the user's language preference from the database."""
    user = await User.find_one(User.tl_id == user_id)
    return user.lang if user else None

async def save_user_lang(user_id: int, lang: str):
    """Save the user's language preference to the database."""
    user = await User.find_one(User.tl_id == user_id)
    if user:
        user.lang = lang
        await user.save()
    else:
        user = User(tl_id=user_id, lang=lang)
        await user.insert()



async def save_user_mobiles(user_id: int, mobiles: List[str]):
    user = await User.find_one(User.tl_id == user_id)
    if user:
        user.mobile_numbers = mobiles
        await user.save()
    else:
        user = User(tl_id=user_id, lang="en", mobile_numbers=mobiles)
        await user.insert()


async def get_user_mobiles(user_id: int) -> List[str]:
    user = await User.find_one(User.tl_id == user_id)
    if user:
        return user.mobile_numbers
    return []


def validate_mobile(mobile: str) -> bool:
    # Add your validation logic here. For example, checking format or length.
    # Simple validation example for mobile number format.
    import re
    pattern = r"^\+?[1-9]\d{1,14}$"  # E.164 format
    return bool(re.match(pattern, mobile))