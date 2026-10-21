"""Reserve answer space when a request relies on the server's thinking budget."""


def thinking_budget(requested, default, max_tokens, enabled):
    if not enabled:
        return 0
    if requested:
        return int(requested)
    return min(int(default), max(1, int(max_tokens) // 2))
