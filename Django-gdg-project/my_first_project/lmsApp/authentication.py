from rest_framework_simplejwt.authentication import JWTAuthentication


class LenientJWTAuthentication(JWTAuthentication):
    """Accept common Authorization header formatting mistakes from API clients."""

    def get_raw_token(self, header):
        if header is None:
            return None

        if isinstance(header, bytes):
            auth_value = header.decode("utf-8", errors="ignore")
        else:
            auth_value = str(header)

        cleaned = auth_value.replace(",", " ").replace(":", " ").strip()
        if not cleaned:
            return None

        parts = [part for part in cleaned.split() if part]
        if len(parts) < 2:
            return None

        scheme = parts[0].lower()
        if scheme != "bearer":
            return None

        token = parts[1]
        return token.encode("utf-8")
