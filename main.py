# bot.py - PRODUCTION READY (No Images)
import json
import os
import time
import random
import string
import datetime
from typing import Dict, List, Optional, Tuple
import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import StateFilter
import traceback
import threading

# ==============================
# CONFIGURATION
# ==============================
BOT_TOKEN = "8560550222:AAHH2-cplRmyCWTaHzaGXbvk8igjSM6oe_o"
ADMIN_IDS = [1882237415]  # Replace with your admin ID
FORCE_JOIN_CHANNELS = [
    {"id": "-1001865679813", "name": "Channel 1", "link": "https://t.me/+jnGZLo7gG5kwYWE1"},
    {"id": "-1002175918537", "name": "Channel 2", "link": "https://t.me/+GtcL_DI5nmI2MzM1"},
    {"id": "-1003065107812", "name": "Channel 3", "link": "https://t.me/+LBoAUt_EfCc4NDQ1"}
]
LOGS_CHANNEL = "@TG07PROOFS"

# Initialize bot with state storage
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
bot.add_custom_filter(StateFilter(bot))

# Define states for withdrawal process
class WithdrawStates(StatesGroup):
    amount = State()
    upi_id = State()
    qr_code = State()

# Store temporary withdrawal data
withdrawal_temp_data = {}

# ==============================
# DATA HANDLING UTILITIES - BULLETPROOF
# ==============================
class DataManager:
    @staticmethod
    def load_json(file_path: str, default: dict = None) -> dict:
        """Safely load JSON data with error handling"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data is None:
                        return default if default is not None else {}
                    return data
        except json.JSONDecodeError:
            # Backup corrupted file
            if os.path.exists(file_path):
                backup_path = f"{file_path}.backup_{int(time.time())}"
                os.rename(file_path, backup_path)
                print(f"JSON corrupted: {file_path}, backed up to {backup_path}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
        return default if default is not None else {}

    @staticmethod
    def save_json(file_path: str, data: dict):
        """Safely save JSON data with atomic write"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # Write to temp file first
            temp_file = f"{file_path}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Atomic rename
            if os.path.exists(file_path):
                os.replace(temp_file, file_path)
            else:
                os.rename(temp_file, file_path)
        except Exception as e:
            print(f"Error saving {file_path}: {e}")

    @staticmethod
    def get_users() -> dict:
        users = DataManager.load_json('data/users.json', {})
        # Fix any malformed data
        users = {k: v for k, v in users.items() if isinstance(v, dict)}
        return users

    @staticmethod
    def save_users(users: dict):
        DataManager.save_json('data/users.json', users)

    @staticmethod
    def get_referrals() -> dict:
        return DataManager.load_json('data/referrals.json', {})

    @staticmethod
    def save_referrals(referrals: dict):
        DataManager.save_json('data/referrals.json', referrals)

    @staticmethod
    def get_withdrawals() -> dict:
        return DataManager.load_json('data/withdrawals.json', {})

    @staticmethod
    def save_withdrawals(withdrawals: dict):
        DataManager.save_json('data/withdrawals.json', withdrawals)

    @staticmethod
    def get_redeem_codes() -> dict:
        return DataManager.load_json('data/redeem_codes.json', {})

    @staticmethod
    def save_redeem_codes(codes: dict):
        DataManager.save_json('data/redeem_codes.json', codes)

    @staticmethod
    def get_settings() -> dict:
        default_settings = {
            "referral_amount": 2,
            "bonus_amount": 0.10,
            "min_withdraw": 20,
            "admin_ids": ADMIN_IDS,
            "force_join_channels": FORCE_JOIN_CHANNELS,
            "logs_channel": LOGS_CHANNEL,
            "support_link": "https://t.me/TradeGenius07_HelpCenter_bot"
        }
        settings = DataManager.load_json('data/settings.json', default_settings)
        # Ensure all required keys exist
        for key, value in default_settings.items():
            if key not in settings:
                settings[key] = value
        return settings

    @staticmethod
    def save_settings(settings: dict):
        DataManager.save_json('data/settings.json', settings)

    @staticmethod
    def add_log(log_type: str, user_id: int, details: str, admin_id: int = None):
        """Add log entry"""
        logs = DataManager.load_json('data/logs.json', {"logs": []})
        if "logs" not in logs:
            logs["logs"] = []
        logs["logs"].append({
            "type": log_type,
            "user_id": user_id,
            "details": details,
            "timestamp": datetime.datetime.now().isoformat(),
            "admin_id": admin_id
        })
        # Keep only last 1000 logs
        if len(logs["logs"]) > 1000:
            logs["logs"] = logs["logs"][-1000:]
        DataManager.save_json('data/logs.json', logs)

# ==============================
# USER MANAGEMENT - FIXED
# ==============================
class UserManager:
    @staticmethod
    def generate_referral_code(user_id: int) -> str:
        """Generate unique referral code"""
        return f"REF{user_id}{random.randint(1000, 9999)}"

    @staticmethod
    def get_user(user_id: int) -> Optional[dict]:
        users = DataManager.get_users()
        user_key = str(user_id)
        
        if user_key not in users:
            return None
        
        user = users[user_key]
        
        # ENSURE ALL REQUIRED FIELDS EXIST
        required_fields = {
            "username": "",
            "first_name": "User",
            "balance": 0.0,
            "referrer_id": None,
            "referral_code": UserManager.generate_referral_code(user_id),
            "total_referred": 0,
            "total_withdrawn": 0.0,
            "total_earned": 0.0,
            "joined_date": datetime.datetime.now().isoformat(),
            "last_bonus_claim": None,
            "has_joined_channels": False,
            "is_active": True,
            "referral_completed": False  # ✅ ADDED: NEW FIELD FOR REFERRAL LOCK
        }
        
        # Add missing fields
        updated = False
        for field, default_value in required_fields.items():
            if field not in user:
                user[field] = default_value
                updated = True
        
        if updated:
            users[user_key] = user
            DataManager.save_users(users)
        
        return user

    @staticmethod
    def create_user(user_id: int, username: str, first_name: str, referrer_id: int = None) -> dict:
        """Create new user with ALL required fields"""
        users = DataManager.get_users()
        
        if str(user_id) in users:
            return users[str(user_id)]
        
        # Generate referral code
        referral_code = UserManager.generate_referral_code(user_id)
        
        # Create user with ALL required fields
        user_data = {
            "username": username or "",
            "first_name": first_name or "User",
            "balance": 0.0,
            "referrer_id": referrer_id,
            "referral_code": referral_code,
            "total_referred": 0,
            "total_withdrawn": 0.0,
            "total_earned": 0.0,
            "joined_date": datetime.datetime.now().isoformat(),
            "last_bonus_claim": None,
            "has_joined_channels": False,
            "is_active": True,
            "referral_completed": False  # ✅ ADDED: NEW FIELD FOR REFERRAL LOCK
        }
        
        users[str(user_id)] = user_data
        DataManager.save_users(users)
        
        # Handle referral if exists - FIXED TO PREVENT DUPLICATES
        if referrer_id and referrer_id != user_id:
            referrals = DataManager.get_referrals()
            referrer_key = str(referrer_id)
            
            # ✅ FIXED: Initialize properly
            referrals.setdefault(referrer_key, {
                "referred_users": [],
                "pending_referrals": [],
                "total_earnings": 0.0
            })
            
            # ✅ FIXED: Check if already in pending or completed
            if str(user_id) not in referrals[referrer_key]["pending_referrals"] \
               and str(user_id) not in referrals[referrer_key]["referred_users"]:
                referrals[referrer_key]["pending_referrals"].append(str(user_id))
            
            DataManager.save_referrals(referrals)
            
            # Notify referrer about pending referral
            try:
                referrer = UserManager.get_user(referrer_id)
                if referrer:
                    bot.send_message(
                        referrer_id,
                        f"🎉 You invited {first_name}!\n"
                        f"💰 You will earn ₹2 once they join all channels and verify!"
                    )
            except:
                pass
        
        # Notify admin about new user
        try:
            settings = DataManager.get_settings()
            admin_ids = settings.get("admin_ids", ADMIN_IDS)
            total_users = len(users)
            for admin_id in admin_ids:
                bot.send_message(
                    admin_id,
                    f"🆕 New User Started the Bot!\n\n"
                    f"👤 User ID: {user_id}\n"
                    f"👤 Username: @{username if username else 'N/A'}\n"
                    f"📛 Name: {first_name}\n"
                    f"📊 Total Users: {total_users}"
                )
        except:
            pass
        
        return user_data

    @staticmethod
    def update_balance(user_id: int, amount: float, action: str = "add") -> bool:
        """Update user balance with validation"""
        users = DataManager.get_users()
        user_key = str(user_id)
        
        if user_key not in users:
            return False
        
        if action == "add":
            users[user_key]["balance"] = users[user_key].get("balance", 0.0) + amount
            users[user_key]["total_earned"] = users[user_key].get("total_earned", 0.0) + amount
        elif action == "subtract":
            current_balance = users[user_key].get("balance", 0.0)
            if current_balance < amount:
                return False
            users[user_key]["balance"] = current_balance - amount
        else:
            return False
        
        DataManager.save_users(users)
        return True

    @staticmethod
    def complete_referral(user_id: int):
        """Complete referral process after user joins channels - FIXED VERSION"""
        users = DataManager.get_users()
        referrals = DataManager.get_referrals()
        settings = DataManager.get_settings()

        user = users.get(str(user_id))
        if not user:
            return

        # ✅ FIXED: Stop if already rewarded
        if user.get("referral_completed", False):
            return

        referrer_id = user.get("referrer_id")
        if not referrer_id:
            return

        referrer_key = str(referrer_id)

        if referrer_key not in referrals:
            # Initialize if missing
            referrals[referrer_key] = {
                "referred_users": [],
                "pending_referrals": [],
                "total_earnings": 0.0
            }

        # Remove from pending
        if str(user_id) in referrals[referrer_key].get("pending_referrals", []):
            referrals[referrer_key]["pending_referrals"].remove(str(user_id))

        # ✅ FIXED: Check if already completed
        if str(user_id) in referrals[referrer_key].get("referred_users", []):
            return

        # Add to completed
        referrals[referrer_key]["referred_users"].append(str(user_id))

        # 💰 CREDIT MONEY
        referral_amount = settings.get("referral_amount", 2)
        
        # Update referrer's balance and earnings directly in the users dict
        if referrer_key in users:
            users[referrer_key]["balance"] = users[referrer_key].get("balance", 0.0) + referral_amount
            users[referrer_key]["total_earned"] = users[referrer_key].get("total_earned", 0.0) + referral_amount
            users[referrer_key]["total_referred"] = users[referrer_key].get("total_referred", 0) + 1

        # Update stats in referrals dict
        referrals[referrer_key]["total_earnings"] = referrals[referrer_key].get("total_earnings", 0.0) + referral_amount

        # ✅ FIXED: LOCK REFERRAL
        user["referral_completed"] = True
        users[str(user_id)] = user

        # SAVE ALL DATA
        DataManager.save_users(users)
        DataManager.save_referrals(referrals)

        # Notify referrer
        try:
            bot.send_message(
                int(referrer_id),
                f"🎉 <b>Referral Successful!</b>\n\n"
                f"👤 {user.get('first_name','User')} joined all channels\n"
                f"💰 <b>₹{referral_amount}</b> credited to your balance instantly!",
                parse_mode='HTML'
            )
        except:
            pass

        # Log referral completion
        DataManager.add_log(
            "referral",
            int(referrer_id),
            f"Earned ₹{referral_amount} from user {user_id}"
        )

