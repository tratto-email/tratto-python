from typing import Optional

from .._http import HttpClient


class DomainsResource:
    """Methods for the ``/v1/domains`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def add(self, domain: str) -> dict:
        """Register a sender domain and generate DKIM keys.

        Returns the domain object including the DNS records you must add at
        your registrar (SPF, DKIM, DMARC). Call :meth:`verify` once the
        records have propagated.

        Example::

            domain = client.domains.add("acme.com")
            for record in domain["data"]["records"]:
                print(record["type"], record["host"], record["value"])
        """
        return self._http._request("POST", "/v1/domains", body={"domain": domain})

    def list(
        self,
        *,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> dict:
        """List all registered sender domains."""
        return self._http._request(
            "GET",
            "/v1/domains",
            params={"limit": limit, "after": after},
        )

    def get(self, domain_id: str) -> dict:
        """Get domain details, including per-record DNS verification status."""
        return self._http._request("GET", f"/v1/domains/{domain_id}")

    def verify(self, domain_id: str) -> dict:
        """Trigger a DNS verification check for a domain.

        Checks SPF, DKIM, and DMARC TXT records. Returns the updated domain
        object with ``status`` set to ``verified`` or ``failed`` and
        per-record ``verified`` booleans.
        """
        return self._http._request("POST", f"/v1/domains/{domain_id}/verify")

    def delete(self, domain_id: str) -> dict:
        """Remove a domain and revoke its DKIM private key.

        Returns ``{"data": {"id": str, "deletedAt": str}}``.
        """
        return self._http._request("DELETE", f"/v1/domains/{domain_id}")
