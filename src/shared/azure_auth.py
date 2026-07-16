"""Credential bootstrap that stays import-safe without live Azure dependencies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CredentialDescriptor:
    """Serializable stand-in for the future Azure credential factory."""

    mode: str
    tenant_id: str
    client_id: str


def create_credential_descriptor(*, tenant_id: str, client_id: str) -> CredentialDescriptor:
    """Return a local-test-safe credential descriptor for downstream adapters."""

    return CredentialDescriptor(mode="oidc-placeholder", tenant_id=tenant_id, client_id=client_id)
