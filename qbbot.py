#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制订阅机器人 V7 - 简化版（只在关键位置使用动态 Emoji）
避免 Entity_text_invalid 错误
"""

import sys
import io
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, MessageEntity
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError
from dotenv import load_dotenv
import os
import json

# 修复 Windows 控制台编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ 配置 ============
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]

# ============ 动态 Emoji ID ============
# 按钮用
EMOJI_SETTINGS = os.getenv('EMOJI_SETTINGS', '5377505475015235101')
EMOJI_CHANNEL = os.getenv('EMOJI_CHANNEL', '5267500801240092311')
EMOJI_ENABLE = os.getenv('EMOJI_ENABLE', '5197434882321567830')
EMOJI_DISABLE = os.getenv('EMOJI_DISABLE', '5197369495739455200')
EMOJI_STATUS = os.getenv('EMOJI_STATUS', '5312441427764989435')
EMOJI_BACK = os.getenv('EMOJI_BACK', '5190741648237161191')
EMOJI_VERIFY = os.getenv('EMOJI_VERIFY', '5197434882321567830')
EMOJI_SUBSCRIBE = os.getenv('EMOJI_SUBSCRIBE', '5267500801240092311')
EMOJI_LIST = os.getenv('EMOJI_LIST', '5197288647275071607')

# 文案用（只在新成员欢迎消息中使用）
EMOJI_WAVE = os.getenv('EMOJI_WAVE', '5215638109068220476')
EMOJI_WARNING = os.getenv('EMOJI_WARNING', '5220181540222291016')
EMOJI_MEGAPHONE = os.getenv('EMOJI_MEGAPHONE', '5267500801240092311')
EMOJI_POINT_DOWN = os.getenv('EMOJI_POINT_DOWN', '5197503331215361533')

# 存储配置
CONFIG_FILE = 'force_sub_config.json'
group_settings = {}
admin_groups = {}

# 提示消息自动删除时间（秒）
WARNING_DELETE_SECONDS = 120


def utf16_len(text: str) -> int:
    """计算字符串的 UTF-16 长度"""
    return len(text.encode('utf-16-le')) // 2


def load_config():
    """加载配置"""
    global group_settings, admin_groups
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                group_settings = {int(k): v for k, v in data.get('groups', {}).items()}
                admin_groups = {int(k): v for k, v in data.get('admins', {}).items()}
                logger.info(f"已加载配置：{len(group_settings)} 个群组")
    except Exception as e:
        logger.error(f"加载配置失败：{e}")
        group_settings = {}
        admin_groups = {}


def save_config():
    """保存配置"""
    try:
        data = {
            'groups': group_settings,
            'admins': admin_groups
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("配置已保存")
    except Exception as e:
        logger.error(f"保存配置失败：{e}")


async def is_group_admin(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """检查用户是否是群组管理员"""
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
    except TelegramError:
        return False


def create_main_menu(user_id: int):
    """创建主菜单"""
    user_groups = admin_groups.get(user_id, [])
    
    keyboard = []
    
    if user_groups:
        keyboard.append([
            InlineKeyboardButton(
                text="我的群组列表",
                callback_data="menu_groups",
                api_kwargs={
                    "icon_custom_emoji_id": EMOJI_LIST,
                    "style": "primary"
                }
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="帮助说明",
            callback_data="menu_help",
            api_kwargs={
                "icon_custom_emoji_id": EMOJI_SETTINGS,
                "style": "primary"
            }
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_groups_list(user_id: int):
    """创建群组列表"""
    user_groups = admin_groups.get(user_id, [])
    
    keyboard = []
    
    for group_info in user_groups:
        chat_id = group_info['chat_id']
        title = group_info['title']
        
        settings = group_settings.get(chat_id, {})
        enabled = settings.get('enabled', False)
        status_emoji = "🟢" if enabled else "🔴"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {title}",
                callback_data=f"group_{chat_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="返回",
            callback_data="menu_main",
            api_kwargs={
                "icon_custom_emoji_id": EMOJI_BACK,
                "style": "primary"
            }
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_group_panel(chat_id: int):
    """创建群组配置面板"""
    settings = group_settings.get(chat_id, {})
    enabled = settings.get('enabled', False)
    
    keyboard = []
    
    keyboard.append([
        InlineKeyboardButton(
            text="设置频道",
            callback_data=f"config_channel_{chat_id}",
            api_kwargs={
                "icon_custom_emoji_id": EMOJI_CHANNEL,
                "style": "primary"
            }
        )
    ])
    
    if enabled:
        keyboard.append([
            InlineKeyboardButton(
                text="禁用强制订阅",
                callback_data=f"config_disable_{chat_id}",
                api_kwargs={
                    "icon_custom_emoji_id": EMOJI_DISABLE,
                    "style": "danger"
                }
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                text="启用强制订阅",
                callback_data=f"config_enable_{chat_id}",
                api_kwargs={
                    "icon_custom_emoji_id": EMOJI_ENABLE,
                    "style": "success"
                }
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="查看状态",
            callback_data=f"config_status_{chat_id}",
            api_kwargs={
                "icon_custom_emoji_id": EMOJI_STATUS,
                "style": "primary"
            }
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="返回群组列表",
            callback_data="menu_groups",
            api_kwargs={
                "icon_custom_emoji_id": EMOJI_BACK,
                "style": "primary"
            }
        )
    ])
    
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令 - 使用普通文本，避免 entity 错误"""
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    
    if chat_type == 'private':
        user_groups = admin_groups.get(user_id, [])
        
        if user_groups:
            text = (
                "👋 欢迎回来！\n\n"
                f"你当前管理 {len(user_groups)} 个群组。\n\n"
                "点击下方按钮管理你的群组："
            )
        else:
            text = (
                "👋 你好！我是强制订阅机器人。\n\n"
                "📌 功能说明：\n"
                "• 新成员进群立即禁言\n"
                "• 必须订阅指定频道\n"
                "• 点击验证后自动解除禁言\n\n"
                "💡 使用步骤：\n"
                "1. 将我添加到你的群组\n"
                "2. 给我管理员权限\n"
                "3. 在群组中发送 /bind\n"
                "4. 回到这里配置"
            )
        
        keyboard = create_main_menu(user_id)
        
        await update.message.reply_text(
            text,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "👋 你好！这个机器人会确保新成员订阅指定频道。\n\n"
            "管理员请发送 /bind 绑定此群组，然后私聊我进行配置。"
        )