# ==============================
# CHANNEL VERIFICATION SYSTEM - FIXED
# ==============================
class ChannelVerifier:
    @staticmethod
    def check_membership(user_id: int) -> Tuple[bool, List[Dict]]:
        """Check if user is member of all required channels - FIXED FOR PRIVATE CHANNELS"""
        settings = DataManager.get_settings()
        channels = settings.get("force_join_channels", FORCE_JOIN_CHANNELS)
        not_joined = []
        
        for channel in channels:
            try:
                chat_member = bot.get_chat_member(channel["id"], user_id)
                if chat_member.status not in ['member', 'administrator', 'creator']:
                    not_joined.append(channel)
            except Exception as e:
                # If bot can't check (private channel or no permission), ask to join
                not_joined.append(channel)
        
        return len(not_joined) == 0, not_joined

    @staticmethod
    def show_force_join_message(chat_id: int, not_joined: List[Dict]):
        """Show ALL channels user needs to join (public + private)"""
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for channel in not_joined:
            markup.add(types.InlineKeyboardButton(
                f"👉 Join {channel['name']}",
                url=channel['link']
            ))
        
        markup.add(types.InlineKeyboardButton(
            "✅ I Have Joined All Channels",
            callback_data="verify_channels"
        ))
        
        channel_list = "\n".join([f"• {channel['name']}" for channel in not_joined])
        
        bot.send_message(
            chat_id,
            f"🔒 <b>Channel Membership Required</b>\n\n"
            f"To use this bot, you must join all our channels:\n\n"
            f"{channel_list}\n\n"
            f"<i>Instructions:</i>\n"
            f"1️⃣ Join all channels above\n"
            f"2️⃣ Click the verification button\n"
            f"3️⃣ Start earning!",
            reply_markup=markup
        )

# ==============================
# KEYBOARDS
# ==============================
class KeyboardManager:
    @staticmethod
    def get_main_keyboard() -> types.ReplyKeyboardMarkup:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = [
            "👤 Profile",
            "🎁 Bonus",
            "📊 Statistics",
            "👥 Refer & Earn",
            "💳 Withdraw",
            "🎟 Redeem",
            "🆘 Support"
        ]
        markup.add(*buttons)
        return markup

    @staticmethod
    def get_admin_keyboard() -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            types.InlineKeyboardButton("💰 Set Referral Amount", callback_data="admin_set_referral"),
            types.InlineKeyboardButton("🎁 Set Bonus Amount", callback_data="admin_set_bonus"),
            types.InlineKeyboardButton("💸 Set Min Withdraw", callback_data="admin_set_min_withdraw"),
            types.InlineKeyboardButton("➕ Add Balance", callback_data="admin_add_balance"),
            types.InlineKeyboardButton("➖ Remove Balance", callback_data="admin_remove_balance"),
            types.InlineKeyboardButton("🎟 Create Redeem Code", callback_data="admin_create_redeem"),
            types.InlineKeyboardButton("✏️ Edit Redeem Code", callback_data="admin_edit_redeem"),
            types.InlineKeyboardButton("📊 View Statistics", callback_data="admin_view_stats"),
            types.InlineKeyboardButton("🔗 Add Support Link", callback_data="admin_add_support_link"),
            types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
        ]
        markup.add(*buttons)
        return markup

    @staticmethod
    def get_referral_keyboard() -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 My Stats", callback_data="referral_stats"),
            types.InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
        )
        return markup

    @staticmethod
    def get_withdraw_method_keyboard() -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📱 UPI ID", callback_data="withdraw_upi"),
            types.InlineKeyboardButton("📷 QR Code", callback_data="withdraw_qr")
        )
        return markup

    @staticmethod
    def get_confirmation_keyboard() -> types.InlineKeyboardMarkup:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Yes", callback_data="confirm_yes"),
            types.InlineKeyboardButton("❌ No", callback_data="confirm_no")
        )
        return markup

# ==============================
# MIDDLEWARE FOR CHANNEL CHECKING
# ==============================
def check_channels_decorator(func):
    """Decorator to check channel membership before processing commands"""
    def wrapper(message):
        user_id = message.from_user.id
        
        # Skip check for start command (handled separately)
        if message.text and message.text.startswith('/start'):
            func(message)
            return
        
        # Skip check for admin panel
        if message.text and message.text.startswith('/admin'):
            func(message)
            return
        
        # Get user
        user = UserManager.get_user(user_id)
        if not user:
            bot.send_message(message.chat.id, "⚠️ Please start the bot first: /start")
            return
        
        # Check channels
        is_member, not_joined = ChannelVerifier.check_membership(user_id)
        
        if not is_member:
            # Update user status
            user["has_joined_channels"] = False
            users = DataManager.get_users()
            users[str(user_id)] = user
            DataManager.save_users(users)
            
            # Show channel join message
            ChannelVerifier.show_force_join_message(message.chat.id, not_joined)
            return
        
        # Update channel status if needed
        if not user.get("has_joined_channels", False):
            user["has_joined_channels"] = True
            users = DataManager.get_users()
            users[str(user_id)] = user
            DataManager.save_users(users)
            
            # ✅ FIXED: Complete referral if applicable (now safe from duplicates)
            UserManager.complete_referral(user_id)
        
        # Execute the original function
        func(message)
    
    return wrapper

