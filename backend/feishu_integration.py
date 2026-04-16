"""Feishu/Lark Bot Integration for Multi-Agent Pipeline.

Handles incoming messages from Feishu via WebSocket and dispatches to the agent pipeline.
Supports both Webhook and WebSocket modes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger(__name__)

# Feishu config paths
FEISHU_CONFIG_PATH = Path.home() / ".multiagent" / "feishu.json"


def _load_feishu_config() -> dict[str, Any]:
    """Load Feishu configuration from ~/.multiagent/feishu.json."""
    try:
        if FEISHU_CONFIG_PATH.exists():
            with open(FEISHU_CONFIG_PATH) as f:
                return json.load(f)
    except Exception as e:
        logger.debug("Failed to load Feishu config: %s", e)
    return {}


class FeishuClient:
    """Feishu API client for sending and receiving messages.

    Configuration loaded from ~/.multiagent/feishu.json
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        bot_name: str = "MultiAgent Bot",
    ):
        config = _load_feishu_config()

        self.app_id = app_id or config.get("appId", "") or config.get("app_id", "")
        self.app_secret = app_secret or config.get("appSecret", "") or config.get("app_secret", "")
        self.bot_name = bot_name

        # Feishu API endpoints
        self.base_url = "https://open.feishu.cn"
        self.api_url = f"{self.base_url}/open-apis"

        # Token cache
        self._tenant_access_token: Optional[str] = None
        self._token_expires_at: float = 0

    async def get_tenant_access_token(self) -> str:
        """Get tenant access token, cached until expiry."""
        if self._tenant_access_token and time.time() < self._token_expires_at - 60:
            return self._tenant_access_token

        url = f"{self.api_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                raise Exception(f"Failed to get tenant access token: {data}")

            self._tenant_access_token = data["tenant_access_token"]
            # Token typically expires in 2 hours
            self._token_expires_at = time.time() + data.get("expire", 7200) - 60

            return self._tenant_access_token

    async def send_message(
        self,
        receive_id: str,
        msg_type: str = "text",
        content: str | dict | list = "",
        msg_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send message to Feishu user or chat.

        Args:
            receive_id: User ID (open_id) or Chat ID
            msg_type: Message type (text, post, image, etc.)
            content: Message content
            msg_id: Optional message ID to reply to
        """
        token = await self.get_tenant_access_token()

        # Determine receive_id_type based on format
        if receive_id.startswith("oc_"):
            receive_id_type = "chat_id"
        elif receive_id.startswith("ou_"):
            receive_id_type = "open_id"
        else:
            receive_id_type = "open_id"  # Default

        url = f"{self.api_url}/im/v1/messages"
        params = {"receive_id_type": receive_id_type}

        # Format content based on type
        if msg_type == "text" and isinstance(content, str):
            message_content = json.dumps({"text": content})
        else:
            message_content = json.dumps(content) if isinstance(content, (dict, list)) else content

        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": message_content,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Add reply_to if msg_id provided
        if msg_id:
            payload["reply_to"] = msg_id

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(url, json=payload, params=params, headers=headers)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"Failed to send message: {result}")

            return result.get("data", {})

    async def send_text(
        self,
        receive_id: str,
        text: str,
        msg_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send text message."""
        return await self.send_message(receive_id, "text", text, msg_id)

    async def send_interactive_card(
        self,
        receive_id: str,
        card_content: str,
        msg_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send interactive card message."""
        return await self.send_message(receive_id, "interactive", card_content, msg_id)

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """Get message content by ID."""
        token = await self.get_tenant_access_token()

        url = f"{self.api_url}/im/v1/messages/{message_id}"

        headers = {
            "Authorization": f"Bearer {token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"Failed to get message: {result}")

            return result.get("data", {})

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        """Get chat information."""
        token = await self.get_tenant_access_token()

        url = f"{self.api_url}/im/v1/chats/{chat_id}"

        headers = {
            "Authorization": f"Bearer {token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"Failed to get chat info: {result}")

            return result.get("data", {})

    async def get_user_info(self, user_id: str, user_id_type: str = "open_id") -> dict[str, Any]:
        """Get user information."""
        token = await self.get_tenant_access_token()

        url = f"{self.api_url}/contact/v3/users/{user_id}"
        params = {"user_id_type": user_id_type}

        headers = {
            "Authorization": f"Bearer {token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"Failed to get user info: {result}")

            return result.get("data", {})


def verify_feishu_signature(
    timestamp: str,
    signature: str,
    secret: str,
) -> bool:
    """Verify Feishu event signature.

    Args:
        timestamp: Timestamp from Feishu
        signature: Signature from Feishu
        secret: App secret
    """
    # Sort and concatenate
    string_to_sign = f"{timestamp}{secret}"

    # Calculate HMAC-SHA256
    sign = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(sign).decode("utf-8")

    return expected == signature


def parse_message_content(content: str, msg_type: str) -> str:
    """Parse message content based on message type."""
    try:
        parsed = json.loads(content)
        if msg_type == "text":
            return parsed.get("text", content)
        elif msg_type == "post":
            # Extract text from rich text post
            text_parts = []
            for paragraph in parsed.get("content", []):
                if isinstance(paragraph, list):
                    for element in paragraph:
                        if element.get("tag") == "text":
                            text_parts.append(element.get("text", ""))
                        elif element.get("tag") == "at":
                            text_parts.append(f"@{element.get('user_name', '')}")
            return "\n".join(text_parts) or content
        return content
    except (json.JSONDecodeError, TypeError):
        return content


# Global client instance
_feishu_client: Optional[FeishuClient] = None


def get_feishu_client() -> FeishuClient:
    """Get or create global Feishu client."""
    global _feishu_client
    if _feishu_client is None:
        _feishu_client = FeishuClient()
    return _feishu_client


def reset_feishu_client() -> None:
    """Reset the global Feishu client."""
    global _feishu_client
    _feishu_client = None


async def process_feishu_message(
    event_data: dict[str, Any],
    pipeline: Any,
) -> str:
    """Process incoming Feishu message through the agent pipeline.

    Args:
        event_data: Feishu event data containing message info
        pipeline: CollaborationPipeline instance

    Returns:
        Response text to send back to Feishu
    """
    from pipelines.collaboration_pipeline import CollaborationPipeline

    # Extract message info
    event = event_data.get("event", {})
    message = event.get("message", {})
    sender = event.get("sender", {})

    msg_type = message.get("message_type", "text")
    chat_id = message.get("chat_id", "")
    _msg_id = message.get("message_id", "")
    content = message.get("content", "")

    # Parse the actual message content
    text = parse_message_content(content, msg_type)

    # Get sender info
    sender_id = sender.get("sender_id", {}).get("open_id", "")
    _sender_type = sender.get("sender_type", "")

    logger.info(f"Feishu message from {sender_id} in {chat_id}: {text[:100]}")

    try:
        # Call the pipeline to process the message
        if pipeline is None:
            pipeline = CollaborationPipeline(enable_tracing=False)

        result = pipeline.invoke(text)

        # Extract the response
        final_response = result.get("final_response", "处理中...")
        return final_response

    except Exception as e:
        logger.error(f"Error processing Feishu message: {e}")
        return f"抱歉，处理消息时出错: {str(e)}"


# ============================================================================
# Feishu WebSocket Client (Event-driven mode)
# ============================================================================


class FeishuWSClient:
    """Feishu WebSocket client using lark-oapi SDK.

    This connects TO Feishu server (reverse connection), no public URL needed.
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        event_handler: Optional[Any] = None,
    ):
        config = _load_feishu_config()

        self.app_id = app_id or config.get("appId", "") or config.get("app_id", "")
        self.app_secret = app_secret or config.get("appSecret", "") or config.get("app_secret", "")
        self.encrypt_key = config.get("encryptKey", "")
        self.verification_token = config.get("verificationToken", "")
        self.domain = config.get("domain", "feishu")

        # The actual WS client
        self._ws_client: Optional[Any] = None
        self._event_handler = event_handler
        self._running = False

    def _create_event_handler(self) -> Any:
        """Create event handler for dispatching Feishu events."""
        from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
        from lark_oapi.core.enum import LogLevel

        builder = EventDispatcherHandler.builder(
            encrypt_key=self.encrypt_key or None,
            verification_token=self.verification_token or None,
            level=LogLevel.INFO,
        )

        # Register message receive handler
        builder.register_p2_im_message_receive_v1(self._handle_message)

        return builder.build()

    def _handle_message(self, data: Any) -> None:
        """Handle incoming message event from Feishu.

        Args:
            data: P2ImMessageReceiveV1 object from lark-oapi SDK
        """
        try:
            # Data is a P2ImMessageReceiveV1 object with:
            # - event.message (EventMessage)
            # - event.sender (EventSender)
            message = data.event.message if hasattr(data.event, 'message') else None
            sender = data.event.sender if hasattr(data.event, 'sender') else None

            if message is None or sender is None:
                logger.warning(f"Invalid message event structure: {data}")
                return

            msg_type = message.message_type if hasattr(message, 'message_type') else "text"
            chat_id = message.chat_id if hasattr(message, 'chat_id') else ""
            msg_id = message.message_id if hasattr(message, 'message_id') else ""
            content_str = message.content if hasattr(message, 'content') else "{}"
            chat_type = message.chat_type if hasattr(message, 'chat_type') else "p2p"

            # Only process text messages in p2p (direct) chats
            if chat_type != "p2p":
                logger.info(f"Ignoring group message in chat {chat_id}")
                return

            # Parse message content
            text = parse_message_content(content_str, msg_type)
            if not text:
                logger.info("Empty message content, ignoring")
                return

            # Get sender info
            sender_id = ""
            if hasattr(sender, 'sender_id') and sender.sender_id:
                sender_id = sender.sender_id.open_id if hasattr(sender.sender_id, 'open_id') else str(sender.sender_id)

            logger.info(f"Feishu WS message from {sender_id} in {chat_id}: {text[:100]}")

            # Call the event handler if set
            if self._event_handler:
                self._event_handler(
                    text=text,
                    sender_id=sender_id,
                    chat_id=chat_id,
                    msg_id=msg_id,
                    event=data.event,
                )

        except Exception as e:
            logger.error(f"Error handling Feishu message: {e}")

    def start(self, event_handler: Optional[Callable] = None) -> None:
        """Start the WebSocket client.

        Args:
            event_handler: Callback function(text, sender_id, chat_id, msg_id, event)
        """
        if self._running:
            logger.warning("Feishu WS client already running")
            return

        if not self.app_id or not self.app_secret:
            raise ValueError("Feishu app_id and app_secret are required")

        self._event_handler = event_handler

        try:
            from lark_oapi.ws import Client
            from lark_oapi.core.enum import LogLevel

            # Create event handler
            event_dispatcher = self._create_event_handler()

            # Create WebSocket client
            self._ws_client = Client(
                app_id=self.app_id,
                app_secret=self.app_secret,
                log_level=LogLevel.INFO,
                event_handler=event_dispatcher,
                domain=self.domain if self.domain != "feishu" else "https://open.feishu.cn",
                auto_reconnect=True,
            )

            # Start the client (this blocks)
            self._running = True
            logger.info(f"Starting Feishu WS client for app {self.app_id}")
            self._ws_client.start()

        except ImportError as e:
            logger.error(f"Failed to import lark-oapi: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to start Feishu WS client: {e}")
            self._running = False
            raise

    def stop(self) -> None:
        """Stop the WebSocket client."""
        self._running = False
        # The WS client doesn't have a clean stop method,
        # so we just set the flag
        logger.info("Feishu WS client stop requested")


# Global WS client instance
_feishu_ws_client: Optional[FeishuWSClient] = None


def get_feishu_ws_client() -> FeishuWSClient:
    """Get or create global Feishu WebSocket client."""
    global _feishu_ws_client
    if _feishu_ws_client is None:
        _feishu_ws_client = FeishuWSClient()
    return _feishu_ws_client


def start_feishu_ws_client(
    event_handler: Callable,
    blocking: bool = True,
) -> Optional[threading.Thread]:
    """Start Feishu WebSocket client in a thread.

    Args:
        event_handler: Callback function(text, sender_id, chat_id, msg_id, event)
        blocking: If True, blocks current thread. If False, runs in background.

    Returns:
        Thread object if blocking=False, None otherwise
    """
    ws_client = get_feishu_ws_client()

    if blocking:
        ws_client.start(event_handler=event_handler)
        return None
    else:
        thread = threading.Thread(
            target=ws_client.start,
            args=(event_handler,),
            daemon=True,
        )
        thread.start()
        logger.info("Feishu WS client started in background thread")
        return thread
