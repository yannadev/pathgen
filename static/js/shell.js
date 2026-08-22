(() => {
    "use strict";

    const sidebar = document.querySelector("[data-sidebar]");
    const overlay = document.querySelector("[data-sidebar-overlay]");
    const openButtons = document.querySelectorAll("[data-sidebar-open]");
    const closeButtons = document.querySelectorAll("[data-sidebar-close]");

    const setSidebarOpen = (isOpen) => {
        if (!sidebar || !overlay) return;
        sidebar.dataset.open = String(isOpen);
        overlay.hidden = !isOpen;
        document.body.classList.toggle("sidebar-open", isOpen);
        openButtons.forEach((button) => {
            button.setAttribute("aria-expanded", String(isOpen));
        });
        if (isOpen) {
            sidebar.querySelector("a, button")?.focus();
        }
    };

    openButtons.forEach((button) => {
        button.addEventListener("click", () => setSidebarOpen(true));
    });
    closeButtons.forEach((button) => {
        button.addEventListener("click", () => setSidebarOpen(false));
    });
    overlay?.addEventListener("click", () => setSidebarOpen(false));

    const desktopQuery = window.matchMedia("(min-width: 768px)");
    desktopQuery.addEventListener("change", (event) => {
        if (event.matches) setSidebarOpen(false);
    });

    document.querySelectorAll("[data-dialog-open]").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            const dialog = document.getElementById(trigger.dataset.dialogOpen);
            if (dialog instanceof HTMLDialogElement) dialog.showModal();
        });
    });

    document.querySelectorAll("[data-dialog-close]").forEach((trigger) => {
        trigger.addEventListener("click", () => trigger.closest("dialog")?.close());
    });

    document.querySelectorAll("dialog").forEach((dialog) => {
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && sidebar?.dataset.open === "true") {
            setSidebarOpen(false);
        }
    });
})();
