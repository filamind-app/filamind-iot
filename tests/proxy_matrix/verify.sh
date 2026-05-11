#!/bin/bash
# Verify the three filamind-iot transports work through whatever proxy
# is listening on http://localhost:$1.
#
# Exits 0 on full pass; nonzero with a diagnostic on the first failure.

set -uo pipefail
PROXY_URL="${1:-http://127.0.0.1:8080}"
fail=0

# 1. WebSocket — must return 101 + Connection: Upgrade.
ws_resp=$(curl -sS -i -m 10 --http1.1 \
    -H 'Connection: Upgrade' \
    -H 'Upgrade: websocket' \
    -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
    -H 'Sec-WebSocket-Version: 13' \
    "$PROXY_URL/websocket" 2>&1 | tr -d '\r' | head -20)
if echo "$ws_resp" | grep -q '^HTTP/1.1 101'; then
    if echo "$ws_resp" | grep -iq '^Connection: Upgrade'; then
        echo "PASS  websocket: 101 Switching Protocols + Connection: Upgrade"
    else
        echo "FAIL  websocket: 101 OK but Connection header is wrong"
        echo "$ws_resp" | sed 's/^/      | /'
        fail=1
    fi
else
    echo "FAIL  websocket: did NOT receive 101"
    echo "$ws_resp" | sed 's/^/      | /'
    fail=1
fi

# 2. Long-poll — must return 200 with JSON within 30s.
lp_resp=$(curl -sS -i -m 30 "$PROXY_URL/longpolling/poll" 2>&1 | tr -d '\r')
if echo "$lp_resp" | head -1 | grep -q '^HTTP/1.1 200'; then
    body=$(echo "$lp_resp" | awk 'BEGIN{b=0}/^$/{b=1;next}b{print}')
    if echo "$body" | grep -q '"channel"'; then
        echo "PASS  longpoll:  200 + JSON body"
    else
        echo "FAIL  longpoll:  200 but body lacks JSON"
        echo "$body" | sed 's/^/      | /'
        fail=1
    fi
else
    echo "FAIL  longpoll:  did NOT receive 200"
    echo "$lp_resp" | head -10 | sed 's/^/      | /'
    fail=1
fi

# 3. Short-poll — must return 200 with JSON immediately.
sp_resp=$(curl -sS -i -m 5 "$PROXY_URL/iot/poll" 2>&1 | tr -d '\r')
if echo "$sp_resp" | head -1 | grep -q '^HTTP/1.1 200'; then
    body=$(echo "$sp_resp" | awk 'BEGIN{b=0}/^$/{b=1;next}b{print}')
    if echo "$body" | grep -q '"commands"'; then
        echo "PASS  shortpoll: 200 + JSON body"
    else
        echo "FAIL  shortpoll: 200 but body lacks JSON"
        echo "$body" | sed 's/^/      | /'
        fail=1
    fi
else
    echo "FAIL  shortpoll: did NOT receive 200"
    echo "$sp_resp" | head -10 | sed 's/^/      | /'
    fail=1
fi

exit $fail
