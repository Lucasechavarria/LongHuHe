def get_client_ip(request):
    """
    Obtiene la dirección IP real del cliente, manejando proxies (ej. Render/Cloudflare).
    """
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
