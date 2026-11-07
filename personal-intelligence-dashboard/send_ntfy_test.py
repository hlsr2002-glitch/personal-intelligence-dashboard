#!/usr/bin/env python3
"""One-off neutral ntfy check; deliberately does not run financial rules."""

import os
import sys

from ntfy_utils import send_test_notification


if __name__ == "__main__":
    if not send_test_notification(os.environ.get("NTFY_TOPIC")):
        print("Notificação de teste não enviada; confirma o segredo NTFY_TOPIC.", file=sys.stderr)
        raise SystemExit(1)
    print("Notificação de teste aceite pelo ntfy.")
