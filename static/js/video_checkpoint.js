(() => {
    "use strict";

    const checkpointVideos = document.querySelectorAll("[data-video-checkpoint]");

    checkpointVideos.forEach((video) => {
        if (!(video instanceof HTMLVideoElement)) return;

        const questionId = video.dataset.questionId;
        const checkpointSeconds = Number(video.dataset.checkpointSeconds);
        const input = document.querySelector(
            `[data-video-checkpoint-input="${questionId}"]`,
        );
        const dialog = document.querySelector(
            `[data-video-checkpoint-dialog="${questionId}"]`,
        );
        const continueButton = document.querySelector(
            `[data-video-checkpoint-continue="${questionId}"]`,
        );
        const status = document.querySelector(
            `[data-video-checkpoint-status="${questionId}"]`,
        );
        if (!input || !Number.isFinite(checkpointSeconds) || checkpointSeconds <= 0) return;

        let pausedAtCheckpoint = false;
        let checkpointReached = input.value === "1";

        const markReached = () => {
            checkpointReached = true;
            input.value = "1";
            if (status) {
                status.textContent = "Video checkpoint complete.";
            }
        };

        video.addEventListener("timeupdate", () => {
            if (checkpointReached || pausedAtCheckpoint || video.currentTime < checkpointSeconds) return;
            pausedAtCheckpoint = true;
            video.pause();
            if (dialog instanceof HTMLDialogElement) {
                dialog.showModal();
            } else {
                markReached();
            }
        });

        continueButton?.addEventListener("click", () => {
            markReached();
            if (dialog instanceof HTMLDialogElement) dialog.close();
            video.play().catch(() => {});
        });
    });
})();
