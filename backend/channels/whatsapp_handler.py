"""
WhatsApp Handler for NovaSaaS Customer Success System

Handles incoming/outgoing WhatsApp messages via Twilio.
"""
import base64
import hashlib
import hmac
import re
import structlog
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from fastapi import Request, HTTPException

logger = structlog.get_logger()


class WhatsAppHandler:
    """
    Handler for WhatsApp integration using Twilio SDK.
    
    Supports:
    - Webhook validation for Twilio signatures
    - Message normalization
    - Response formatting with 1600 char limit
    - Media message handling
    """
    
    MAX_MESSAGE_LENGTH = 1600
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        whatsapp_number: str,
        webhook_url: str,
    ):
        """
        Initialize WhatsApp handler.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            whatsapp_number: WhatsApp-enabled Twilio number (e.g., "whatsapp:+14155238886")
            webhook_url: Public URL for receiving webhooks
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.whatsapp_number = whatsapp_number
        self.webhook_url = webhook_url
        
        self._client = None
        
        logger.info(
            "WhatsAppHandler initialized",
            account_sid=account_sid[:8] + "...",
            whatsapp_number=whatsapp_number
        )
    
    @property
    def client(self):
        """Get or create Twilio client"""
        if self._client is None:
            from twilio.rest import Client
            self._client = Client(self.account_sid, self.auth_token)
        return self._client
    
    def validate_webhook(self, request: Request) -> bool:
        """
        Validate Twilio webhook signature.
        
        Args:
            request: FastAPI request object
        
        Returns:
            True if signature is valid, False otherwise
        """
        # Get Twilio signature from headers
        twilio_signature = request.headers.get('X-Twilio-Signature', '')
        
        if not twilio_signature:
            logger.warning("Missing Twilio signature")
            return False
        
        # Get request body
        body = request.query_params
        body_string = urlencode(sorted(body.items()))
        
        # Compute expected signature
        signature = hmac.new(
            self.auth_token.encode('utf-8'),
            body_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        expected_signature = base64.b64encode(signature).decode('utf-8')
        
        # Compare signatures
        is_valid = hmac.compare_digest(twilio_signature, expected_signature)
        
        if not is_valid:
            logger.warning("Invalid Twilio signature")
        
        return is_valid
    
    def process_webhook(self, form_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process incoming WhatsApp webhook.
        
        Args:
            form_data: Parsed form data from Twilio webhook
        
        Returns:
            Normalized message dict with channel='whatsapp', or None if not a message
        """
        logger.info("Processing WhatsApp webhook", from_number=form_data.get('From'))
        
        # Check if this is an incoming message
        message_sid = form_data.get('MessageSid')
        if not message_sid:
            logger.debug("Not a message webhook", event=form_data.get('EventType'))
            return None
        
        # Extract message data
        from_number = form_data.get('From', '')
        to_number = form_data.get('To', '')
        body = form_data.get('Body', '')
        num_media = int(form_data.get('NumMedia', 0))
        
        # Normalize phone numbers
        from_phone = self._normalize_phone(from_number)
        to_phone = self._normalize_phone(to_number)
        
        # Handle media attachments
        media = []
        for i in range(num_media):
            media_url = form_data.get(f'MediaUrl{i}', '')
            media_type = form_data.get(f'MediaContentType{i}', '')
            if media_url:
                media.append({
                    'url': media_url,
                    'type': media_type,
                })
        
        # Build normalized message
        normalized = {
            'channel': 'whatsapp',
            'customer_email': None,
            'customer_phone': from_phone,
            'customer_name': self._extract_name_from_phone(from_phone),
            'content': body,
            'subject': None,
            'channel_message_id': message_sid,
            'channel_thread_id': form_data.get('From', ''),  # Use sender as thread
            'received_at': datetime.utcnow().isoformat(),
            'metadata': {
                'from_number': from_number,
                'to_number': to_number,
                'num_media': num_media,
                'media': media,
                'message_status': form_data.get('MessageStatus', 'received'),
                'direction': form_data.get('Direction', 'inbound'),
            }
        }
        
        logger.info(
            "WhatsApp message processed",
            from_phone=from_phone,
            message_length=len(body),
            media_count=num_media
        )
        
        return normalized
    
    def send_message(self, to_phone: str, body: str) -> Dict[str, Any]:
        """
        Send a WhatsApp message.
        
        Args:
            to_phone: Recipient phone number
            body: Message body text
        
        Returns:
            Dict with message SID and status
        """
        try:
            # Format message for WhatsApp (split if needed)
            formatted_body = self.format_response(body)
            
            message = self.client.messages.create(
                from_=self.whatsapp_number,
                body=formatted_body,
                to=f"whatsapp:{to_phone}"
            )
            
            logger.info(
                "WhatsApp message sent",
                to=to_phone,
                sid=message.sid
            )
            
            return {
                'message_sid': message.sid,
                'status': message.status,
                'sent_at': datetime.utcnow().isoformat(),
                'body_length': len(formatted_body),
            }
            
        except Exception as error:
            logger.error("Failed to send WhatsApp message", to=to_phone, error=str(error))
            return {
                'status': 'error',
                'error': str(error),
            }
    
    def send_media_message(
        self,
        to_phone: str,
        media_url: str,
        caption: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message with media.
        
        Args:
            to_phone: Recipient phone number
            media_url: URL of media to send
            caption: Optional caption for the media
        
        Returns:
            Dict with message SID and status
        """
        try:
            message_kwargs = {
                'from_': self.whatsapp_number,
                'to': f"whatsapp:{to_phone}",
                'media_url': media_url,
            }
            
            if caption:
                message_kwargs['body'] = self.format_response(caption)
            
            message = self.client.messages.create(**message_kwargs)
            
            logger.info(
                "WhatsApp media message sent",
                to=to_phone,
                sid=message.sid,
                media_url=media_url
            )
            
            return {
                'message_sid': message.sid,
                'status': message.status,
                'sent_at': datetime.utcnow().isoformat(),
            }
            
        except Exception as error:
            logger.error("Failed to send WhatsApp media message", error=str(error))
            return {
                'status': 'error',
                'error': str(error),
            }
    
    def format_response(self, text: str) -> str:
        """
        Format response text for WhatsApp.
        
        Splits at 1600 characters on sentence boundaries.
        WhatsApp has a 1600 character limit per message.
        
        Args:
            text: Original text
        
        Returns:
            Formatted text (truncated at sentence boundary if needed)
        """
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return text
        
        # Find the last sentence boundary before the limit
        # Look for ., !, ?, or newline
        truncate_at = self.MAX_MESSAGE_LENGTH
        
        # Try to find sentence boundary
        for punct in ['.\n', '. ', '!\n', '! ', '?\n', '? ']:
            last_pos = text.rfind(punct, 0, self.MAX_MESSAGE_LENGTH)
            if last_pos != -1:
                truncate_at = last_pos + (2 if punct.endswith(' ') or punct.endswith('\n') else 1)
                break
        
        # If no boundary found, hard truncate
        truncated = text[:truncate_at].rstrip()
        
        # Add ellipsis if we truncated
        if len(truncated) < len(text):
            truncated += "..."
        
        logger.info(
            "Message truncated for WhatsApp",
            original_length=len(text),
            truncated_length=len(truncated)
        )
        
        return truncated
    
    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get the status of a sent message.
        
        Args:
            message_sid: Twilio message SID
        
        Returns:
            Dict with message status and details
        """
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                'message_sid': message.sid,
                'status': message.status,
                'to': message.to,
                'from': message.from_,
                'body': message.body,
                'date_sent': message.date_sent.isoformat() if message.date_sent else None,
                'date_updated': message.date_updated.isoformat() if message.date_updated else None,
            }
            
        except Exception as error:
            logger.error("Failed to get message status", sid=message_sid, error=str(error))
            return {
                'status': 'error',
                'error': str(error),
            }
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone number by removing 'whatsapp:' prefix"""
        if phone.startswith('whatsapp:'):
            return phone[9:]
        return phone
    
    @staticmethod
    def _extract_name_from_phone(phone: str) -> Optional[str]:
        """
        Extract a name-like identifier from phone number.
        
        In production, this would look up the contact in a database.
        For now, we return None as we don't have name info from WhatsApp alone.
        """
        return None
    
    def get_conversation_history(
        self,
        phone_number: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a phone number.
        
        Note: Twilio doesn't provide a direct way to fetch message history.
        This would typically be stored in your own database.
        
        Args:
            phone_number: Phone number to get history for
            limit: Maximum messages to return
        
        Returns:
            List of message dicts (from local storage)
        """
        logger.warning(
            "get_conversation_history called - implement local storage retrieval",
            phone_number=phone_number
        )
        return []


