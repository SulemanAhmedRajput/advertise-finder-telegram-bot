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