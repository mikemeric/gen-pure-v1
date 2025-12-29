"""
RabbitMQ consumer with robustness features

Provides reliable message consumption with:
- Automatic reconnection
- Message retry with exponential backoff
- Dead letter queue for failed messages
- Circuit breaker integration
- Graceful shutdown
"""
import time
import json
import threading
from typing import Callable, Optional, Dict, Any
from datetime import datetime

try:
    import pika
    PIKA_AVAILABLE = True
except ImportError:
    PIKA_AVAILABLE = False
    print("⚠️  pika not installed. RabbitMQ features disabled.")

from infrastructure.queue.circuit_breaker import CircuitBreaker, CircuitBreakerError


class RabbitMQConsumer:
    """
    Robust RabbitMQ consumer
    
    Features:
    - Auto reconnect on connection loss
    - Message retry with exponential backoff
    - Dead letter queue for failed messages
    - Circuit breaker protection
    - Graceful shutdown
    - Message acknowledgment
    """
    
    def __init__(
        self,
        rabbitmq_url: str,
        queue_name: str,
        callback: Callable[[Dict[str, Any]], None],
        max_retries: int = 3,
        retry_delay: int = 5,
        prefetch_count: int = 1,
        use_circuit_breaker: bool = True
    ):
        """
        Initialize RabbitMQ consumer
        
        Args:
            rabbitmq_url: RabbitMQ connection URL
                         Format: amqp://user:pass@host:port/vhost
            queue_name: Queue to consume from
            callback: Function to process messages
            max_retries: Maximum retry attempts per message
            retry_delay: Initial retry delay in seconds
            prefetch_count: Number of messages to prefetch
            use_circuit_breaker: Enable circuit breaker protection
        
        Example:
            >>> def process_message(message):
            ...     print(f"Processing: {message}")
            >>> 
            >>> consumer = RabbitMQConsumer(
            ...     "amqp://guest:guest@localhost:5672/",
            ...     "detection_queue",
            ...     process_message
            ... )
        """
        if not PIKA_AVAILABLE:
            raise ImportError("pika library not installed. Install with: pip install pika")
        
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.callback = callback
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.prefetch_count = prefetch_count
        
        # Connection
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.channel.Channel] = None
        self._consuming = False
        self._reconnect_delay = 5
        
        # Circuit breaker
        self._circuit_breaker: Optional[CircuitBreaker] = None
        if use_circuit_breaker:
            self._circuit_breaker = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60
            )
        
        # Threading
        self._consumer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Statistics
        self._messages_processed = 0
        self._messages_failed = 0
        self._messages_retried = 0
    
    def _connect(self) -> bool:
        """
        Establish connection to RabbitMQ
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            # Create connection
            parameters = pika.URLParameters(self.rabbitmq_url)
            parameters.heartbeat = 60
            parameters.blocked_connection_timeout = 300
            
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            
            # Declare queue
            self._channel.queue_declare(
                queue=self.queue_name,
                durable=True,  # Survive broker restart
                arguments={
                    'x-message-ttl': 86400000,  # 24 hours
                    'x-max-length': 10000,  # Max queue size
                }
            )
            
            # Declare dead letter queue
            dlq_name = f"{self.queue_name}_dlq"
            self._channel.queue_declare(
                queue=dlq_name,
                durable=True
            )
            
            # Set QoS (prefetch)
            self._channel.basic_qos(prefetch_count=self.prefetch_count)
            
            print(f"✅ Connected to RabbitMQ: {self.queue_name}")
            return True
        
        except Exception as e:
            print(f"❌ Failed to connect to RabbitMQ: {e}")
            return False
    
    def _on_message(
        self,
        channel: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes
    ):
        """
        Handle incoming message
        
        Args:
            channel: Channel
            method: Delivery method
            properties: Message properties
            body: Message body
        """
        try:
            # Parse message
            message = json.loads(body.decode())
            
            # Get retry count
            headers = properties.headers or {}
            retry_count = headers.get('x-retry-count', 0)
            
            # Process message
            self._process_message_with_retry(message, retry_count, channel, method.delivery_tag)
        
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON message: {e}")
            # Reject invalid message
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        except Exception as e:
            print(f"❌ Message processing error: {e}")
            # Reject with requeue
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def _process_message_with_retry(
        self,
        message: Dict[str, Any],
        retry_count: int,
        channel: pika.channel.Channel,
        delivery_tag: int
    ):
        """
        Process message with retry logic
        
        Args:
            message: Message data
            retry_count: Current retry count
            channel: Channel
            delivery_tag: Delivery tag for acknowledgment
        """
        try:
            # Check circuit breaker
            if self._circuit_breaker:
                self._circuit_breaker.call(self.callback, message)
            else:
                self.callback(message)
            
            # Success - acknowledge
            channel.basic_ack(delivery_tag=delivery_tag)
            self._messages_processed += 1
        
        except CircuitBreakerError:
            # Circuit breaker open - requeue for later
            print(f"⚠️  Circuit breaker OPEN - requeuing message")
            channel.basic_nack(delivery_tag=delivery_tag, requeue=True)
        
        except Exception as e:
            print(f"❌ Message processing failed: {e}")
            self._messages_failed += 1
            
            # Check if we should retry
            if retry_count < self.max_retries:
                self._retry_message(message, retry_count, channel, delivery_tag)
            else:
                # Max retries exceeded - send to DLQ
                self._send_to_dlq(message, retry_count, str(e), channel, delivery_tag)
    
    def _retry_message(
        self,
        message: Dict[str, Any],
        retry_count: int,
        channel: pika.channel.Channel,
        delivery_tag: int
    ):
        """
        Retry failed message with exponential backoff
        
        Args:
            message: Message data
            retry_count: Current retry count
            channel: Channel
            delivery_tag: Delivery tag
        """
        # Calculate delay (exponential backoff)
        delay = self.retry_delay * (2 ** retry_count)
        
        print(f"🔄 Retrying message (attempt {retry_count + 1}/{self.max_retries}) after {delay}s")
        
        # Republish with updated retry count
        properties = pika.BasicProperties(
            delivery_mode=2,  # Persistent
            headers={
                'x-retry-count': retry_count + 1,
                'x-original-timestamp': datetime.now().isoformat()
            }
        )
        
        # Wait before retry
        time.sleep(delay)
        
        channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            body=json.dumps(message),
            properties=properties
        )
        
        # Acknowledge original message
        channel.basic_ack(delivery_tag=delivery_tag)
        self._messages_retried += 1
    
    def _send_to_dlq(
        self,
        message: Dict[str, Any],
        retry_count: int,
        error: str,
        channel: pika.channel.Channel,
        delivery_tag: int
    ):
        """
        Send message to dead letter queue
        
        Args:
            message: Message data
            retry_count: Retry count
            error: Error message
            channel: Channel
            delivery_tag: Delivery tag
        """
        dlq_name = f"{self.queue_name}_dlq"
        
        print(f"💀 Sending to DLQ after {retry_count} retries: {error}")
        
        # Add metadata
        dlq_message = {
            'original_message': message,
            'retry_count': retry_count,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        # Publish to DLQ
        channel.basic_publish(
            exchange='',
            routing_key=dlq_name,
            body=json.dumps(dlq_message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        # Acknowledge original message
        channel.basic_ack(delivery_tag=delivery_tag)
    
    def start(self):
        """Start consuming messages in background thread"""
        if self._consuming:
            print("⚠️  Consumer already running")
            return
        
        self._stop_event.clear()
        self._consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._consumer_thread.start()
        print(f"▶️  Consumer started for queue: {self.queue_name}")
    
    def _consume_loop(self):
        """Main consumption loop with auto-reconnect"""
        while not self._stop_event.is_set():
            try:
                # Connect if not connected
                if not self._connection or self._connection.is_closed:
                    if not self._connect():
                        time.sleep(self._reconnect_delay)
                        continue
                
                # Start consuming
                self._consuming = True
                self._channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._on_message,
                    auto_ack=False
                )
                
                print(f"👂 Listening for messages on: {self.queue_name}")
                self._channel.start_consuming()
            
            except KeyboardInterrupt:
                break
            
            except Exception as e:
                print(f"❌ Consumer error: {e}")
                self._consuming = False
                
                # Cleanup
                try:
                    if self._channel:
                        self._channel.stop_consuming()
                    if self._connection:
                        self._connection.close()
                except:
                    pass
                
                # Wait before reconnect
                if not self._stop_event.is_set():
                    print(f"🔄 Reconnecting in {self._reconnect_delay}s...")
                    time.sleep(self._reconnect_delay)
    
    def stop(self):
        """Stop consuming messages gracefully"""
        print(f"⏹️  Stopping consumer: {self.queue_name}")
        self._stop_event.set()
        
        try:
            if self._channel and self._consuming:
                self._channel.stop_consuming()
        except:
            pass
        
        try:
            if self._connection:
                self._connection.close()
        except:
            pass
        
        if self._consumer_thread:
            self._consumer_thread.join(timeout=5)
        
        self._consuming = False
        print(f"✅ Consumer stopped")
    
    def get_stats(self) -> dict:
        """
        Get consumer statistics
        
        Returns:
            dict: Statistics including processed, failed, retried counts
        """
        stats = {
            "queue": self.queue_name,
            "consuming": self._consuming,
            "messages_processed": self._messages_processed,
            "messages_failed": self._messages_failed,
            "messages_retried": self._messages_retried,
            "max_retries": self.max_retries
        }
        
        # Add circuit breaker stats
        if self._circuit_breaker:
            stats["circuit_breaker"] = self._circuit_breaker.get_stats()
        
        return stats
