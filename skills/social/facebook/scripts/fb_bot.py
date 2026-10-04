import sys
import os
import asyncio
from fbchat_muqit import Client, Message, EventType
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Configure Gemini AI SDK if key is configured
try:
    import google.generativeai as genai
    GEMINI_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
except ImportError:
    genai = None
    GEMINI_KEY = None

# Add the Tapo scripts path to sys.path to reuse its control functions
TAPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "home", "tapo", "scripts"))
sys.path.append(TAPO_PATH)

try:
    from tapo_control import get_device_by_alias, discover_all_devices
except ImportError:
    # Fallback to dummy functions if Tapo skill is not present
    get_device_by_alias = None
    discover_all_devices = None

# Load authorized users
AUTH_USERS_RAW = os.getenv("AUTHORIZED_FB_USERS", "")
AUTHORIZED_USERS = [uid.strip() for uid in AUTH_USERS_RAW.split(",") if uid.strip()]

# Load Tapo credentials
TAPO_USER = os.getenv("TAPO_USERNAME")
TAPO_PASS = os.getenv("TAPO_PASSWORD")

import json

COOKIES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fb_cookies.json")

# Write session cookies from env to file if configured
FB_COOKIES_ENV = os.getenv("FB_COOKIES", "")
if FB_COOKIES_ENV:
    try:
        cookies_data = json.loads(FB_COOKIES_ENV)
        with open(COOKIES_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies_data, f, indent=4)
        print(f"Successfully wrote cookies from environment variable to {COOKIES_PATH}", flush=True)
    except Exception as e:
        print(f"Warning: Failed to parse FB_COOKIES env variable: {e}", file=sys.stderr)

if not os.path.exists(COOKIES_PATH):
    print(f"Error: Cookies file not found at {COOKIES_PATH} and FB_COOKIES env variable is not configured.", file=sys.stderr)
    # Don't exit immediately so the syntax check still works during validation, but prevent run
    client = None
else:
    client = Client(cookies_file_path=COOKIES_PATH)
# Tapo cache path to scan device names offline
TAPO_CACHE_PATH = os.path.abspath(os.path.join(TAPO_PATH, "tapo_cache.json"))

# Custom room-to-IP mappings to handle duplicate device names
ROOM_MAP_RAW = os.getenv("TAPO_ROOM_MAP", "")
ROOM_MAP = {}
if ROOM_MAP_RAW:
    for item in ROOM_MAP_RAW.split(","):
        if ":" in item:
            k, v = item.split(":", 1)
            ROOM_MAP[k.strip().lower()] = v.strip()