# =============================================================================
# FastAPI Webhook Endpoint Helper
# =============================================================================

def create_whatsapp_webhook_handler(handler: WhatsAppHandler):
    """
    Create a FastAPI route handler for WhatsApp webhooks.
    
    Usage:
        app.post("/webhooks/whatsapp")(create_whatsapp_webhook_handler(whatsapp_handler))
    """
    from fastapi import Response
    
    async def webhook_handler(request: Request):
        # Get form data
        form_data = await request.form()
        form_dict = dict(form_data)
        
        # Validate signature (optional in development)
        # if not handler.validate_webhook(request):
        #     raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Process webhook
        normalized = handler.process_webhook(form_dict)
        
        if normalized:
            # Here you would typically:
            # 1. Store the message in your database
            # 2. Trigger the AI agent to process it
            # 3. Send a response
            logger.info("Webhook processed", normalized=normalized)
        
        # Twilio expects a 200 response
        return Response(status_code=200)
    
    return webhook_handler


# =============================================================================
# Factory function
# =============================================================================

def create_whatsapp_handler(
    account_sid: str,
    auth_token: str,
    whatsapp_number: str,
    webhook_url: str,
) -> WhatsAppHandler:
    """
    Create a WhatsApp handler instance.
    
    Args:
        account_sid: Twilio account SID
        auth_token: Twilio auth token
        whatsapp_number: WhatsApp-enabled Twilio number
        webhook_url: Public webhook URL
    
    Returns:
        Configured WhatsAppHandler instance
    """
    return WhatsAppHandler(
        account_sid=account_sid,
        auth_token=auth_token,
        whatsapp_number=whatsapp_number,
        webhook_url=webhook_url,
    )