async def bind_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """绑定群组"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat = update.effective_chat
    
    if chat.type == 'private':
        await update.message.reply_text("❌ 此命令只能在群组中使用！")
        return
    
    if not await is_group_admin(user_id, chat_id, context):
        await update.message.reply_text("❌ 只有管理员才能绑定群组！")
        return
    
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                "❌ 请先给我管理员权限！\n\n"
                "需要的权限：\n"
                "• 删除消息\n"
                "• 限制成员\n"
                "• 邀请用户"
            )
            return
    except TelegramError as e:
        await update.message.reply_text(f"❌ 检查权限失败：{e}")
        return
    
    if user_id not in admin_groups:
        admin_groups[user_id] = []
    
    already_bound = False
    for group_info in admin_groups[user_id]:
        if group_info['chat_id'] == chat_id:
            already_bound = True
            break
    
    if not already_bound:
        admin_groups[user_id].append({
            'chat_id': chat_id,
            'title': chat.title
        })
        save_config()
    
    bot_username = (await context.bot.get_me()).username
    private_link = f"https://t.me/{bot_username}?start=config_{chat_id}"
    
    await update.message.reply_text(
        f"✅ 群组绑定成功！\n\n"
        f"📱 请点击下方链接，私聊我进行配置：\n"
        f"{private_link}\n\n"
        f"或者直接私聊我，然后选择这个群组进行配置。"
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理回调查询 - 使用普通文本，避免 entity 错误"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "menu_main":
        keyboard = create_main_menu(user_id)
        await query.edit_message_text(
            "🏠 主菜单\n\n选择功能：",
            reply_markup=keyboard
        )
    
    elif data == "menu_groups":
        user_groups = admin_groups.get(user_id, [])
        if not user_groups:
            await query.answer("❌ 你还没有绑定任何群组！", show_alert=True)
            return
        
        keyboard = create_groups_list(user_id)
        await query.edit_message_text(
            "📋 我的群组列表\n\n点击群组进行配置：",
            reply_markup=keyboard
        )
    
    elif data == "menu_help":
        keyboard = [[
            InlineKeyboardButton(
                text="返回",
                callback_data="menu_main",
                api_kwargs={
                    "icon_custom_emoji_id": EMOJI_BACK,
                    "style": "primary"
                }
            )
        ]]
        await query.edit_message_text(
            "📖 帮助说明\n\n"
            "工作流程：\n"
            "1. 新成员加入 → 立即禁言\n"
            "2. 显示提示消息（120秒后自动删除）\n"
            "3. 用户订阅频道 → 点击验证\n"
            "4. 验证通过 → 自动解除禁言\n\n"
            "配置步骤：\n"
            "1. 将机器人添加到群组\n"
            "2. 给机器人管理员权限\n"
            "3. 在群组发送 /bind\n"
            "4. 私聊机器人进行配置\n\n"
            "需要的权限：\n"
            "• 删除消息\n"
            "• 限制成员\n"
            "• 邀请用户",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("group_"):
        chat_id = int(data.split('_')[1])
        
        user_groups = admin_groups.get(user_id, [])
        has_permission = any(g['chat_id'] == chat_id for g in user_groups)
        
        if not has_permission:
            await query.answer("❌ 你没有权限管理此群组！", show_alert=True)
            return
        
        group_title = "未知群组"
        for g in user_groups:
            if g['chat_id'] == chat_id:
                group_title = g['title']
                break
        
        settings = group_settings.get(chat_id, {})
        enabled = settings.get('enabled', False)
        channel = settings.get('channel', '未设置')
        
        status_text = "已启用" if enabled else "已禁用"
        status_emoji = "🟢" if enabled else "🔴"
        
        keyboard = create_group_panel(chat_id)
        
        await query.edit_message_text(
            f"⚙️ 群组配置\n\n"
            f"📱 群组：{group_title}\n"
            f"📢 频道：{channel}\n"
            f"{status_emoji} 状态：{status_text}\n\n"
            f"点击下方按钮进行配置：",
            reply_markup=keyboard
        )
    
    elif data.startswith("config_channel_"):
        chat_id = int(data.split('_')[2])
        await query.edit_message_text(
            "📢 设置频道\n\n"
            "请回复此消息，发送频道用户名或转发频道消息：\n\n"
            "• 格式：@频道用户名\n"
            "• 或者：转发频道任意消息\n\n"
            "💡 提示：\n"
            "1. 频道必须是公开频道\n"
            "2. 我必须在频道中是管理员"
        )
        context.user_data['waiting_channel'] = chat_id
    
    elif data.startswith("config_enable_"):
        chat_id = int(data.split('_')[2])
        
        if chat_id not in group_settings or 'channel' not in group_settings[chat_id]:
            await query.answer("❌ 请先设置频道！", show_alert=True)
            return
        
        group_settings[chat_id]['enabled'] = True
        save_config()
        
        settings = group_settings[chat_id]
        channel = settings['channel']
        
        keyboard = create_group_panel(chat_id)
        
        await query.edit_message_text(
            f"✅ 强制订阅已启用！\n\n"
            f"📢 频道：{channel}\n"
            f"🟢 状态：已启用\n\n"
            f"新成员加入时将立即禁言，订阅频道后可解除。",
            reply_markup=keyboard
        )
    
    elif data.startswith("config_disable_"):
        chat_id = int(data.split('_')[2])
        
        if chat_id in group_settings:
            group_settings[chat_id]['enabled'] = False
            save_config()
        
        keyboard = create_group_panel(chat_id)
        
        await query.edit_message_text(
            f"🔴 强制订阅已禁用！\n\n新成员可以自由发言。",
            reply_markup=keyboard
        )
    
    elif data.startswith("config_status_"):
        chat_id = int(data.split('_')[2])
        
        settings = group_settings.get(chat_id, {})
        enabled = settings.get('enabled', False)
        channel = settings.get('channel', '未设置')
        
        status_text = "已启用" if enabled else "已禁用"
        status_emoji = "🟢" if enabled else "🔴"
        
        keyboard = create_group_panel(chat_id)
        
        await query.edit_message_text(
            f"📊 当前状态：\n\n"
            f"📢 频道：{channel}\n"
            f"{status_emoji} 状态：{status_text}\n"
            f"⏱️ 提示消息自动删除时间：{WARNING_DELETE_SECONDS}秒",
            reply_markup=keyboard
        )


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理私聊消息"""
    if 'waiting_channel' not in context.user_data:
        return
    
    chat_id = context.user_data['waiting_channel']
    user_id = update.effective_user.id
    
    user_groups = admin_groups.get(user_id, [])
    has_permission = any(g['chat_id'] == chat_id for g in user_groups)
    
    if not has_permission:
        return
    
    channel = None
    
    if update.message.text and update.message.text.startswith('@'):
        channel = update.message.text.strip()
    elif update.message.forward_from_chat:
        channel_id = update.message.forward_from_chat.id
        channel_username = update.message.forward_from_chat.username
        if channel_username:
            channel = f"@{channel_username}"
        else:
            channel = str(channel_id)
    
    if not channel:
        await update.message.reply_text(
            "❌ 无效的输入！\n\n请发送：\n• @频道用户名\n• 或转发频道消息"
        )
        return
    
    try:
        chat = await context.bot.get_chat(channel)
        bot_member = await context.bot.get_chat_member(channel, context.bot.id)
        
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                f"❌ 我不是 {channel} 的管理员！\n\n"
                "请先将我添加到频道并设为管理员。"
            )
            return
        
        if chat_id not in group_settings:
            group_settings[chat_id] = {}
        
        group_settings[chat_id]['channel'] = channel
        group_settings[chat_id]['channel_id'] = chat.id
        group_settings[chat_id]['channel_title'] = chat.title
        save_config()
        
        del context.user_data['waiting_channel']
        
        keyboard = create_group_panel(chat_id)
        
        await update.message.reply_text(
            f"✅ 频道设置成功！\n\n"
            f"📢 频道：{channel}\n"
            f"📝 名称：{chat.title}\n\n"
            f"现在可以启用强制订阅了。",
            reply_markup=keyboard
        )
        
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ 无法访问频道！\n\n"
            f"错误：{str(e)}\n\n"
            "请确保：\n"
            "1. 频道用户名正确\n"
            "2. 频道是公开的\n"
            "3. 我已被添加到频道并设为管理员"
        )


