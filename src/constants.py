# ======================
# Conversation States
# ======================
# (Note: The original conversation states from your snippet have been extended
# to separate the steps for creating a case. You may adjust the numbering as needed.)
SELECT_LANG = 0
SHOW_DISCLAIMER = 1
CHOOSE_COUNTRY = 2
CHOOSE_CITY = 3
CHOOSE_PROVINCE = 4  # New state for province selection
CHOOSE_ACTION = 5
CHOOSE_WALLET_TYPE = 6
NAME_WALLET = 7
CREATE_CASE_NAME = 8
CREATE_CASE_MOBILE = 9
CREATE_CASE_TAC = 10
CREATE_CASE_DISCLAIMER = 11
CREATE_CASE_REWARD_TYPE = 12
CREATE_CASE_REWARD_AMOUNT = 13
CREATE_CASE_PERSON_NAME = 14
CREATE_CASE_RELATIONSHIP = 15
CREATE_CASE_PHOTO = 16
CREATE_CASE_LAST_SEEN_LOCATION = 17
CREATE_CASE_SEX = 18
CREATE_CASE_AGE = 19
CREATE_CASE_HAIR_COLOR = 20
CREATE_CASE_EYE_COLOR = 21
CREATE_CASE_HEIGHT = 22
CREATE_CASE_WEIGHT = 23
CREATE_CASE_DISTINCTIVE_FEATURES = 24
CREATE_CASE_SUBMIT = 25
ENTER_PRIVATE_KEY = 26
TRANSFER_CONFIRMATION = 27
END = 28
# Additional states for Wallet and Settings flows
WALLET_MENU = 80
WAITING_FOR_MOBILE = 81
SETTINGS_MENU = 92
# Additional flow of the listing command
CASE_LIST = 100
CASE_DETAILS = 101
UPLOAD_PROOF = 102  # New state for uploading proof
ENTER_LOCATION = 103  # New state for entering the location where the person was found

