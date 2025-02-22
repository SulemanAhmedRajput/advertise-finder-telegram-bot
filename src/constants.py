from telegram.ext import (
    ConversationHandler,
)

from enum import Enum


class State(Enum):
    SELECT_LANG = "SELECT_LANG"
    SHOW_DISCLAIMER = "SHOW_DISCLAIMER"
    CHOOSE_COUNTRY = "CHOOSE_COUNTRY"
    CHOOSE_PROVINCE = "CHOOSE_PROVINCE"
    CHOOSE_CITY = "CHOOSE_CITY"
    CHOOSE_ACTION = "CHOOSE_ACTION"
    CHOOSE_WALLET_TYPE = "CHOOSE_WALLET_TYPE"
    NAME_WALLET = "NAME_WALLET"

    CREATE_CASE_NAME = "CREATE_CASE_NAME"
    CREATE_CASE_MOBILE = "CREATE_CASE_MOBILE"
    CREATE_CASE_TAC = "CREATE_CASE_TAC"
    CREATE_CASE_DISCLAIMER = "CREATE_CASE_DISCLAIMER"
    CREATE_CASE_REWARD_TYPE = "CREATE_CASE_REWARD_TYPE"
    CREATE_CASE_REWARD_AMOUNT = "CREATE_CASE_REWARD_AMOUNT"
    CREATE_CASE_PERSON_NAME = "CREATE_CASE_PERSON_NAME"
    CREATE_CASE_RELATIONSHIP = "CREATE_CASE_RELATIONSHIP"
    CREATE_CASE_PHOTO = "CREATE_CASE_PHOTO"
    CREATE_CASE_LAST_SEEN_LOCATION = "CREATE_CASE_LAST_SEEN_LOCATION"
    CREATE_CASE_SEX = "CREATE_CASE_SEX"
    CREATE_CASE_AGE = "CREATE_CASE_AGE"
    CREATE_CASE_HAIR_COLOR = "CREATE_CASE_HAIR_COLOR"
    CREATE_CASE_EYE_COLOR = "CREATE_CASE_EYE_COLOR"
    CREATE_CASE_HEIGHT = "CREATE_CASE_HEIGHT"
    CREATE_CASE_WEIGHT = "CREATE_CASE_WEIGHT"
    CREATE_CASE_DISTINCTIVE_FEATURES = "CREATE_CASE_DISTINCTIVE_FEATURES"
    CREATE_CASE_SUBMIT = "CREATE_CASE_SUBMIT"

    ENTER_PRIVATE_KEY = "ENTER_PRIVATE_KEY"
    ENTER_PUBLIC_KEY = "ENTER_PUBLIC_KEY"
    CONFIRM_TRANSFER = "CONFIRM_TRANSFER"
    TRANSFER_CONFIRMATION = "TRANSFER_CONFIRMATION"

    WALLET_MENU = "WALLET_MENU"
    WAITING_FOR_MOBILE = "WAITING_FOR_MOBILE"
    CREATE_WALLET = "CREATE_WALLET"
    SELECT_WALLET = "SELECT_WALLET"

    CASE_LIST = "CASE_LIST"
    CASE_DETAILS = "CASE_DETAILS"
    UPLOAD_PROOF = "UPLOAD_PROOF"
    ENTER_LOCATION = "ENTER_LOCATION"
    ADVERTISER_CONFIRMATION = "ADVERTISER_CONFIRMATION"
    MOBILE_VERIFICATION = "MOBILE_VERIFICATION"

    SETTINGS_MENU = "SETTINGS_MENU"
    MOBILE_MANAGEMENT = "MOBILE_MANAGEMENT"
    HISTORY_MENU = "HISTORY_MENU"

    ENTER_NUMBER = "ENTER_NUMBER"
    VERIFY_OTP = "VERIFY_OTP"

    VIEW_HISTORY = "VIEW_HISTORY"
    DELETE_WALLET = "DELETE_WALLET"
    SHOW_ADDRESS = "SHOW_ADDRESS"
    HANDLER_END = ConversationHandler.END
    END = "END"


# ======================
# Language Data & Constants
# ======================