async def check_subscription(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """检查用户是否已订阅频道"""
    if chat_id not in group_settings:
        return True
    
    settings = group_settings[chat_id]
    if not settings.get('enabled', False):
        return True
    
    channel = settings.get('channel')
    if not channel:
        return True
    
    try:
        member = await context.bot.get_chat_member(channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramError:
        return False


async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理新成员加入 - 无条件禁言，必须验证"""
    chat_id = update.effective_chat.id
    
    if chat_id not in group_settings or not group_settings[chat_id].get('enabled', False):
        return
    
    channel = group_settings[chat_id]['channel']
    channel_url = f"https://t.me/{channel[1:]}" if channel.startswith('@') else channel
    
    for new_member in update.message.new_chat_members:
        if new_member.is_bot:
            continue
        
        user_id = new_member.id
        
        # ✅ 无条件禁言所有新成员（不检查订阅状态）
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_media_messages=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False
                )
            )
            logger.info(f"✅ 已禁言新成员 {user_id}")
        except TelegramError as e:
            logger.error(f"❌ 禁言失败：{e}")
            continue  # 如果禁言失败，跳过这个用户
        
        # 发送提示消息（带动态 Emoji）
        text = f"👋 欢迎 {new_member.mention_html()}！\n\n⚠️ 在发言之前，请先订阅我们的频道：\n📢 {channel}\n\n👇 订阅后点击下方'我已关注'按钮验证："
        
        entities = [
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=0,
                length=2,
                custom_emoji_id=EMOJI_WAVE
            ),
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=utf16_len(f"👋 欢迎 {new_member.mention_html()}！\n\n"),
                length=2,
                custom_emoji_id=EMOJI_WARNING
            ),
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=utf16_len(f"👋 欢迎 {new_member.mention_html()}！\n\n⚠️ 在发言之前，请先订阅我们的频道：\n"),
                length=2,
                custom_emoji_id=EMOJI_MEGAPHONE
            ),
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=utf16_len(f"👋 欢迎 {new_member.mention_html()}！\n\n⚠️ 在发言之前，请先订阅我们的频道：\n📢 {channel}\n\n"),
                length=2,
                custom_emoji_id=EMOJI_POINT_DOWN
            ),
        ]
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="订阅频道",
                    url=channel_url,
                    api_kwargs={
                        "icon_custom_emoji_id": EMOJI_SUBSCRIBE,
                        "style": "primary"
                    }
                )
            ],
            [
                InlineKeyboardButton(
                    text="我已关注",
                    callback_data=f"verify_{user_id}",
                    api_kwargs={
                        "icon_custom_emoji_id": EMOJI_VERIFY,
                        "style": "success"
                    }
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            welcome_msg = await update.message.reply_text(
                text=text,
                entities=entities,
                reply_markup=reply_markup,
                parse_mode=None  # 不使用 parse_mode，直接用 entities
            )
            logger.info(f"✅ 已发送欢迎消息给 {user_id}，将在 {WARNING_DELETE_SECONDS} 秒后删除")
            
            # 120秒后自动删除
            context.job_queue.run_once(
                lambda ctx: welcome_msg.delete(),
                when=WARNING_DELETE_SECONDS,
                name=f"delete_welcome_{welcome_msg.message_id}"
            )
        except TelegramError as e:
            logger.error(f"❌ 发送欢迎消息失败：{e}")


async def verify_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """验证订阅状态并解除禁言"""
    query = update.callback_query
    
    if not query.data.startswith('verify_'):
        return
    
    await query.answer()
    
    user_id = int(query.data.split('_')[1])
    chat_id = query.message.chat_id
    
    if query.from_user.id != user_id:
        await query.answer("❌ 这不是你的验证按钮！", show_alert=True)
        return
    
    is_subscribed = await check_subscription(user_id, chat_id, context)
    
    if is_subscribed:
        # 解除禁言
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            
            await query.edit_message_text(
                f"✅ 验证成功！\n\n"
                f"欢迎 {query.from_user.mention_html()} 加入群组！\n\n"
                f"你现在可以自由发言了。",
                parse_mode='HTML'
            )
            
            logger.info(f"用户 {user_id} 验证成功，已解除禁言")
            
            # 5秒后删除验证成功消息
            context.job_queue.run_once(
                lambda ctx: query.message.delete(),
                when=5,
                name=f"delete_verified_{query.message.message_id}"
            )
            
        except TelegramError as e:
            logger.error(f"解除限制失败：{e}")
            await query.answer("❌ 验证失败，请联系管理员", show_alert=True)
    else:
        channel = group_settings[chat_id]['channel']
        await query.answer(
            f"❌ 你还没有订阅 {channel}！\n请先订阅后再点击验证。",
            show_alert=True
        )


def main():
    """启动机器人"""
    if not BOT_TOKEN:
        print("❌ 错误：未找到 BOT_TOKEN！")
        print("请在 .env 文件中配置 BOT_TOKEN")
        return
    
    load_config()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bind", bind_group))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(CallbackQueryHandler(verify_subscription, pattern=r"^verify_\d+$"))
    
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_member
    ))
    
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_private_message
    ))
    
    print("🤖 强制订阅机器人 V7 启动成功！")
    print("✨ 新成员加入立即禁言模式")
    print("   ✅ 新成员加入 → 立即禁言")
    print("   ✅ 必须点击验证按钮")
    print("   ✅ 验证通过 → 解除禁言")
    print("   ✅ 提示消息120秒后自动删除")
    print("📝 按 Ctrl+C 停止机器人")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