def get_cached_devices():
    if os.path.exists(TAPO_CACHE_PATH):
        try:
            with open(TAPO_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_cached_device_list():
    cache = get_cached_devices()
    devices = []
    for alias, info in cache.items():
        devices.append({
            "ip": info.get("ip", ""),
            "alias": alias,
            "model": info.get("type", "Unknown")
        })
    return devices

def parse_natural_language_command(text, devices):
    text_lower = text.lower()
    
    # 1. Determine the action (supporting English and Tagalog root words)
    action = None
    if any(phrase in text_lower for phrase in ["turn on", "switch on", "power on", "enable", "activate", "buksan", "sindi"]):
        action = "on"
    elif any(phrase in text_lower for phrase in ["turn off", "switch off", "power off", "disable", "deactivate", "patay"]):
        action = "off"
    elif any(phrase in text_lower for phrase in ["toggle", "switch", "palitan"]):
        action = "toggle"
    elif any(phrase in text_lower for phrase in ["status", "info", "state", "check", "kamusta"]):
        action = "status"
    elif any(phrase in text_lower for phrase in ["list", "show all", "find"]):
        action = "list"
        
    if not action:
        return None, None
        
    if action == "list":
        return "list", None
        
    # 2. Match by custom room-to-IP map
    for room, ip in ROOM_MAP.items():
        if room in text_lower:
            return action, ip
            
    # 3. Find the target device by scanning the text for known aliases or IPs
    for d in devices:
        # Match by IP
        if d["ip"] in text:
            return action, d["ip"]
        # Match by alias (case-insensitive)
        alias_lower = d["alias"].lower()
        if alias_lower in text_lower:
            return action, d["alias"]
            
    return action, None

async def evaluate_message_with_ai(text_content):
    if not GEMINI_KEY or not genai:
        return None
        
    cached_devices = get_cached_device_list()
    device_info_str = ""
    for d in cached_devices:
        device_info_str += f"- Name/Alias: '{d['alias']}', IP: '{d['ip']}', Model: '{d['model']}'\n"
        
    room_map_str = ""
    for room, ip in ROOM_MAP.items():
        room_map_str += f"- Room Keyword: '{room}' -> IP: '{ip}'\n"
        
    prompt = f"""You are an AI Smart Home Assistant for the Ayala family.
Your job is to analyze incoming chat messages and decide if you need to control or check any Tapo smart home devices.

Available Tapo Devices:
{device_info_str}
Custom Room Mappings (you can match locations directly to these IPs):
{room_map_str}

Analyze the message: "{text_content}"

Decide:
1. Is this a request to turn a device on, turn it off, toggle it, or check its status/info?
2. Does this message require you to take action or respond (for example, if it describes a home automation command, or if it is a greeting/question addressed to the bot)?
3. Which device or IP is the target?

Respond STRICTLY with a JSON object in this format (no markdown code blocks or extra text, just raw JSON):
{{
  "is_command": true/false (true if you need to execute a command or reply to a mention/question),
  "action": "on" | "off" | "toggle" | "status" | "list" | null,
  "target": "<resolved_ip_or_alias_or_room_name>" | null,
  "reply": "<optional_friendly_reply_text>" | null
}}
"""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        return None

if client:
    @client.event
    async def on_message(message: Message):
        # Ignore messages sent by the bot itself
        if message.sender_id == client.uid:
            return
            
        text = message.text or ""
        text_lower = text.lower()
        print(f"Incoming message from {message.sender_id}: '{text}' (thread_id: {message.thread_id})", flush=True)
        
        # Route logic using Gemini API if configured
        ai_response = None
        if GEMINI_KEY:
            print("Evaluating message with Gemini AI...", flush=True)
            ai_response = await evaluate_message_with_ai(text)
            
        if ai_response:
            print(f"Gemini AI evaluation result: {ai_response}", flush=True)
            should_respond = ai_response.get("is_command", False)
            if not should_respond:
                return
                
            # Check authorization
            if message.sender_id not in AUTHORIZED_USERS:
                print(f"Unauthorized command attempt from user ID {message.sender_id}: {text}", flush=True)
                try:
                    await client.send_message(f"Unauthorized: Your User ID is {message.sender_id}. You are not authorized to control this bot.", message.thread_id)
                except Exception as e:
                    print(f"Failed to send unauthorized reply: {e}", flush=True)
                return
                
            # Send AI reply if provided (e.g. greeting or confirmation)
            reply_text = ai_response.get("reply")
            if reply_text:
                try:
                    await client.send_message(reply_text, message.thread_id)
                except Exception as e:
                    print(f"Failed to send AI response message: {e}", flush=True)
                    
            command = ai_response.get("action")
            args = ai_response.get("target") or ""
            
            if not command:
                # If there's no device action, we've already sent the friendly reply, so we can return
                return
        else:
            # Fallback to local rule-based parsing if Gemini API key is missing or failed
            is_command = text.startswith("!")
            
            bot_mentions = ["second-command", "ayala bot", "bot", "@61591442588854"]
            if client.name:
                bot_mentions.append(client.name.lower())
                
            is_tagged = any(name in text_lower for name in bot_mentions) or (
                message.mentions and any(m.user_id == client.uid for m in message.mentions)
            )
            
            cached_devices = get_cached_device_list()
            nl_action, nl_target = parse_natural_language_command(text, cached_devices)
            
            should_respond = is_command or is_tagged or (nl_action is not None and nl_target is not None)
            
            if not should_respond:
                return
                
            # Check authorization
            if message.sender_id not in AUTHORIZED_USERS:
                print(f"Unauthorized command attempt from user ID {message.sender_id}: {text}", flush=True)
                try:
                    await client.send_message(f"Unauthorized: Your User ID is {message.sender_id}. You are not authorized to control this bot.", message.thread_id)
                except Exception as e:
                    print(f"Failed to send unauthorized reply: {e}", flush=True)
                return
                
            # Route logic
            if is_command:
                print(f"Command received from {message.sender_id}: {text}", flush=True)
                parts = text[1:].strip().split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
            else:
                # Natural language command routing
                if nl_action:
                    print(f"Natural language command parsed from {message.sender_id}: {nl_action} on {nl_target}", flush=True)
                    command = nl_action
                    args = nl_target or ""
                else:
                    # Bot was tagged but no specific command parsed
                    print(f"Bot tagged by {message.sender_id}: '{text}'", flush=True)
                    try:
                        await client.send_message("Hello! I am your Ayala smart home assistant. You can control devices by saying things like 'turn off Light' or using commands like !list.", message.thread_id)
                    except Exception as e:
                        print(f"Failed to send bot greeting: {e}", flush=True)
                    return
        
        if command == "ping":
            await client.send_message("Pong! 🏡 Bot is online and listening.", message.thread_id)
            
        elif command == "list":
            if not discover_all_devices or not TAPO_USER or not TAPO_PASS:
                await client.send_message("Tapo integration is not loaded or configured.", message.thread_id)
                return
                
            await client.send_message("Scanning local network for Tapo devices... 🔍", message.thread_id)
            try:
                devices = await discover_all_devices(TAPO_USER, TAPO_PASS, silent=True)
                if not devices:
                    await client.send_message("No Tapo devices found on the local network.", message.thread_id)
                    return
                    
                response = "Discovered Tapo Devices:\n"
                for d in devices:
                    state_str = "ON" if d["is_on"] else "OFF"
                    if d["unauthorized"]:
                        state_str = "LOCKED (Need Third-Party Compatibility)"
                    response += f"• {d['alias']} ({d['model']}): {state_str} at {d['ip']}\n"
                await client.send_message(response.strip(), message.thread_id)
            except Exception as e:
                await client.send_message(f"Error scanning network: {str(e)}", message.thread_id)
                
        elif command in ["on", "off", "toggle", "status"]:
            if not get_device_by_alias or not TAPO_USER or not TAPO_PASS:
                await client.send_message("Tapo integration is not loaded or configured.", message.thread_id)
                return
                
            if not args:
                await client.send_message(f"Please specify a device name or IP, e.g. !{command} Living Room Plug", message.thread_id)
                return
                
            await client.send_message(f"Contacting device '{args}'...", message.thread_id)
            try:
                dev, ip = await get_device_by_alias(args, TAPO_USER, TAPO_PASS)
                if not dev:
                    await client.send_message(f"Device '{args}' not found on the local network.", message.thread_id)
                    return
                    
                info = await dev.get_device_info()
                info_dict = info.to_dict()
                alias = info_dict.get("nickname", args)
                model = info_dict.get("model", "Unknown")
                is_on = info_dict.get("device_on", False)
                
                # Room location and nickname verification check
                expected_room = None
                for room_name, room_ip in ROOM_MAP.items():
                    if args == room_ip or args.lower() == room_name:
                        expected_room = room_name
                        break
                        
                if expected_room:
                    # If the user has customized the nickname in the Tapo App
                    if alias.lower() not in ["light", "unknown", "tapo bulb", "smart bulb"]:
                        # Verify that the custom nickname matches the requested room/location
                        if expected_room not in alias.lower() and alias.lower() not in expected_room:
                            print(f"Aborted: Nickname '{alias}' does not match expected room '{expected_room}'", flush=True)
                            await client.send_message(
                                f"❌ Aborted: Device at {ip} has nickname '{alias}', which does not match your requested location '{expected_room}'. "
                                "Command cancelled to prevent controlling the wrong device.",
                                message.thread_id
                            )
                            return
                
                if command == "on":
                    await dev.on()
                    await client.send_message(f"Success: Turned ON '{alias}' ({model}).", message.thread_id)
                elif command == "off":
                    await dev.off()
                    await client.send_message(f"Success: Turned OFF '{alias}' ({model}).", message.thread_id)
                elif command == "toggle":
                    if is_on:
                        await dev.off()
                        await client.send_message(f"Success: Toggled OFF '{alias}' ({model}).", message.thread_id)
                    else:
                        await dev.on()
                        await client.send_message(f"Success: Toggled ON '{alias}' ({model}).", message.thread_id)
                elif command == "status":
                    state_str = "ON" if is_on else "OFF"
                    response = f"Device Status for '{alias}':\n• Model: {model}\n• IP: {ip}\n• State: {state_str}"
                    if hasattr(dev, "get_current_power"):
                        try:
                            power = await dev.get_current_power()
                            power_dict = power.to_dict()
                            response += f"\n• Power Draw: {power_dict.get('current_power', 0) / 1000.0:.2f} W"
                        except Exception:
                            pass
                    await client.send_message(response, message.thread_id)
            except Exception as e:
                await client.send_message(f"Error controlling device: {str(e)}", message.thread_id)
                
        else:
            await client.send_message(f"Unknown command: !{command}. Try !ping, !list, !on, !off, !toggle, or !status.", message.thread_id)

def start_bot():
    if not client:
        print("Could not start bot. Ensure fb_cookies.json is present.", file=sys.stderr)
        return
    print("Starting Facebook Messenger Bot...")
    print(f"Authorized users: {AUTHORIZED_USERS}")
    client.run()

if __name__ == "__main__":
    start_bot()
