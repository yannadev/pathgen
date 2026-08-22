(() => {
    "use strict";

    const timer = document.querySelector("[data-assessment-timer]");
    const form = document.querySelector("[data-assessment-form]");
    if (!timer || !(form instanceof HTMLFormElement)) return;

    const initialSeconds = Number.parseInt(timer.dataset.remainingSeconds || "0", 10);
    const deadline = Date.now() + Math.max(0, initialSeconds) * 1000;
    const warningDialog = document.getElementById("time-warning-dialog");
    const warningTitle = document.querySelector("[data-time-warning-title]");
    const timedOutInput = form.querySelector("[data-timed-out]");
    const answeredCount = document.querySelector("[data-answered-count]");
    const shownWarnings = new Set();
    let submitted = false;

    const formatTime = (seconds) => {
        const minutes = Math.floor(seconds / 60);
        const remainder = seconds % 60;
        return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
    };

    const showWarning = (seconds) => {
        const threshold = seconds <= 60 ? 60 : 300;
        if (seconds > threshold || shownWarnings.has(threshold)) return;
        shownWarnings.add(threshold);
        if (warningTitle) {
            warningTitle.textContent = threshold === 60
                ? "1 minute remaining"
                : "5 minutes remaining";
        }
        if (warningDialog instanceof HTMLDialogElement && !warningDialog.open) {
            warningDialog.showModal();
        }
    };

    const submitOnTimeout = () => {
        if (submitted) return;
        submitted = true;
        if (timedOutInput instanceof HTMLInputElement) timedOutInput.value = "1";
        form.requestSubmit();
    };

    const renderTimer = () => {
        const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        timer.textContent = formatTime(remaining);
        timer.classList.toggle("text-rose-700", remaining <= 60);
        timer.classList.toggle("dark:text-rose-300", remaining <= 60);
        if (remaining > 0) showWarning(remaining);
        if (remaining === 0) submitOnTimeout();
        return remaining;
    };

    const updateAnsweredCount = () => {
        if (!answeredCount) return;
        const answeredNames = new Set(
            Array.from(form.querySelectorAll("input[type='radio']:checked"), (input) => input.name)
        );
        answeredCount.textContent = String(answeredNames.size);
    };

    form.addEventListener("change", updateAnsweredCount);
    form.addEventListener("submit", () => {
        submitted = true;
        form.querySelectorAll("button[type='submit']").forEach((button) => {
            button.disabled = true;
        });
    });

    updateAnsweredCount();
    if (renderTimer() > 0) {
        const intervalId = window.setInterval(() => {
            if (renderTimer() === 0) window.clearInterval(intervalId);
        }, 250);
        document.addEventListener("visibilitychange", renderTimer);
    }
})();
