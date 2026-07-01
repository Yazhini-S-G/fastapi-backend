blacklisted_tokens: set[str] = set()


def blacklist_token(token: str) -> None:
    blacklisted_tokens.add(token)


def is_token_blacklisted(token: str) -> bool:
    return token in blacklisted_tokens
