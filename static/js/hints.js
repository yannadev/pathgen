(() => {
    "use strict";

    document.querySelectorAll("[data-hint-trigger]").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            const input = document.querySelector(
                `[data-hint-used-input="${trigger.dataset.hintTrigger}"]`,
            );
            if (input instanceof HTMLInputElement) input.value = "1";
        });
    });
})();
