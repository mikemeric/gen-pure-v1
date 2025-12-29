"""
IP Utilities - Real IP extraction behind proxies

Handles X-Forwarded-For and X-Real-IP headers for proper rate limiting
behind reverse proxies (NGINX, CloudFlare, etc.)
"""
from fastapi import Request
from typing import Optional


def get_real_client_ip(request: Request) -> str:
    """
    Extract real client IP address behind reverse proxy
    
    Handles common proxy headers:
    - X-Forwarded-For (standard, multiple proxies)
    - X-Real-IP (NGINX)
    - Direct connection (no proxy)
    
    Args:
        request: FastAPI Request object
    
    Returns:
        str: Client IP address
    
    Security:
        - Validates IP format
        - Takes first IP from X-Forwarded-For (client, not proxies)
        - Fallback to direct connection if no headers
    
    Example:
        >>> from fastapi import Request
        >>> ip = get_real_client_ip(request)
        >>> rate_limiter.check(f"login:{ip}")
    """
    # 1. Check X-Forwarded-For (standard header)
    # Format: "client_ip, proxy1_ip, proxy2_ip"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (real client)
        client_ip = forwarded_for.split(",")[0].strip()
        if _is_valid_ip(client_ip):
            return client_ip
    
    # 2. Check X-Real-IP (NGINX specific)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        if _is_valid_ip(real_ip):
            return real_ip
    
    # 3. Fallback to direct connection
    if request.client:
        return request.client.host
    
    # 4. Ultimate fallback (should never happen)
    return "unknown"


def _is_valid_ip(ip: str) -> bool:
    """
    Validate IP address format
    
    Args:
        ip: IP address string
    
    Returns:
        bool: True if valid IPv4 or IPv6
    """
    import ipaddress
    
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_private_ip(ip: str) -> bool:
    """
    Check if IP is private/internal
    
    Args:
        ip: IP address string
    
    Returns:
        bool: True if private IP (RFC 1918)
    
    Example:
        >>> is_private_ip("192.168.1.1")
        True
        >>> is_private_ip("8.8.8.8")
        False
    """
    import ipaddress
    
    try:
        ip_obj = ipaddress.ip_address(ip)
        return ip_obj.is_private
    except ValueError:
        return False


def get_client_info(request: Request) -> dict:
    """
    Get comprehensive client information
    
    Args:
        request: FastAPI Request object
    
    Returns:
        dict: Client information including IP, headers, etc.
    
    Example:
        >>> info = get_client_info(request)
        >>> logger.info("Request", **info)
    """
    return {
        "ip": get_real_client_ip(request),
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "referer": request.headers.get("Referer"),
        "forwarded_for": request.headers.get("X-Forwarded-For"),
        "real_ip": request.headers.get("X-Real-IP"),
        "is_private": is_private_ip(get_real_client_ip(request))
    }
