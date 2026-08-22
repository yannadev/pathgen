(() => {
    "use strict";

    const heartbeatUrl = document.body.dataset.heartbeatUrl;
    if (!heartbeatUrl) return;

    const intervalMs = 45_000;
    let lastPingAt = Date.now();

    const getCookie = (name) => {
        const prefix = `${name}=`;
        return document.cookie
            .split(";")
            .map((part) => part.trim())
            .find((part) => part.startsWith(prefix))
            ?.slice(prefix.length) || "";
    };

    const ping = async () => {
        if (document.visibilityState !== "visible") return;
        lastPingAt = Date.now();
        try {
            await fetch(heartbeatUrl, {
                method: "POST",
                credentials: "same-origin",
                keepalive: true,
                headers: {
                    "X-CSRFToken": decodeURIComponent(getCookie("csrftoken")),
                    "X-Requested-With": "XMLHttpRequest"
                }
            });
        } catch {
            // The next interval retries. Tracking must never interrupt learning.
        }
    };

    window.setInterval(ping, intervalMs);
    document.addEventListener("visibilitychange", () => {
        if (
            document.visibilityState === "visible" &&
            Date.now() - lastPingAt >= intervalMs
        ) {
            ping();
        }
    });
})();