# ==============================
# START COMMAND - FIXED
# ==============================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "User"
    
    # Check if referral link was used
    referrer_id = None
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
            # Prevent self-referral
            if referrer_id == user_id:
                referrer_id = None
        except:
            pass
    
    users = DataManager.get_users()
    
    if str(user_id) in users:
        # Existing user
        user = users[str(user_id)]
        
        # Check channel membership
        is_member, not_joined = ChannelVerifier.check_membership(user_id)
        
        if not is_member:
            user["has_joined_channels"] = False
            DataManager.save_users(users)
            ChannelVerifier.show_force_join_message(message.chat.id, not_joined)
            return
        
        # Update channel status
        if not user.get("has_joined_channels", False):
            user["has_joined_channels"] = True
            DataManager.save_users(users)
            
            # ✅ FIXED: Complete referral if applicable (now safe from duplicates)
            UserManager.complete_referral(user_id)
        
        # Show main menu
        bot.send_message(
            message.chat.id,
            "🎉 Welcome back!\n"
            "Choose an option from the menu below:",
            reply_markup=KeyboardManager.get_main_keyboard()
        )
    else:
        # New user
        # ✅ FIXED: Create user FIRST to track referrer immediately
        UserManager.create_user(user_id, username, first_name, referrer_id)
        
        # Check channel membership
        is_member, not_joined = ChannelVerifier.check_membership(user_id)
        
        if not is_member:
            ChannelVerifier.show_force_join_message(message.chat.id, not_joined)
            return
        
        # If they already joined all channels
        users = DataManager.get_users()
        if str(user_id) in users:
            users[str(user_id)]["has_joined_channels"] = True
            DataManager.save_users(users)
        
        # ✅ FIXED: Complete referral if applicable
        UserManager.complete_referral(user_id)
        
        # Welcome message with main menu
        bot.send_message(
            message.chat.id,
            "🎉 <b>Welcome to Refer & Earn Bot!</b>\n\n"
            "💰 <b>Earn Money by Referring Friends</b>\n\n"
            "✅ <b>How it works:</b>\n"
            "1. Share your referral link\n"
            "2. Friends join via your link\n"
            "3. They join required channels\n"
            "4. You earn ₹2 per referral!\n\n"
            "Use the menu below to get started!",
            reply_markup=KeyboardManager.get_main_keyboard()
        )

@bot.message_handler(func=lambda message: message.text == "👤 Profile")
@check_channels_decorator
def handle_profile(message):
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ User not found!")
        return
    
    # Get only needed fields
    first_name = user.get('first_name', 'User')
    balance = user.get('balance', 0.0)
    
    # ESCAPE HTML SPECIAL CHARACTERS IN FIRST NAME
    def escape_html(text):
        if not text:
            return ""
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    first_name_safe = escape_html(first_name)
    
    # Simple profile text
    profile_text = (
        f"👤 <b>PROFILE</b>\n\n"
        f"📛 First Name: {first_name_safe}\n"
        f"🆔 User ID: <code>{user_id}</code>\n"
        f"💰 Balance: ₹{balance:.2f}\n\n"
        f"<i>Invite and earn By Our Bot</i>"
    )
    
    bot.send_message(message.chat.id, profile_text, parse_mode='HTML')

# ==============================
# BONUS COMMAND - FIXED
# ==============================
@bot.message_handler(func=lambda message: message.text == "🎁 Bonus")
@check_channels_decorator
def handle_bonus(message):
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ User not found!")
        return
    
    settings = DataManager.get_settings()
    bonus_amount = settings.get("bonus_amount", 10)
    
    # Check cooldown
    last_claim = user.get("last_bonus_claim")
    if last_claim:
        try:
            last_claim_dt = datetime.datetime.fromisoformat(last_claim)
            hours_passed = (datetime.datetime.now() - last_claim_dt).total_seconds() / 3600
            
            if hours_passed < 24:
                hours_left = 24 - hours_passed
                bot.send_message(
                    message.chat.id,
                    f"⏰ Bonus already claimed!\n"
                    f"Next bonus available in {hours_left:.1f} hours."
                )
                return
        except:
            pass  # If date parsing fails, allow bonus
    
    # Claim bonus
    UserManager.update_balance(user_id, bonus_amount, "add")
    
    # Update last claim time
    users = DataManager.get_users()
    users[str(user_id)]["last_bonus_claim"] = datetime.datetime.now().isoformat()
    DataManager.save_users(users)
    
    bot.send_message(
        message.chat.id,
        f"🎉 Bonus claimed successfully!\n"
        f"💰 ₹{bonus_amount} added to your balance."
    )
    
    DataManager.add_log("bonus", user_id, f"Claimed daily bonus of ₹{bonus_amount}")

# ==============================
# REFER & EARN COMMAND - FIXED
# ==============================
@bot.message_handler(func=lambda message: message.text == "👥 Refer & Earn")
@check_channels_decorator
def handle_refer(message):
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ User not found!")
        return
    
    settings = DataManager.get_settings()
    referral_amount = settings.get("referral_amount", 2)
    
    # Generate referral link
    bot_username = bot.get_me().username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    referrals = DataManager.get_referrals()
    user_referrals = referrals.get(str(user_id), {})
    
    pending = len(user_referrals.get("pending_referrals", []))
    completed = len(user_referrals.get("referred_users", []))
    total_earnings = user_referrals.get("total_earnings", 0.0)
    
    referral_text = (
        f"🎯 <b>REFER & EARN</b>\n\n"
        f"💰 <b>Earn ₹{referral_amount} per referral!</b>\n\n"
        f"📊 <b>Your Stats:</b>\n"
        f"✅ Completed Referrals: {completed}\n"
        f"⏳ Pending Verification: {pending}\n"
        f"💰 Total Earned: ₹{total_earnings:.2f}\n\n"
        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"📝 <b>How to earn:</b>\n"
        f"1. Share your link with friends\n"
        f"2. They must join all channels\n"
        f"3. You get ₹{referral_amount} instantly!"
    )
    
    bot.send_message(
        message.chat.id,
        referral_text,
        reply_markup=KeyboardManager.get_referral_keyboard()
    )

# ==============================
# WITHDRAW COMMAND - FIXED
# ==============================
@bot.message_handler(func=lambda message: message.text == "💳 Withdraw")
@check_channels_decorator
def handle_withdraw(message):
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ User not found!")
        return
    
    settings = DataManager.get_settings()
    min_withdraw = settings.get("min_withdraw", 100)
    
    balance = user.get("balance", 0.0)
    if balance < min_withdraw:
        bot.send_message(
            message.chat.id,
            f"❌ Minimum withdraw amount is ₹{min_withdraw}\n"
            f"💰 Your balance: ₹{balance:.2f}"
        )
        return
    
    # Store user ID for withdrawal process
    withdrawal_temp_data[user_id] = {"step": "amount"}
    
    # Ask for withdraw amount
    bot.send_message(
        message.chat.id,
        f"💰 <b>Withdrawal Request</b>\n\n"
        f"Minimum: ₹{min_withdraw}\n"
        f"Your Balance: ₹{balance:.2f}\n\n"
        f"Enter amount to withdraw (INR):"
    )
    bot.set_state(user_id, WithdrawStates.amount, message.chat.id)

# Handle amount input
@bot.message_handler(state=WithdrawStates.amount)
def process_withdraw_amount(message):
    user_id = message.from_user.id
    
    try:
        amount = float(message.text)
        settings = DataManager.get_settings()
        min_withdraw = settings.get("min_withdraw", 100)
        
        if amount < min_withdraw:
            bot.send_message(
                message.chat.id,
                f"❌ Minimum withdraw amount is ₹{min_withdraw}"
            )
            return
        
        user = UserManager.get_user(user_id)
        if not user:
            bot.send_message(message.chat.id, "❌ User not found!")
            return
        
        balance = user.get("balance", 0.0)
        if amount > balance:
            bot.send_message(
                message.chat.id,
                f"❌ Insufficient balance!\n"
                f"💰 Your balance: ₹{balance:.2f}"
            )
            return
        
        # Store amount in temporary data
        withdrawal_temp_data[user_id] = {
            "step": "method",
            "amount": amount
        }
        
        bot.send_message(
            message.chat.id,
            f"✅ Amount valid: ₹{amount}\n\n"
            f"Choose payment method:",
            reply_markup=KeyboardManager.get_withdraw_method_keyboard()
        )
        
        bot.delete_state(user_id, message.chat.id)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a valid number!")

# ==============================
# WITHDRAW CALLBACKS - FIXED
# ==============================
@bot.callback_query_handler(func=lambda call: call.data in ['withdraw_upi', 'withdraw_qr'])
def handle_withdraw_method(call):
    user_id = call.from_user.id
    
    # Check if user has amount stored
    if user_id not in withdrawal_temp_data or withdrawal_temp_data[user_id].get("step") != "method":
        bot.answer_callback_query(call.id, "❌ Please start withdrawal process again!")
        return
    
    amount = withdrawal_temp_data[user_id].get("amount")
    
    if call.data == 'withdraw_upi':
        withdrawal_temp_data[user_id] = {
            "step": "upi",
            "amount": amount,
            "method": "upi"
        }
        bot.set_state(user_id, WithdrawStates.upi_id, call.message.chat.id)
        bot.send_message(
            call.message.chat.id,
            "📱 Enter your UPI ID (e.g., username@upi):"
        )
    elif call.data == 'withdraw_qr':
        withdrawal_temp_data[user_id] = {
            "step": "qr",
            "amount": amount,
            "method": "qr"
        }
        bot.set_state(user_id, WithdrawStates.qr_code, call.message.chat.id)
        bot.send_message(
            call.message.chat.id,
            "📷 Please send your QR Code image:"
        )
    
    bot.answer_callback_query(call.id)

# HTML escaping helper function
def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))

