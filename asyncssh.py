# Placeholder for asyncssh dependency used by tests that patch asyncssh.connect.
# The real asyncssh package is not installed, so this minimal module allows
# patches to target "asyncssh.connect" without import-time errors.


async def connect(*args, **kwargs):
    """Placeholder SSH connect coroutine."""
    raise NotImplementedError("asyncssh is not installed; tests must patch this function")


async def run(*args, **kwargs):
    """Placeholder SSH run coroutine."""
    raise NotImplementedError("asyncssh is not installed; tests must patch this function")
