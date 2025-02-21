from constant.case_constant import CASE_CONSTANT
from constant.settings_constant import SETTINGS_CONSTANT
from constant.start_constant import START_LANG_DATA
from constant.wallet_constant import WALLET_LANG_DATA


def merge_lang_data(lang_data, *new_constants):
    for new_data in new_constants:  # Loop through each constant
        for lang, entries in new_data.items():
            if lang in lang_data:
                lang_data[lang].update(entries)  # Merge into existing language
            else:
                lang_data[lang] = entries  # Add new language section if missing
    return lang_data


LANG_DATA = merge_lang_data(
    START_LANG_DATA, WALLET_LANG_DATA, SETTINGS_CONSTANT, CASE_CONSTANT
)


user_data_store = {}


def get_text(user_id, key):
    """Get the localized text for a given key based on user language."""
    lang = user_data_store.get(user_id, {}).get("lang", "en")
    return LANG_DATA.get(lang, LANG_DATA["en"]).get(key, f"Undefined text for {key}")


# Pagination Constants
ITEMS_PER_PAGE = 10  # Number of items per page for pagination