# Handle UPI ID input
@bot.message_handler(state=WithdrawStates.upi_id, content_types=['text'])
def process_upi_id(message):
    user_id = message.from_user.id
    upi_id = message.text.strip()
    
    # Validate UPI ID format
    if not '@' in upi_id:
        bot.send_message(message.chat.id, "❌ Invalid UPI ID format! Please enter a valid UPI ID (e.g., username@upi)")
        return
    
    # Get stored data
    if user_id not in withdrawal_temp_data:
        bot.send_message(message.chat.id, "❌ Session expired! Please start withdrawal again.")
        bot.delete_state(user_id, message.chat.id)
        return
    
    stored_data = withdrawal_temp_data[user_id]
    amount = stored_data.get("amount")
    
    # DEDUCT BALANCE IMMEDIATELY WHEN USER SUBMITS WITHDRAWAL REQUEST
    if not UserManager.update_balance(user_id, amount, "subtract"):
        bot.send_message(message.chat.id, "❌ Insufficient balance! Please try again.")
        bot.delete_state(user_id, message.chat.id)
        return
    
    # Create withdrawal entry
    withdrawals = DataManager.get_withdrawals()
    withdrawal_id = f"WD{int(time.time())}{random.randint(1000, 9999)}"
    
    withdrawals[withdrawal_id] = {
        "user_id": user_id,
        "amount": amount,
        "method": "upi",
        "upi_id": upi_id,
        "qr_image_path": None,
        "status": "pending",
        "balance_deducted": True,  # Track that balance was already deducted
        "request_time": datetime.datetime.now().isoformat(),
        "admin_action_time": None,
        "admin_id": None
    }
    DataManager.save_withdrawals(withdrawals)
    
    # Store withdrawal ID for confirmation
    withdrawal_temp_data[user_id]["withdrawal_id"] = withdrawal_id
    
    # Get updated balance
    user = UserManager.get_user(user_id)
    new_balance = user.get("balance", 0.0) if user else 0.0
    
    # Ask for confirmation with escaped HTML
    upi_id_safe = escape_html(upi_id)
    bot.send_message(
        message.chat.id,
        f"📋 <b>Withdrawal Summary</b>\n\n"
        f"💰 Amount: ₹{amount}\n"
        f"📱 Method: UPI\n"
        f"🔗 UPI ID: <code>{upi_id_safe}</code>\n"
        f"💳 New Balance: ₹{new_balance:.2f}\n\n"
        f"✅ <b>₹{amount} has been deducted from your balance.</b>\n"
        f"⏳ <i>Your request is pending admin approval.</i>\n\n"
        f"Confirm withdrawal request?",
        reply_markup=KeyboardManager.get_confirmation_keyboard(),
        parse_mode='HTML'
    )
    
    bot.delete_state(user_id, message.chat.id)

# Handle QR Code input
@bot.message_handler(state=WithdrawStates.qr_code, content_types=['photo'])
def process_qr_code(message):
    user_id = message.from_user.id
    
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Please send an image!")
        return
    
    # Get stored data
    if user_id not in withdrawal_temp_data:
        bot.send_message(message.chat.id, "❌ Session expired! Please start withdrawal again.")
        bot.delete_state(user_id, message.chat.id)
        return
    
    stored_data = withdrawal_temp_data[user_id]
    amount = stored_data.get("amount")
    
    # DEDUCT BALANCE IMMEDIATELY WHEN USER SUBMITS WITHDRAWAL REQUEST
    if not UserManager.update_balance(user_id, amount, "subtract"):
        bot.send_message(message.chat.id, "❌ Insufficient balance! Please try again.")
        bot.delete_state(user_id, message.chat.id)
        return
    
    # Save photo file ID (in production, you would download and save the image)
    photo_file_id = message.photo[-1].file_id
    
    # Create withdrawal entry
    withdrawals = DataManager.get_withdrawals()
    withdrawal_id = f"WD{int(time.time())}{random.randint(1000, 9999)}"
    
    withdrawals[withdrawal_id] = {
        "user_id": user_id,
        "amount": amount,
        "method": "qr",
        "upi_id": None,
        "qr_image_path": photo_file_id,  # Store file ID for now
        "status": "pending",
        "balance_deducted": True,  # Track that balance was already deducted
        "request_time": datetime.datetime.now().isoformat(),
        "admin_action_time": None,
        "admin_id": None
    }
    DataManager.save_withdrawals(withdrawals)
    
    # Store withdrawal ID for confirmation
    withdrawal_temp_data[user_id]["withdrawal_id"] = withdrawal_id
    
    # Get updated balance
    user = UserManager.get_user(user_id)
    new_balance = user.get("balance", 0.0) if user else 0.0
    
    # Ask for confirmation
    bot.send_message(
        message.chat.id,
        f"📋 <b>Withdrawal Summary</b>\n\n"
        f"💰 Amount: ₹{amount}\n"
        f"📷 Method: QR Code\n"
        f"💳 New Balance: ₹{new_balance:.2f}\n\n"
        f"✅ <b>₹{amount} has been deducted from your balance.</b>\n"
        f"⏳ <i>Your request is pending admin approval.</i>\n\n"
        f"Confirm withdrawal request?",
        reply_markup=KeyboardManager.get_confirmation_keyboard()
    )
    
    bot.delete_state(user_id, message.chat.id)