# ======================
# Language Data & Constants
# ======================
LANG_DATA = {
    "en": {
        "lang_choice": "English",
        "lang_button": "English",
        "start_msg": "Hello! Welcome to People Finder Bot.\nPlease select your language:",
        "choose_country": "Please enter your country name (partial name allowed):",
        "country_not_found": "No matching countries found. Please try again:",
        "country_multi": "Multiple countries found (Page {page} of {total}):",
        "country_selected": "You have selected",
        "disclaimer_title": "Disclaimer\n\n",
        "disclaimer_text": (
            "1. All bounties are held in escrow.\n"
            "2. AI-generated fake content is prohibited.\n"
            "3. For lawful, ethical use only.\n"
            "4. Report to authorities first when locating someone.\n"
            "5. We are not liable for misuse.\n"
            "6. Community-driven approach; verify carefully.\n"
            "7. We do not handle reward disputes.\n\n"
            "By using this bot, you agree to these terms."
        ),
        "agree_btn": "I Agree ✅",
        "disagree_btn": "I Disagree ❌",
        "disagree_end": "You did not agree. Conversation ended.",
        "enter_city": "Please enter your city name (partial name allowed):",
        "city_not_found": "No matching cities found. Please try again:",
        "city_multi": "Multiple cities found (Page {page} of {total}):",
        "city_selected": "City recorded:",
        "choose_action": "Would you like to Advertise or Find People?",
        "advertise_btn": "Advertise 📢",
        "find_btn": "Find People 👥",
        "find_dev": "Find People is under development.",
        "choose_wallet": "Please choose the type of wallet:",
        "sol_wallet": "Solana (SOL)",
        "btc_wallet": "Bitcoin (BTC)",
        "btc_dev": "BTC wallet creation is under development.",
        "wallet_name_prompt": "You've chosen Solana wallet.\nPlease enter a name for your wallet:",
        "wallet_name_empty": "Wallet name cannot be empty. Please try again:",
        "wallet_create_ok": "✅ Wallet Created Successfully!\n\n",
        "wallet_create_err": "❌ Error creating wallet.",
        "cancel_msg": "Operation cancelled. Use /start to begin again.",
        "invalid_choice": "Invalid choice. Conversation ended.",
        # Milestone 2 Additions
        "account_wallet_type": "Account Wallet Type (SOL | BTC)",
        "menu_wallet_title": "Wallet Menu",
        "btn_refresh": "🔄 Refresh",
        "btn_sol": "SOL",
        "btn_btc": "BTC",
        "btn_show_address": "Show Address",
        "btn_create_wallet": "Create Wallet",
        "btn_delete_wallet": "Delete Wallet",
        "wallet_no_exists": "No wallet found.",
        "wallet_exists": "Existing wallet:\nName: {name}\nPublic Key: {pub}\nBalance: {bal} SOL",
        "wallet_deleted": "✅ Wallet deleted successfully.",
        "wallet_not_deleted": "No wallet to delete.",
        "wallet_refreshed": "Balance updated:\nName: {name}\nPublic Key: {pub}\nBalance: {bal} SOL",
        "menu_settings_title": "Settings Menu",
        "btn_language": "Change Language",
        "btn_mobile_number": "Mobile Number",
        "btn_close_menu": "Close Menu",
        "enter_mobile": "Please type your mobile number:",
        "mobile_saved": "✅ Mobile number saved: {number}",
        "lang_updated": "Language has been updated.",
        # Case Functionality
        "create_case_title": "Create New Case",
        "enter_name": "Enter your name:",
        "enter_mobile": "Enter your mobile number (TAC will be sent here):",
        "enter_tac": "Enter the TAC sent to your mobile:",
        "verify_tac": "Verifying TAC...",
        "tac_verified": "✅ TAC verified successfully.",
        "tac_invalid": "❌ Invalid TAC. Please try again.",
        "disclaimer_2": (
            "Disclaimer 2:\n\n"
            "1. The reward amount will be held in escrow until the case is resolved.\n"
            "2. Misuse of this service is prohibited.\n"
            "3. All information provided will be publicly visible.\n\n"
            "Do you agree?"
        ),
        "enter_reward_amount": "Enter the reward amount:",
        "insufficient_funds": "Insufficient funds. Please top up your wallet.",
        "top_up_tutorial": (
            "How to top up your wallet:\n"
            "1. Open your Solana wallet app (e.g., Phantom, Solflare).\n"
            "2. Copy your wallet address: {address}\n"
            "3. Send at least {amount} SOL to the address."
        ),
        "enter_person_name": "Enter the name of the person you're looking for:",
        "relationship": "Your relationship to the person:",
        "upload_photo": "Upload a clear photo of the person:",
        "last_seen_location": "Enter the last seen location (province):",
        "sex": "Sex (Male/Female):",
        "age": "Age:",
        "hair_color": "Hair Color:",
        "eye_color": "Eye Color:",
        "height": "Height (cm):",
        "weight": "Weight (kg):",
        "distinctive_features": "Distinctive physical features (e.g., Tattoo of eagle):",
        "reason_for_finding": "Reason for finding:",
        "submit_case": "Submit Case",
        "case_submitted": "✅ Case submitted successfully!\nCase Number: {case_no}",
        "case_failed": "❌ Failed to submit case. Please try again.",
        "escrow_transfer": "Reward amount transferred to escrow wallet.",
        # Find People Functionality
        "choose_province": "Please select a province:",
        "more_provinces": "More provinces...",
        "case_list": "Available cases:",
        "case_details": "Case Details:",
        "save_case": "Save Case",
        "found_case": "Found Case",
        "upload_proof": "Please upload a photo or video as proof.",
        "invalid_proof": "Invalid proof. Please upload a photo or video.",
        "enter_location": "Enter the location where the person was found:",
        "notify_advertiser": "The advertiser has been notified. Thank you!",
        "province_not_found": "No matching provinces found. Please try again:",
        "province_multi": "Multiple provinces found (Page {page} of {total}):",
        "province_selected": "You have selected",
    },
    "zh": {
        "lang_choice": "中文",
        "lang_button": "中文",
        "start_msg": "你好！欢迎使用 People Finder 机器人。\n请选择语言：",
        "choose_country": "请输入您的国家名称（支持模糊搜索）：",
        "country_not_found": "未找到匹配的国家。请重试：",
        "country_multi": "找到多个国家 (第 {page} 页，共 {total} 页)：",
        "country_selected": "您已选择",
        "disclaimer_title": "免责声明\n\n",
        "disclaimer_text": (
            "1. 所有悬赏由平台托管。\n"
            "2. 严禁使用 AI 虚假内容。\n"
            "3. 仅限合法合规使用。\n"
            "4. 寻人应先向当地警方或政府部门报备。\n"
            "5. 平台对任何滥用不承担责任。\n"
            "6. 社区互助，需自行核实。\n"
            "7. 平台不介入赏金纠纷。\n\n"
            "使用本机器人即表示您同意上述条款。"
        ),
        "agree_btn": "同意 ✅",
        "disagree_btn": "不同意 ❌",
        "disagree_end": "您不同意，结束对话。",
        "enter_city": "请输入您的城市名称（支持模糊搜索）：",
        "city_not_found": "未找到匹配的城市。请重试：",
        "city_multi": "找到多个城市 (第 {page} 页，共 {total} 页)：",
        "city_selected": "已记录城市：",
        "choose_action": "请选择：发布悬赏或寻找信息？",
        "advertise_btn": "发布悬赏 📢",
        "find_btn": "寻找信息 👥",
        "find_dev": "寻找信息功能正在开发中。",
        "choose_wallet": "请选择要创建的钱包类型：",
        "sol_wallet": "Solana (SOL)",
        "btc_wallet": "比特币 (BTC)",
        "btc_dev": "BTC 钱包功能正在开发中。",
        "wallet_name_prompt": "您选择了 Solana 钱包。\n请输入钱包名称：",
        "wallet_name_empty": "钱包名称不能为空，请重新输入：",
        "wallet_create_ok": "✅ 成功创建钱包！\n\n",
        "wallet_create_err": "❌ 创建钱包时出错。",
        "cancel_msg": "操作已取消。输入 /start 重新开始。",
        "invalid_choice": "无效选择，结束对话。",
        # Milestone 2 Additions
        "account_wallet_type": "Account Wallet Type (SOL | BTC)",
        "menu_wallet_title": "钱包菜单",
        "btn_refresh": "🔄 刷新",
        "btn_sol": "SOL",
        "btn_btc": "BTC",
        "btn_show_address": "显示地址",
        "btn_create_wallet": "创建钱包",
        "btn_delete_wallet": "删除钱包",
        "wallet_no_exists": "当前没有可用钱包。",
        "wallet_exists": "现有钱包:\n名称: {name}\n公钥: {pub}\n余额: {bal} SOL",
        "wallet_deleted": "✅ 钱包已成功删除。",
        "wallet_not_deleted": "没有钱包可删除。",
        "wallet_refreshed": "余额已更新:\n名称: {name}\n公钥: {pub}\n余额: {bal} SOL",
        "menu_settings_title": "设置菜单",
        "btn_language": "更改语言",
        "btn_mobile_number": "手机号",
        "btn_close_menu": "关闭菜单",
        "enter_mobile": "请输入您的手机号：",
        "mobile_saved": "✅ 已保存手机号：{number}",
        "lang_updated": "语言已更新。",
        # Case Functionality
        "create_case_title": "创建新案件",
        "enter_name": "请输入您的姓名：",
        "enter_mobile": "请输入您的手机号（将发送验证码至此号码）：",
        "enter_tac": "请输入发送到您手机的验证码：",
        "verify_tac": "正在验证验证码...",
        "tac_verified": "✅ 验证码验证成功。",
        "tac_invalid": "❌ 验证码无效，请重试。",
        "disclaimer_2": (
            "免责声明 2:\n\n"
            "1. 赏金金额将托管至案件解决。\n"
            "2. 禁止滥用本服务。\n"
            "3. 提供的所有信息将公开可见。\n\n"
            "您是否同意？"
        ),
        "enter_reward_amount": "请输入赏金金额：",
        "insufficient_funds": "余额不足，请充值钱包。",
        "top_up_tutorial": (
            "如何充值钱包：\n"
            "1. 打开您的 Solana 钱包应用（例如 Phantom、Solflare）。\n"
            "2. 复制您的钱包地址：{address}\n"
            "3. 向该地址发送至少 {amount} SOL。"
        ),
        "enter_person_name": "请输入您要寻找的人的姓名：",
        "relationship": "您与该人的关系：",
        "upload_photo": "上传清晰的人物照片：",
        "last_seen_location": "请输入最后出现的位置（省份）：",
        "sex": "性别（男/女）：",
        "age": "年龄：",
        "hair_color": "发色：",
        "eye_color": "眼睛颜色：",
        "height": "身高（厘米）：",
        "weight": "体重（公斤）：",
        "distinctive_features": "显著的身体特征（例如，鹰形纹身）：",
        "reason_for_finding": "寻找原因：",
        "submit_case": "提交案件",
        "case_submitted": "✅ 案件提交成功！\n案件编号：{case_no}",
        "case_failed": "❌ 提交案件失败，请重试。",
        "escrow_transfer": "赏金金额已转入托管钱包。",
        # Find People Functionality
        "choose_province": "请选择省份：",
        "more_provinces": "更多省份...",
        "case_list": "可用案件：",
        "case_details": "案件详情：",
        "save_case": "保存案件",
        "found_case": "找到案件",
        "upload_proof": "请上传照片或视频作为证据。",
        "invalid_proof": "无效证据。请上传照片或视频。",
        "enter_location": "请输入发现该人的地点：",
        "notify_advertiser": "已通知广告主。谢谢！",
        "province_not_found": "未找到匹配的省份。请重试：",
        "province_multi": "找到多个省份 (第 {page} 页，共 {total} 页)：",
        "province_selected": "已记录省份：",
    },
}

ITEMS_PER_PAGE = 10  # Number of items per page for pagination
WALLETS_DIR = "wallets"  # Directory to store user wallets
PHOTOS_DIR = "photos"  # Directory to store uploaded photos
PROOFS_DIR = "proofs"  # Directory to store proof uploads

# A simple in-memory data store for user preferences (language, etc.)
user_data_store = {}


def get_text(user_id, key):
    """Get the localized text for a given key based on user language."""
    lang = user_data_store.get(user_id, {}).get("lang", "en")
    return LANG_DATA.get(lang, LANG_DATA["en"]).get(key, f"Undefined text for {key}")
