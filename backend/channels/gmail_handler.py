"""
Gmail Handler for NovaSaaS Customer Success System

Handles incoming emails via Gmail API push notifications.
"""
import base64
import re
import structlog
from datetime import datetime
from email.utils import parseaddr
from typing import Optional, Dict, Any, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = structlog.get_logger()


class GmailHandler:
    """
    Handler for Gmail integration using Google API client.
    
    Supports:
    - OAuth2 authentication with service account
    - Push notifications via Pub/Sub
    - Email parsing and normalization
    - Reply sending with thread tracking
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
    ]
    
    def __init__(
        self,
        service_account_file: str,
        delegated_user: str,
        project_id: str,
        topic_name: str,
    ):
        """
        Initialize Gmail handler.
        
        Args:
            service_account_file: Path to service account JSON key
            delegated_user: Email of user to impersonate (domain-wide delegation)
            project_id: GCP project ID for Pub/Sub
            topic_name: Pub/Sub topic name for push notifications
        """
        self.service_account_file = service_account_file
        self.delegated_user = delegated_user
        self.project_id = project_id
        self.topic_name = topic_name
        
        self._credentials = None
        self._service = None
        
        logger.info(
            "GmailHandler initialized",
            project_id=project_id,
            topic_name=topic_name
        )
    
    @property
    def credentials(self):
        """Get or create OAuth2 credentials"""
        if self._credentials is None:
            self._credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=self.SCOPES,
                subject=self.delegated_user
            )
        return self._credentials
    
    @property
    def service(self):
        """Get or create Gmail API service"""
        if self._service is None:
            self._service = build('gmail', 'v1', credentials=self.credentials)
        return self._service
    
    def setup_push_notifications(self, topic_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Set up push notifications for the Gmail inbox.
        
        Args:
            topic_name: Optional topic name (uses default if not provided)
        
        Returns:
            Dict with history_id and expiration timestamp
        """
        topic = topic_name or self.topic_name
        full_topic_name = f"projects/{self.project_id}/topics/{topic}"
        
        try:
            response = self.service.users().watch(
                userId='me',
                body={
                    'labelIds': ['INBOX', 'UNREAD'],
                    'topicName': full_topic_name,
                    'labelFilterBehavior': 'INCLUDE',
                }
            ).execute()
            
            logger.info(
                "Push notifications set up",
                history_id=response.get('historyId'),
                expiration=response.get('expiration')
            )
            
            return {
                'history_id': response.get('historyId'),
                'expiration': response.get('expiration'),
                'topic_name': topic,
            }
            
        except HttpError as error:
            logger.error("Failed to set up push notifications", error=str(error))
            raise
    
    def stop_push_notifications(self) -> None:
        """Stop push notifications for the Gmail inbox"""
        try:
            self.service.users().stop(userId='me').execute()
            logger.info("Push notifications stopped")
        except HttpError as error:
            logger.error("Failed to stop push notifications", error=str(error))
    
    def process_notification(self, pubsub_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a Pub/Sub notification and extract emails.
        
        Args:
            pubsub_message: Decoded Pub/Sub message data
        
        Returns:
            List of normalized email message dicts
        """
        logger.info("Processing Gmail notification", message=pubsub_message)
        
        history_id = pubsub_message.get('historyId')
        messages_added = []
        
        try:
            # Get history records
            history = self.service.users().history().list(
                userId='me',
                startHistoryId=history_id,
                historyTypes='messageAdded',
            ).execute()
            
            history_records = history.get('history', [])
            
            for record in history_records:
                messages = record.get('messagesAdded', [])
                for msg in messages:
                    message_data = msg.get('message', {})
                    message_id = message_data.get('id')
                    
                    if message_id:
                        normalized = self.get_message(message_id)
                        if normalized:
                            messages_added.append(normalized)
            
            logger.info("Notification processed", messages_count=len(messages_added))
            return messages_added
            
        except HttpError as error:
            logger.error("Failed to process notification", error=str(error))
            return []
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get and parse a Gmail message.
        
        Args:
            message_id: Gmail message ID
        
        Returns:
            Normalized message dict with channel='email'
        """
        try:
            raw_message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full',
                metadataHeaders=['From', 'To', 'Subject', 'References', 'In-Reply-To']
            ).execute()
            
            # Parse headers
            headers = raw_message.get('payload', {}).get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            from_header = header_dict.get('From', '')
            to_header = header_dict.get('To', '')
            subject = header_dict.get('Subject', '')
            thread_id = raw_message.get('threadId', '')
            
            # Extract email addresses
            from_email = self.extract_email(from_header)
            from_name = self.extract_name(from_header)
            
            # Get message body
            body = self._extract_body(raw_message)
            
            # Get attachments info
            attachments = self._get_attachments_info(raw_message)
            
            # Parse references for threading
            references = header_dict.get('References', '')
            in_reply_to = header_dict.get('In-Reply-To', '')
            
            normalized = {
                'channel': 'email',
                'customer_email': from_email,
                'customer_name': from_name,
                'customer_phone': None,
                'content': body,
                'subject': subject,
                'channel_message_id': message_id,
                'channel_thread_id': thread_id,
                'received_at': datetime.utcnow().isoformat(),
                'metadata': {
                    'to': to_header,
                    'from_raw': from_header,
                    'references': references,
                    'in_reply_to': in_reply_to,
                    'attachments': attachments,
                    'label_ids': raw_message.get('labelIds', []),
                }
            }
            
            logger.info("Message retrieved", message_id=message_id)
            return normalized
            
        except HttpError as error:
            logger.error("Failed to get message", message_id=message_id, error=str(error))
            return None
    
    def _extract_body(self, raw_message: Dict[str, Any]) -> str:
        """Extract the plain text body from a Gmail message"""
        payload = raw_message.get('payload', {})
        parts = payload.get('parts', [])
        body_data = payload.get('body', {})
        
        # Try to find plain text part
        def find_text_part(parts_list):
            for part in parts_list:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    part_body = part.get('body', {})
                    data = part_body.get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                # Recurse into multipart
                if mime_type.startswith('multipart/') and 'parts' in part:
                    result = find_text_part(part['parts'])
                    if result:
                        return result
            return None
        
        # Check parts first
        if parts:
            text_body = find_text_part(parts)
            if text_body:
                return text_body
        
        # Fall back to main body
        if body_data.get('data'):
            try:
                return base64.urlsafe_b64decode(body_data['data']).decode('utf-8', errors='replace')
            except Exception:
                pass
        
        # If no plain text, try HTML
        def find_html_part(parts_list):
            for part in parts_list:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/html':
                    part_body = part.get('body', {})
                    data = part_body.get('data', '')
                    if data:
                        html = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                        # Strip HTML tags
                        return re.sub('<[^<]+?>', '', html)
                if mime_type.startswith('multipart/') and 'parts' in part:
                    result = find_html_part(part['parts'])
                    if result:
                        return result
            return None
        
        if parts:
            html_body = find_html_part(parts)
            if html_body:
                return html_body
        
        return "[No text content]"
    
    def _get_attachments_info(self, raw_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get attachment metadata from message"""
        attachments = []
        payload = raw_message.get('payload', {})
        parts = payload.get('parts', [])
        
        def find_attachments(parts_list):
            for part in parts_list:
                mime_type = part.get('mimeType', '')
                if not mime_type.startswith('multipart/'):
                    filename = part.get('filename', '')
                    if filename:
                        body = part.get('body', {})
                        attachments.append({
                            'filename': filename,
                            'mime_type': mime_type,
                            'size': body.get('size', 0),
                            'attachment_id': body.get('attachmentId', ''),
                        })
                if mime_type.startswith('multipart/') and 'parts' in part:
                    find_attachments(part['parts'])
        
        find_attachments(parts)
        return attachments
    
    def send_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email reply.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            thread_id: Optional thread ID for threading
        
        Returns:
            Dict with message_id and status
        """
        import base64
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['to'] = to_email
            message['subject'] = subject
            
            # Add plain text and HTML versions
            message.attach(MIMEText(body, 'plain', 'utf-8'))
            message.attach(MIMEText(
                f'<html><body>{body.replace(chr(10), "<br>")}</body></html>',
                'html',
                'utf-8'
            ))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send or reply
            if thread_id:
                # Reply to existing thread
                response = self.service.users().messages().send(
                    userId='me',
                    body={
                        'raw': raw_message,
                        'threadId': thread_id,
                    }
                ).execute()
            else:
                # New message
                response = self.service.users().messages().send(
                    userId='me',
                    body={'raw': raw_message}
                ).execute()
            
            logger.info(
                "Email sent",
                to=to_email,
                message_id=response.get('id'),
                thread_id=response.get('threadId')
            )
            
            return {
                'message_id': response.get('id'),
                'thread_id': response.get('threadId'),
                'status': 'sent',
                'sent_at': datetime.utcnow().isoformat(),
            }
            
        except HttpError as error:
            logger.error("Failed to send email", to=to_email, error=str(error))
            return {
                'status': 'error',
                'error': str(error),
            }
    
    @staticmethod
    def extract_email(email_header: str) -> Optional[str]:
        """
        Extract email address from "Name <email>" format.
        
        Args:
            email_header: Email header value (e.g., "John Doe <john@example.com>")
        
        Returns:
            Email address or None
        """
        _, email = parseaddr(email_header)
        return email if email else None
    
    @staticmethod
    def extract_name(email_header: str) -> Optional[str]:
        """
        Extract name from "Name <email>" format.
        
        Args:
            email_header: Email header value
        
        Returns:
            Name or None
        """
        name, _ = parseaddr(email_header)
        return name if name else None
    
    def refresh_messages(self, query: str = 'is:unread', max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Refresh and fetch unread messages.
        
        Args:
            query: Gmail search query
            max_results: Maximum messages to fetch
        
        Returns:
            List of normalized message dicts
        """
        try:
            response = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = response.get('messages', [])
            normalized = []
            
            for msg in messages:
                message_id = msg['id']
                normalized_msg = self.get_message(message_id)
                if normalized_msg:
                    normalized.append(normalized_msg)
            
            return normalized
            
        except HttpError as error:
            logger.error("Failed to refresh messages", error=str(error))
            return []


# =============================================================================
# Factory function
# =============================================================================

def create_gmail_handler(
    service_account_file: str,
    delegated_user: str,
    project_id: str,
    topic_name: str,
) -> GmailHandler:
    """
    Create a Gmail handler instance.
    
    Args:
        service_account_file: Path to service account JSON
        delegated_user: Email to impersonate
        project_id: GCP project ID
        topic_name: Pub/Sub topic name
    
    Returns:
        Configured GmailHandler instance
    """
    return GmailHandler(
        service_account_file=service_account_file,
        delegated_user=delegated_user,
        project_id=project_id,
        topic_name=topic_name,
    )