# ==============================
# CONFIRMATION CALLBACKS - FIXED
# ==============================
@bot.callback_query_handler(func=lambda call: call.data in ['confirm_yes', 'confirm_no'])
def handle_confirmation(call):
    user_id = call.from_user.id
    
    if user_id not in withdrawal_temp_data:
        bot.answer_callback_query(call.id, "❌ Session expired!")
        return
    
    stored_data = withdrawal_temp_data[user_id]
    withdrawal_id = stored_data.get("withdrawal_id")
    
    if not withdrawal_id:
        bot.answer_callback_query(call.id, "❌ Withdrawal not found!")
        return
    
    withdrawals = DataManager.get_withdrawals()
    if withdrawal_id not in withdrawals:
        bot.answer_callback_query(call.id, "❌ Withdrawal not found!")
        return
    
    if call.data == 'confirm_no':
        # Get withdrawal data before deleting
        withdrawal = withdrawals.get(withdrawal_id)
        if withdrawal and withdrawal.get("balance_deducted"):
            # REFUND BALANCE IF USER CANCELS
            amount = withdrawal.get("amount", 0)
            UserManager.update_balance(user_id, amount, "add")
        
        # Remove pending withdrawal
        if withdrawal_id in withdrawals:
            del withdrawals[withdrawal_id]
            DataManager.save_withdrawals(withdrawals)
        
        bot.edit_message_text(
            "❌ Withdrawal cancelled. Amount refunded to your balance.",
            call.message.chat.id,
            call.message.message_id
        )
        # Clear temp data
        if user_id in withdrawal_temp_data:
            del withdrawal_temp_data[user_id]
        return
    
    # Confirm withdrawal (send to admin)
    withdrawal = withdrawals[withdrawal_id]
    user = UserManager.get_user(user_id)
    
    if not user:
        bot.answer_callback_query(call.id, "❌ User not found!")
        return
    
    # Send to admin with proper HTML escaping
    settings = DataManager.get_settings()
    admin_ids = settings.get("admin_ids", ADMIN_IDS)
    
    # Escape user input for HTML
    first_name_safe = escape_html(user.get('first_name', 'User'))
    username_safe = escape_html(user.get('username', 'N/A'))
    
    for admin_id in admin_ids:
        try:
            if withdrawal["method"] == "upi":
                # Escape UPI ID for HTML
                upi_id_safe = escape_html(withdrawal['upi_id'] if withdrawal.get('upi_id') else 'N/A')
                
                admin_msg = (
                    f"🔄 <b>New Withdrawal Request</b>\n\n"
                    f"👤 User: {first_name_safe}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"👤 Username: @{username_safe}\n"
                    f"💰 Amount: ₹{withdrawal['amount']}\n"
                    f"📅 Time: {withdrawal['request_time']}\n"
                    f"📱 Method: UPI\n"
                    f"🔗 UPI ID: <code>{upi_id_safe}</code>\n"
                    f"💰 User Balance: ₹{user.get('balance', 0.0):.2f}"
                )
                
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{withdrawal_id}"),
                    types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{withdrawal_id}")
                )
                bot.send_message(admin_id, admin_msg, reply_markup=markup, parse_mode='HTML')
            
            elif withdrawal["method"] == "qr":
                # Get the QR image file ID from withdrawal data
                qr_image_file_id = withdrawal.get("qr_image_path")
                
                admin_msg = (
                    f"🔄 <b>New Withdrawal Request</b>\n\n"
                    f"👤 User: {first_name_safe}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"👤 Username: @{username_safe}\n"
                    f"💰 Amount: ₹{withdrawal['amount']}\n"
                    f"📅 Time: {withdrawal['request_time']}\n"
                    f"📱 Method: QR Code\n"
                    f"💰 User Balance: ₹{user.get('balance', 0.0):.2f}\n\n"
                    f"⬇️ <b>User's QR Code:</b>"
                )
                
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{withdrawal_id}"),
                    types.InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{withdrawal_id}")
                )
                
                # First send the text message with details
                bot.send_message(
                    admin_id,
                    admin_msg,
                    reply_markup=markup,
                    parse_mode='HTML'
                )
                
                # Then send the QR code image
                if qr_image_file_id:
                    try:
                        bot.send_photo(
                            admin_id,
                            qr_image_file_id,
                            caption=f"📷 QR Code for {first_name_safe} - ₹{withdrawal['amount']}",
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        print(f"Error sending QR image to admin: {e}")
                        bot.send_message(
                            admin_id,
                            "⚠️ Could not send QR code image. File ID may be invalid.",
                            parse_mode='HTML'
                        )
                else:
                    bot.send_message(
                        admin_id,
                        "⚠️ No QR code image received from user.",
                        parse_mode='HTML'
                    )
        
        except Exception as e:
            print(f"Error notifying admin {admin_id}: {e}")
    
    bot.edit_message_text(
        "✅ Withdrawal request sent to admin!\n"
        "⏳ Your request is pending approval.\n"
        "📞 You will be notified once processed.",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Clear temp data
    if user_id in withdrawal_temp_data:
        del withdrawal_temp_data[user_id]
    
    bot.answer_callback_query(call.id)

# ==============================
# REDEEM COMMAND - FIXED
# ==============================
@bot.message_handler(func=lambda message: message.text == "🎟 Redeem")
@check_channels_decorator
def handle_redeem(message):
    user_id = message.from_user.id
    
    msg = bot.send_message(
        message.chat.id,
        "🎫 Enter redeem code:"
    )
    bot.register_next_step_handler(msg, process_redeem_code)

def process_redeem_code(message):
    user_id = message.from_user.id
    code = message.text.strip().upper()
    
    redeem_codes = DataManager.get_redeem_codes()
    
    if code not in redeem_codes:
        bot.send_message(message.chat.id, "❌ Invalid redeem code!")
        return
    
    redeem_data = redeem_codes[code]
    
    # Check if code is active
    if not redeem_data.get("is_active", True):
        bot.send_message(message.chat.id, "❌ This code is no longer active!")
        return
    
    # Check max users
    max_users = redeem_data.get("max_users", 1)
    used_count = redeem_data.get("used_count", 0)
    if used_count >= max_users:
        bot.send_message(message.chat.id, "❌ This code has reached maximum usage!")
        return
    
    # Check if user already used this code
    used_by = redeem_data.get("used_by", [])
    if str(user_id) in used_by:
        bot.send_message(message.chat.id, "❌ You have already used this code!")
        return
    
    # Redeem code
    amount = redeem_data.get("amount", 0)
    UserManager.update_balance(user_id, amount, "add")
    
    # Update redeem code stats
    redeem_data["used_count"] = used_count + 1
    if "used_by" not in redeem_data:
        redeem_data["used_by"] = []
    redeem_data["used_by"].append(str(user_id))
    redeem_codes[code] = redeem_data
    DataManager.save_redeem_codes(redeem_codes)
    
    bot.send_message(
        message.chat.id,
        f"✅ Redeem successful!\n"
        f"💰 ₹{amount} added to your balance."
    )
    
    DataManager.add_log("redeem", user_id, f"Redeemed code {code} for ₹{amount}")

# ==============================
# STATISTICS COMMAND - FIXED
# ==============================
@bot.message_handler(func=lambda message: message.text == "📊 Statistics")
@check_channels_decorator
def handle_statistics(message):
    user_id = message.from_user.id
    user = UserManager.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, "❌ User not found!")
        return
    
    # SAFE joined_date access
    joined_date_str = user.get('joined_date')
    if joined_date_str:
        try:
            joined_date = datetime.datetime.fromisoformat(joined_date_str)
        except:
            joined_date = datetime.datetime.now()
    else:
        joined_date = datetime.datetime.now()
    
    days_joined = max(1, (datetime.datetime.now() - joined_date).days)
    
    stats_text = (
        f"📊 <b>YOUR STATISTICS</b>\n\n"
        f"👥 Total Referrals: {user.get('total_referred', 0)}\n"
        f"💰 Total Withdrawn: ₹{user.get('total_withdrawn', 0.0):.2f}\n"
        f"💵 Total Earned: ₹{user.get('total_earned', 0.0):.2f}\n"
        f"🏦 Current Balance: ₹{user.get('balance', 0.0):.2f}\n"
        f"📅 Days Active: {days_joined}\n"
        f"📈 Referral Success Rate: {user.get('total_referred', 0)/max(days_joined, 1)*100:.1f}%\n\n"
        f"🎯 Keep referring to earn more!"
    )
    
    bot.send_message(message.chat.id, stats_text)

# ==============================
# SUPPORT COMMAND - FIXED
# ==============================
@bot.message_handler(func=lambda message: message.text == "🆘 Support")
@check_channels_decorator
def handle_support(message):
    user_id = message.from_user.id
    
    settings = DataManager.get_settings()
    support_link = settings.get("support_link", "https://t.me/ownerusername")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🆘 Need Help?", url=support_link))
    
    bot.send_message(
        message.chat.id,
        "🆘 <b>SUPPORT</b>\n\n"
        "Facing any problem? Contact the owner directly.\n\n"
        "📖 <b>Bot Guide:</b>\n"
        "1. Share your referral link with friends\n"
        "2. Friends must join all channels\n"
        "3. You earn ₹2 per successful referral\n"
        "4. Withdraw when you reach ₹20\n"
        "5. Claim daily bonus every 24 hours\n\n"
        "For immediate assistance, click the button below:",
        reply_markup=markup
    )

# ==============================
# CALLBACK QUERY HANDLERS - FIXED
# ==============================
@bot.callback_query_handler(func=lambda call: call.data == "verify_channels")
def verify_channels(call):
    user_id = call.from_user.id
    is_member, not_joined = ChannelVerifier.check_membership(user_id)
    
    if not is_member:
        bot.answer_callback_query(call.id, "❌ Please join all channels first!")
        ChannelVerifier.show_force_join_message(call.message.chat.id, not_joined)
        return
    
    # Update user status
    users = DataManager.get_users()
    if str(user_id) in users:
        users[str(user_id)]["has_joined_channels"] = True
        DataManager.save_users(users)
        
        # ✅ FIXED: Complete referral if applicable (now safe from duplicates)
        UserManager.complete_referral(user_id)
    
    bot.edit_message_text(
        "✅ Verification successful!\n"
        "Welcome to Refer & Earn Bot!",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Show main menu
    bot.send_message(
        call.message.chat.id,
        "Choose an option from the menu below:",
        reply_markup=KeyboardManager.get_main_keyboard()
    )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "referral_stats")
def show_referral_stats(call):
    user_id = call.from_user.id
    referrals = DataManager.get_referrals()
    user_referrals = referrals.get(str(user_id), {})
    
    pending = len(user_referrals.get("pending_referrals", []))
    completed = len(user_referrals.get("referred_users", []))
    total_earnings = user_referrals.get("total_earnings", 0.0)
    
    stats_text = (
        f"📊 <b>Your Referral Stats</b>\n\n"
        f"✅ Completed: {completed}\n"
        f"⏳ Pending: {pending}\n"
        f"💰 Total Earnings: ₹{total_earnings:.2f}"
    )
    
    bot.edit_message_text(
        stats_text,
        call.message.chat.id,
        call.message.message_id
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "leaderboard")
def show_leaderboard(call):
    users = DataManager.get_users()
    referrals = DataManager.get_referrals()
    
    # HTML escaping helper
    def escape_html(text):
        if not text:
            return ""
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
    
    # Create leaderboard
    leaderboard = []
    for user_id_str, user_data in users.items():
        if not isinstance(user_data, dict):
            continue
            
        user_refs = referrals.get(user_id_str, {})
        completed = len(user_refs.get("referred_users", []))
        if completed > 0:
            leaderboard.append({
                "user_id": int(user_id_str),
                "username": user_data.get("username", "N/A"),
                "first_name": user_data.get("first_name", "User"),
                "referrals": completed,
                "earnings": user_refs.get("total_earnings", 0)
            })
    
    # Sort by referrals
    leaderboard.sort(key=lambda x: x["referrals"], reverse=True)
    
    # Create message
    leaderboard_text = "<b>🏆 REFERRAL LEADERBOARD</b>\n\n"
    
    for i, entry in enumerate(leaderboard[:10], 1):
        # Escape HTML in user-provided data
        first_name_safe = escape_html(entry['first_name'])
        username_safe = escape_html(entry['username'])
        
        leaderboard_text += (
            f"{i}. {first_name_safe} (@{username_safe})\n"
            f"   👥 Referrals: {entry['referrals']}\n"
            f"   💰 Earned: ₹{entry['earnings']:.2f}\n\n"
        )
    
    if not leaderboard:
        leaderboard_text = "No referrals yet. Be the first to top the leaderboard!"
    
    bot.edit_message_text(
        leaderboard_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )
    bot.answer_callback_query(call.id)

# ==============================
# ==============================
# ADMIN HANDLERS - FIXED
# ==============================
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    user_id = message.from_user.id
    settings = DataManager.get_settings()
    
    admin_ids = settings.get("admin_ids", ADMIN_IDS)
    if user_id not in admin_ids:
        bot.send_message(message.chat.id, "❌ Access denied!")
        return
    
    bot.send_message(
        message.chat.id,
        "⚙️ <b>ADMIN PANEL</b>\n\n"
        "Choose an option:",
        reply_markup=KeyboardManager.get_admin_keyboard()
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith('admin_')
    and not call.data.startswith('admin_approve_')
    and not call.data.startswith('admin_reject_')
)
def handle_admin_actions(call):
    user_id = call.from_user.id
    settings = DataManager.get_settings()
    
    admin_ids = settings.get("admin_ids", ADMIN_IDS)
    if user_id not in admin_ids:
        bot.answer_callback_query(call.id, "❌ Access denied!")
        return

    # ---- existing admin panel logic stays SAME below ----
    if call.data == 'admin_set_referral':
        msg = bot.send_message(call.message.chat.id, "Enter new referral amount (INR):")
        bot.register_next_step_handler(msg, process_set_referral)

    elif call.data == 'admin_set_bonus':
        msg = bot.send_message(call.message.chat.id, "Enter new bonus amount (INR):")
        bot.register_next_step_handler(msg, process_set_bonus)

    elif call.data == 'admin_set_min_withdraw':
        msg = bot.send_message(call.message.chat.id, "Enter new minimum withdraw amount (INR):")
        bot.register_next_step_handler(msg, process_set_min_withdraw)

    elif call.data == 'admin_add_balance':
        msg = bot.send_message(call.message.chat.id, "Enter user ID to add balance:")
        bot.register_next_step_handler(msg, process_add_balance_step1)

    elif call.data == 'admin_remove_balance':
        msg = bot.send_message(call.message.chat.id, "Enter user ID to remove balance:")
        bot.register_next_step_handler(msg, process_remove_balance_step1)

    elif call.data == 'admin_create_redeem':
        msg = bot.send_message(call.message.chat.id, "Enter redeem code amount (INR):")
        bot.register_next_step_handler(msg, process_create_redeem_step1)

    elif call.data == 'admin_edit_redeem':
        redeem_codes = DataManager.get_redeem_codes()
        if not redeem_codes:
            bot.send_message(call.message.chat.id, "❌ No redeem codes found!")
            return
        
        codes_text = "📋 Available Codes:\n"
        for code, data in redeem_codes.items():
            codes_text += f"\n<code>{code}</code> - ₹{data.get('amount', 0)}"

        msg = bot.send_message(call.message.chat.id, f"{codes_text}\n\nEnter code to edit:")
        bot.register_next_step_handler(msg, process_edit_redeem_step1)

    elif call.data == 'admin_view_stats':
        show_admin_stats(call.message)

    elif call.data == 'admin_add_support_link':
        msg = bot.send_message(call.message.chat.id, "Enter support link URL:")
        bot.register_next_step_handler(msg, process_add_support_link)

    elif call.data == 'admin_broadcast':
        msg = bot.send_message(call.message.chat.id, "Send message/image/video to broadcast:")
        bot.register_next_step_handler(msg, process_broadcast)

    bot.answer_callback_query(call.id)

def process_set_referral(message):
    try:
        amount = float(message.text)
        settings = DataManager.get_settings()
        settings["referral_amount"] = amount
        DataManager.save_settings(settings)
        
        bot.send_message(
            message.chat.id,
            f"✅ Referral amount set to ₹{amount}"
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_set_bonus(message):
    try:
        amount = float(message.text)
        settings = DataManager.get_settings()
        settings["bonus_amount"] = amount
        DataManager.save_settings(settings)
        
        bot.send_message(
            message.chat.id,
            f"✅ Bonus amount set to ₹{amount}"
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_set_min_withdraw(message):
    try:
        amount = float(message.text)
        settings = DataManager.get_settings()
        settings["min_withdraw"] = amount
        DataManager.save_settings(settings)
        
        bot.send_message(
            message.chat.id,
            f"✅ Minimum withdraw amount set to ₹{amount}"
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_add_balance_step1(message):
    try:
        target_id = int(message.text)
        msg = bot.send_message(
            message.chat.id,
            "Enter amount to add (INR):"
        )
        bot.register_next_step_handler(msg, process_add_balance_step2, target_id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID!")

def process_add_balance_step2(message, target_id):
    try:
        amount = float(message.text)
        if UserManager.update_balance(target_id, amount, "add"):
            user = UserManager.get_user(target_id)
            bot.send_message(
                message.chat.id,
                f"✅ Added ₹{amount} to user {target_id}\n"
                f"New balance: ₹{user.get('balance', 0.0):.2f}"
            )
            
            # Notify user
            try:
                bot.send_message(
                    target_id,
                    f"💰 Admin added ₹{amount} to your account!\n"
                    f"New balance: ₹{user.get('balance', 0.0):.2f}"
                )
            except:
                pass
            
            DataManager.add_log("admin_action", message.from_user.id,
                              f"Added ₹{amount} to user {target_id}")
        else:
            bot.send_message(message.chat.id, "❌ User not found!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_remove_balance_step1(message):
    try:
        target_id = int(message.text)
        msg = bot.send_message(
            message.chat.id,
            "Enter amount to remove (INR):"
        )
        bot.register_next_step_handler(msg, process_remove_balance_step2, target_id)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID!")

def process_remove_balance_step2(message, target_id):
    try:
        amount = float(message.text)
        if UserManager.update_balance(target_id, amount, "subtract"):
            user = UserManager.get_user(target_id)
            bot.send_message(
                message.chat.id,
                f"✅ Removed ₹{amount} from user {target_id}\n"
                f"New balance: ₹{user.get('balance', 0.0):.2f}"
            )
            
            # Notify user
            try:
                bot.send_message(
                    target_id,
                    f"⚠️ Admin removed ₹{amount} from your account!\n"
                    f"New balance: ₹{user.get('balance', 0.0):.2f}"
                )
            except:
                pass
            
            DataManager.add_log("admin_action", message.from_user.id,
                              f"Removed ₹{amount} from user {target_id}")
        else:
            bot.send_message(message.chat.id, "❌ Insufficient balance or user not found!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_create_redeem_step1(message):
    try:
        amount = int(float(message.text))
        msg = bot.send_message(
            message.chat.id,
            "Enter maximum users allowed:"
        )
        bot.register_next_step_handler(msg, process_create_redeem_step2, amount)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_create_redeem_step2(message, amount):
    try:
        max_users = int(message.text)
        msg = bot.send_message(
            message.chat.id,
            "Enter custom code (letters/numbers only):"
        )
        bot.register_next_step_handler(msg, process_create_redeem_step3, amount, max_users)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid number!")

def process_create_redeem_step3(message, amount, max_users):
    code = message.text.strip().upper()
    
    if not code.isalnum():
        bot.send_message(message.chat.id, "❌ Code must contain only letters and numbers!")
        return
    
    redeem_codes = DataManager.get_redeem_codes()
    
    if code in redeem_codes:
        bot.send_message(message.chat.id, "❌ Code already exists!")
        return
    
    redeem_codes[code] = {
        "amount": amount,
        "max_users": max_users,
        "used_count": 0,
        "used_by": [],
        "created_by": message.from_user.id,
        "created_at": datetime.datetime.now().isoformat(),
        "is_active": True
    }
    
    DataManager.save_redeem_codes(redeem_codes)
    
    bot.send_message(
        message.chat.id,
        f"✅ Redeem code created!\n\n"
        f"🎟 Code: <code>{code}</code>\n"
        f"💰 Amount: ₹{amount}\n"
        f"👥 Max Users: {max_users}"
    )
    
    DataManager.add_log("redeem_code", message.from_user.id,
                       f"Created code {code} for ₹{amount}")

def process_edit_redeem_step1(message):
    code = message.text.strip().upper()
    redeem_codes = DataManager.get_redeem_codes()
    
    if code not in redeem_codes:
        bot.send_message(message.chat.id, "❌ Code not found!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✏️ Edit Amount", callback_data=f"edit_redeem_amount_{code}"),
        types.InlineKeyboardButton("👥 Edit Max Users", callback_data=f"edit_redeem_max_{code}"),
        types.InlineKeyboardButton("✅ Activate/Deactivate", callback_data=f"edit_redeem_status_{code}"),
        types.InlineKeyboardButton("🗑 Delete Code", callback_data=f"delete_redeem_{code}")
    )
    
    code_data = redeem_codes[code]
    bot.send_message(
        message.chat.id,
        f"🎟 Editing Code: <code>{code}</code>\n\n"
        f"💰 Amount: ₹{code_data.get('amount', 0)}\n"
        f"👥 Max Users: {code_data.get('max_users', 1)}\n"
        f"✅ Used: {code_data.get('used_count', 0)}/{code_data.get('max_users', 1)}\n"
        f"📊 Status: {'Active' if code_data.get('is_active', True) else 'Inactive'}",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_redeem_'))
def handle_redeem_edit(call):
    user_id = call.from_user.id
    settings = DataManager.get_settings()
    
    admin_ids = settings.get("admin_ids", ADMIN_IDS)
    if user_id not in admin_ids:
        bot.answer_callback_query(call.id, "❌ Access denied!")
        return
    
    if call.data.startswith('edit_redeem_amount_'):
        code = call.data.split('_')[-1]
        msg = bot.send_message(
            call.message.chat.id,
            f"Enter new amount for code <code>{code}</code>:"
        )
        bot.register_next_step_handler(msg, process_edit_redeem_amount, code)
    
    elif call.data.startswith('edit_redeem_max_'):
        code = call.data.split('_')[-1]
        msg = bot.send_message(
            call.message.chat.id,
            f"Enter new max users for code <code>{code}</code>:"
        )
        bot.register_next_step_handler(msg, process_edit_redeem_max, code)
    
    elif call.data.startswith('edit_redeem_status_'):
        code = call.data.split('_')[-1]
        redeem_codes = DataManager.get_redeem_codes()
        
        if code in redeem_codes:
            current_status = redeem_codes[code].get("is_active", True)
            redeem_codes[code]["is_active"] = not current_status
            DataManager.save_redeem_codes(redeem_codes)
            
            status = "activated" if redeem_codes[code]["is_active"] else "deactivated"
            bot.edit_message_text(
                f"✅ Code <code>{code}</code> {status}!",
                call.message.chat.id,
                call.message.message_id
            )
    
    elif call.data.startswith('delete_redeem_'):
        code = call.data.split('_')[-1]
        redeem_codes = DataManager.get_redeem_codes()
        
        if code in redeem_codes:
            del redeem_codes[code]
            DataManager.save_redeem_codes(redeem_codes)
            
            bot.edit_message_text(
                f"✅ Code <code>{code}</code> deleted!",
                call.message.chat.id,
                call.message.message_id
            )
    
    bot.answer_callback_query(call.id)

def process_edit_redeem_amount(message, code):
    try:
        amount = int(float(message.text))
        redeem_codes = DataManager.get_redeem_codes()
        
        if code in redeem_codes:
            redeem_codes[code]["amount"] = amount
            DataManager.save_redeem_codes(redeem_codes)
            
            bot.send_message(
                message.chat.id,
                f"✅ Amount for code <code>{code}</code> updated to ₹{amount}"
            )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount!")

def process_edit_redeem_max(message, code):
    try:
        max_users = int(message.text)
        redeem_codes = DataManager.get_redeem_codes()
        
        if code in redeem_codes:
            redeem_codes[code]["max_users"] = max_users
            DataManager.save_redeem_codes(redeem_codes)
            
            bot.send_message(
                message.chat.id,
                f"✅ Max users for code <code>{code}</code> updated to {max_users}"
            )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid number!")

# ==============================
# WITHDRAWAL ADMIN APPROVAL/REJECTION - FIXED
# ==============================
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_approve_') or call.data.startswith('admin_reject_'))
def handle_withdrawal_action(call):
    try:
        user_id = call.from_user.id
        settings = DataManager.get_settings()
        
        admin_ids = settings.get("admin_ids", ADMIN_IDS)
        if user_id not in admin_ids:
            bot.answer_callback_query(call.id, "❌ Access denied!")
            return
        
        # Parse callback data
        if call.data.startswith('admin_approve_'):
            action = "approve"
            withdrawal_id = call.data.replace('admin_approve_', '')
        else:
            action = "reject"
            withdrawal_id = call.data.replace('admin_reject_', '')
        
        # Get withdrawal data
        withdrawals = DataManager.get_withdrawals()
        
        if withdrawal_id not in withdrawals:
            bot.answer_callback_query(call.id, "❌ Withdrawal not found!")
            return
        
        withdrawal = withdrawals[withdrawal_id]
        
        if withdrawal.get("status") != "pending":
            bot.answer_callback_query(call.id, "❌ Withdrawal already processed!")
            return
        
        if action == "approve":
            # APPROVE WITHDRAWAL
            user = UserManager.get_user(withdrawal.get("user_id"))
            if not user:
                bot.answer_callback_query(call.id, "❌ User not found!")
                return
            
            amount = withdrawal.get("amount", 0)
            
            # Update withdrawal status
            withdrawal["status"] = "approved"
            withdrawal["admin_action_time"] = datetime.datetime.now().isoformat()
            withdrawal["admin_id"] = user_id
            
            # Update user's total withdrawn
            users = DataManager.get_users()
            user_key = str(withdrawal.get("user_id"))
            if user_key in users:
                users[user_key]["total_withdrawn"] = users[user_key].get("total_withdrawn", 0.0) + amount
                DataManager.save_users(users)
            
            # Notify user
            try:
                if withdrawal.get("method") == "upi":
                    upi_id = withdrawal.get('upi_id', 'N/A')
                    upi_id_safe = escape_html(upi_id) if upi_id else 'N/A'
                    
                    bot.send_message(
                        withdrawal.get("user_id"),
                        f"✅ <b>Withdrawal Approved!</b>\n\n"
                        f"💰 Amount: ₹{amount}\n"
                        f"📱 Method: UPI\n"
                        f"🔗 UPI ID: <code>{upi_id_safe}</code>\n"
                        f"✅ Payment has been sent successfully!\n\n"
                        f"💳 <b>Please check your bank account/UPI app.</b>\n"
                        f"⏰ <i>It may take 5-10 minutes to reflect.</i>",
                        parse_mode='HTML'
                    )
                else:
                    bot.send_message(
                        withdrawal.get("user_id"),
                        f"✅ <b>Withdrawal Approved!</b>\n\n"
                        f"💰 Amount: ₹{amount}\n"
                        f"📱 Method: QR Code\n"
                        f"✅ Payment has been sent successfully!\n\n"
                        f"💳 <b>Please check your bank account/UPI app.</b>\n"
                        f"⏰ <i>It may take 5-10 minutes to reflect.</i>",
                        parse_mode='HTML'
                    )
            except Exception as e:
                print(f"Error notifying user: {e}")
            
            # Update admin message
            try:
                new_text = (
                    f"✅ <b>APPROVED</b>\n\n"
                    f"📊 Withdrawal ID: <code>{withdrawal_id}</code>\n"
                    f"💰 Amount: ₹{amount}\n"
                    f"👤 User ID: {withdrawal.get('user_id')}\n"
                    f"✅ Approved by: Admin {user_id}\n"
                    f"⏰ Time: {datetime.datetime.now().strftime('%H:%M:%S')}"
                )
                
                bot.edit_message_text(
                    new_text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"Error editing message: {e}")
                bot.send_message(
                    call.message.chat.id,
                    f"✅ Withdrawal {withdrawal_id} approved!",
                    reply_to_message_id=call.message.message_id
                )
            
            # Log to logs channel
            try:
                logs_channel = settings.get("logs_channel", LOGS_CHANNEL)
                
                # Escape HTML for safety
                user_first_name = escape_html(user.get('first_name', 'User'))
                user_username = escape_html(user.get('username', 'N/A'))
                
                log_text = (
                    f"💰 <b>WITHDRAWAL APPROVED</b>\n\n"
                    f"👤 User: {user_first_name}\n"
                    f"🆔 ID: <code>{withdrawal.get('user_id')}</code>\n"
                    f"👤 Username: @{user_username}\n"
                    f"💳 Amount: ₹{amount}\n"
                    f"📱 Method: {withdrawal.get('method', '').upper()}\n"
                )
                
                if withdrawal.get("method") == "upi":
                    upi_id = withdrawal.get('upi_id', 'N/A')
                    if upi_id:
                        upi_id_safe = escape_html(upi_id)
                        log_text += f"🔗 UPI ID: <code>{upi_id_safe}</code>\n"
                
                log_text += (
                    f"⏰ Request Time: {withdrawal.get('request_time', 'N/A')}\n"
                    f"✅ Approved Time: {withdrawal.get('admin_action_time', 'N/A')}\n"
                    f"👮 Approved by: Admin ID {user_id}\n\n"
                    f"✅ <b>Payment Sent Successfully</b>"
                )
                
                bot.send_message(logs_channel, log_text, parse_mode='HTML')
            except Exception as e:
                print(f"Error sending to logs channel: {e}")
            
            # Add to logs
            DataManager.add_log("withdrawal_approved", withdrawal.get("user_id"),
                              f"Approved withdrawal of ₹{amount} by admin {user_id}")
            
            bot.answer_callback_query(call.id, "✅ Withdrawal approved!")
        
        else:  # REJECT WITHDRAWAL
            # REJECT WITHDRAWAL
            user = UserManager.get_user(withdrawal.get("user_id"))
            if not user:
                bot.answer_callback_query(call.id, "❌ User not found!")
                return
            
            amount = withdrawal.get("amount", 0)
            
            # REFUND BALANCE TO USER
            if withdrawal.get("balance_deducted"):
                UserManager.update_balance(withdrawal.get("user_id"), amount, "add")
            
            # Update withdrawal status
            withdrawal["status"] = "rejected"
            withdrawal["admin_action_time"] = datetime.datetime.now().isoformat()
            withdrawal["admin_id"] = user_id
            
            # Notify user
            try:
                bot.send_message(
                    withdrawal.get("user_id"),
                    f"❌ <b>Withdrawal Rejected</b>\n\n"
                    f"💰 Amount: ₹{amount}\n"
                    f"❌ Your withdrawal request has been rejected.\n"
                    f"💳 <b>₹{amount} has been refunded to your balance.</b>\n"
                    f"📞 Contact support for more information.",
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"Error notifying user: {e}")
            
            # Update admin message
            try:
                new_text = (
                    f"❌ <b>REJECTED</b>\n\n"
                    f"📊 Withdrawal ID: <code>{withdrawal_id}</code>\n"
                    f"💰 Amount: ₹{amount}\n"
                    f"👤 User ID: {withdrawal.get('user_id')}\n"
                    f"❌ Rejected by: Admin {user_id}\n"
                    f"⏰ Time: {datetime.datetime.now().strftime('%H:%M:%S')}"
                )
                
                bot.edit_message_text(
                    new_text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"Error editing message: {e}")
                bot.send_message(
                    call.message.chat.id,
                    f"❌ Withdrawal {withdrawal_id} rejected!",
                    reply_to_message_id=call.message.message_id
                )
            
            # Log to logs channel
            try:
                logs_channel = settings.get("logs_channel", LOGS_CHANNEL)
                
                # Escape HTML for safety
                user_first_name = escape_html(user.get('first_name', 'User'))
                user_username = escape_html(user.get('username', 'N/A'))
                
                log_text = (
                    f"❌ <b>WITHDRAWAL REJECTED</b>\n\n"
                    f"👤 User: {user_first_name}\n"
                    f"🆔 ID: <code>{withdrawal.get('user_id')}</code>\n"
                    f"👤 Username: @{user_username}\n"
                    f"💳 Amount: ₹{amount}\n"
                    f"📱 Method: {withdrawal.get('method', '').upper()}\n"
                    f"⏰ Request Time: {withdrawal.get('request_time', 'N/A')}\n"
                    f"❌ Rejected Time: {withdrawal.get('admin_action_time', 'N/A')}\n"
                    f"👮 Rejected by: Admin ID {user_id}\n\n"
                    f"💳 <b>Amount refunded to user balance.</b>"
                )
                
                bot.send_message(logs_channel, log_text, parse_mode='HTML')
            except Exception as e:
                print(f"Error sending to logs channel: {e}")
            
            # Add to logs
            DataManager.add_log("withdrawal_rejected", withdrawal.get("user_id"),
                              f"Rejected withdrawal of ₹{amount} by admin {user_id}")
            
            bot.answer_callback_query(call.id, "❌ Withdrawal rejected!")
        
        # Save updated withdrawal
        withdrawals[withdrawal_id] = withdrawal
        DataManager.save_withdrawals(withdrawals)
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR in handle_withdrawal_action: {e}")
        traceback.print_exc()
        try:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)[:50]}")
        except:
            pass

def show_admin_stats(message):
    users = DataManager.get_users()
    referrals = DataManager.get_referrals()
    withdrawals = DataManager.get_withdrawals()
    settings = DataManager.get_settings()
    
    # Calculate stats
    total_users = len(users)
    active_users = sum(1 for u in users.values() if isinstance(u, dict) and u.get("is_active", True))
    total_balance = sum(u.get("balance", 0.0) for u in users.values() if isinstance(u, dict))
    total_withdrawn = sum(u.get("total_withdrawn", 0.0) for u in users.values() if isinstance(u, dict))
    
    # Pending withdrawals
    pending_withdrawals = sum(1 for w in withdrawals.values() if isinstance(w, dict) and w.get("status") == "pending")
    pending_amount = sum(w.get("amount", 0.0) for w in withdrawals.values() if isinstance(w, dict) and w.get("status") == "pending")
    
    # Today's stats
    today = datetime.datetime.now().date()
    today_users = 0
    for u in users.values():
        if not isinstance(u, dict):
            continue
        joined_date_str = u.get("joined_date")
        if joined_date_str:
            try:
                joined_date = datetime.datetime.fromisoformat(joined_date_str).date()
                if joined_date == today:
                    today_users += 1
            except:
                pass
    
    stats_text = (
        f"📊 <b>ADMIN STATISTICS</b>\n\n"
        f"👥 Total Users: {total_users}\n"
        f"✅ Active Users: {active_users}\n"
        f"📈 New Today: {today_users}\n\n"
        f"💰 Total Balance: ₹{total_balance:.2f}\n"
        f"💸 Total Withdrawn: ₹{total_withdrawn:.2f}\n"
        f"⏳ Pending Withdrawals: {pending_withdrawals} (₹{pending_amount:.2f})\n\n"
        f"👥 Total Referrals: {sum(len(r.get('referred_users', [])) for r in referrals.values() if isinstance(r, dict))}\n\n"
        f"⚙️ Settings:\n"
        f"• Referral Amount: ₹{settings.get('referral_amount', 2)}\n"
        f"• Bonus Amount: ₹{settings.get('bonus_amount', 0.10)}\n"
        f"• Min Withdraw: ₹{settings.get('min_withdraw', 20)}"
    )
    
    bot.send_message(message.chat.id, stats_text)

def process_add_support_link(message):
    link = message.text.strip()
    settings = DataManager.get_settings()
    settings["support_link"] = link
    DataManager.save_settings(settings)
    
    bot.send_message(
        message.chat.id,
        f"✅ Support link updated!\n"
        f"New link: {link}"
    )

def process_broadcast(message):
    user_id = message.from_user.id
    settings = DataManager.get_settings()
    
    admin_ids = settings.get("admin_ids", ADMIN_IDS)
    if user_id not in admin_ids:
        return
    
    users = DataManager.get_users()
    total_users = len(users)
    success = 0
    failed = 0
    
    # Show broadcasting status
    status_msg = bot.send_message(
        message.chat.id,
        f"📢 Broadcasting to {total_users} users...\n"
        f"✅ Sent: 0\n"
        f"❌ Failed: 0"
    )
    
    def broadcast_thread():
        nonlocal success, failed
        
        for uid_str in users.keys():
            try:
                uid = int(uid_str)
                
                # Forward the message
                if message.content_type == 'text':
                    bot.send_message(uid, message.text)
                elif message.content_type == 'photo':
                    bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)
                elif message.content_type == 'video':
                    bot.send_video(uid, message.video.file_id, caption=message.caption)
                elif message.content_type == 'document':
                    bot.send_document(uid, message.document.file_id, caption=message.caption)
                
                success += 1
                
            except Exception as e:
                failed += 1
            
            # Small delay
            time.sleep(0.05)
        
        # Final status
        try:
            bot.edit_message_text(
                f"📢 Broadcast Completed!\n\n"
                f"✅ Successfully sent: {success}\n"
                f"❌ Failed: {failed}\n"
                f"📊 Total Users: {total_users}",
                message.chat.id,
                status_msg.message_id
            )
        except:
            pass
    
    # Start broadcast in thread
    thread = threading.Thread(target=broadcast_thread)
    thread.start()

# ==============================
# ERROR HANDLING
# ==============================
@bot.message_handler(func=lambda message: True, content_types=['audio', 'document', 'photo', 'sticker', 'video', 'voice', 'location', 'contact'])
def handle_unsupported(message):
    bot.send_message(message.chat.id, "❌ Please use the menu buttons or text commands.")

# ==============================
# MAIN EXECUTION
# ==============================
if __name__ == "__main__":
    print("🤖 Bot starting...")
    print(f"👮 Admin IDs: {ADMIN_IDS}")
    print(f"📢 Force Join Channels: {[c['name'] for c in FORCE_JOIN_CHANNELS]}")
    
    # Create data directory if not exists
    os.makedirs('data', exist_ok=True)
    
    # Initialize data files if not exists
    DataManager.get_users()
    DataManager.get_referrals()
    DataManager.get_withdrawals()
    DataManager.get_redeem_codes()
    DataManager.get_settings()
    
    # Clean up any corrupted data
    print("🔧 Initializing data files...")
    
    try:
        # Start polling
        print("🚀 Bot is running...")
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        traceback.print_exc()