DUMMY_DATA = {
    "en": {
        "enter_mobile": "Please type your mobile number:",
        "mobile_saved": "✅ Mobile number saved: {number}",
        # Case Functionality
        "create_case_title": "Create New Case",
        "enter_name": "Enter your name:",
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
        "missing_information": "❌ Missing information. Please start over.",
        "notification_text": (
            "🚨 Potential Match Alert! 🚨\n\n"
            "Case #{case_no}: {person_name}\n"
            "📍 Reported Location: {location}\n"
            "🔗 Proof File: {proof_path}"
        ),
        "reply_to_advertiser": "✅ The case owner has been notified!\n\n"
        "Thank you for your contribution. We'll contact you if more information is needed.",
        "error_sending_notification": "❌ Error sending notification. Please try again later.",
        "proof_upload": "Please upload photo/video proof:",
        "error_processing_proof": "❌ Error processing your proof. Please try again.",
        "case_not_found": "❌ Case not found.",
        "proof_received": "✅ Proof received. \n \n  Please enter the location where you found this person:",
        "error_upload_proof": "❌ Please upload a photo or video.",
        "no_case_selected": "Error: No case selected. Please start over.",
        "error_loading_case": "Error loading case details, Please try again.",
        "mark_as_found": "✅ Mark as Found",
        "back_to_list": "🔙 Back to List",
        "case_not_found_in_province": "No cases found in this province.",
        "select_province": "Please select a province first.",
        "no_case_found_in_province": "No cases found for {province}.",
        # Remaining messages
        "choose_number_or_add_new": "Choose a number or add a new one:",
        "add_new_number": "Add New Number",
        "enter_new_number": "Please enter a new number:",
        "number_already_exists": "The number <b>{number}</b> already exists.",
        "otp_sent": "An OTP has been sent to <b>{number}</b>. Please enter the OTP to verify.",
        "number_added": "The number <b>{number}</b> has been added successfully.",
        "invalid_otp": "Invalid OTP. Please try again.",
    },
    "zh": {
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
        "missing_information": "❌ 缺少信息。请重新开始。",
        "notification_text": (
            "🚨 潜在匹配警报！🚨\n\n"
            "案件 #{case_no}: {person_name}\n"
            "📍 报告位置: {location}\n"
            "🔗 证据文件: {proof_path}"
        ),
        "reply_to_advertiser": "✅ 案件所有者已收到通知！\n\n"
        "感谢您的贡献。如果需要更多信息，我们会联系您。",
        "error_sending_notification": "❌ 发送通知时出错。请稍后再试。",
        "proof_upload": "请上传照片/视频证据：",
        "error_processing_proof": "❌ 处理您的证据时出错。请重试。",
        "case_not_found": "❌ 未找到案件。",
        "proof_received": "✅ 证据已收到。\n\n请输入您发现此人的位置：",
        "error_upload_proof": "❌ 请上传照片或视频。",
        "no_case_selected": "错误: 未选择案件。请重新开始。",
        "error_loading_case": "加载案件详情时出错，请重试。",
        "mark_as_found": "✅ 标记为已找到",
        "back_to_list": "🔙 返回列表",
        "case_not_found_in_province": "该省份未找到案件。",
        "select_province": "请先选择一个省份。",
        "no_case_found_in_province": "在 {province} 没有找到相关案件。",
        "choose_number_or_add_new": "选择一个号码或添加新号码：",
        "add_new_number": "添加新号码",
        "enter_new_number": "请输入一个新号码：",
        "number_already_exists": "号码 <b>{number}</b> 已存在。",
        "otp_sent": "已向 <b>{number}</b> 发送验证码。请输入验证码以验证。",
        "number_added": "号码 <b>{number}</b> 已成功添加。",
        "invalid_otp": "无效的验证码。请重试。",
    },
}


WALLETS_DIR = "wallets"  # Directory to store user wallets
PHOTOS_DIR = "photos"  # Directory to store uploaded photos
PROOFS_DIR = "proofs"  # Directory to store proof uploads

# A simple in-memory data store for user preferences (language, etc.)
