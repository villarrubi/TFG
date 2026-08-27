"""Validaciones de red para mantener los servicios del TFG en el equipo local."""

from __future__ import annotations

import ipaddress


class UnsafeBindAddressError(ValueError):
    """Indica que se intentó publicar un servicio local en una interfaz remota."""


def es_host_loopback(host: str) -> bool:
    """Devuelve ``True`` si el host solo puede resolver a direcciones loopback."""
    normalized = host.strip().lower()
    if not normalized:
        return False
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        pass

    # No se resuelven nombres arbitrarios: además de evitar esperas DNS,
    # impide que un cambio de resolución convierta un host antes local en remoto.
    return False


def validar_host_local(host: str, *, allow_remote: bool = False) -> str:
    """Valida el bind y exige consentimiento explícito para una interfaz remota."""
    normalized = host.strip()
    if not normalized:
        raise UnsafeBindAddressError("El host no puede estar vacío.")
    if not allow_remote and not es_host_loopback(normalized):
        raise UnsafeBindAddressError(
            "El servicio solo puede escuchar en loopback. Usa 127.0.0.1 o localhost; "
            "para una exposición deliberada añade --allow-remote y protege antes el endpoint."
        )
    return normalized
