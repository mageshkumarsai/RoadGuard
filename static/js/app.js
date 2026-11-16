// RoadGuard shared browser enhancements and Progressive Web App installation.
(function () {
  "use strict";

  // The root-level endpoint gives the worker scope over the whole application.
  // Browsers allow service workers on HTTPS and localhost (including 127.0.0.1).
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/service-worker.js", { scope: "/" })
        .catch(function (error) {
          console.warn("RoadGuard service worker registration failed:", error);
        });
    });
  }

  const installButton = document.getElementById("pwaInstallButton");
  const installDialog = document.getElementById("pwaInstallDialog");
  const closeDialog = document.getElementById("pwaInstallClose");
  const instructions = document.getElementById("pwaInstallInstructions");
  if (!installButton) return;

  let deferredInstallPrompt = null;
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;

  if (isStandalone) {
    installButton.hidden = true;
  } else {
    installButton.hidden = false;
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    // Keep the browser's prompt until the visitor taps our install control.
    event.preventDefault();
    deferredInstallPrompt = event;
    installButton.hidden = false;
  });

  function showInstallHelp() {
    if (!instructions) return;
    if (isIOS) {
      instructions.innerHTML = "<p class=\"mb-2\">On your iPhone or iPad, use Safari to install RoadGuard:</p>" +
        "<ol class=\"mb-3\"><li>Open this page in <strong>Safari</strong>.</li>" +
        "<li>Tap the <strong>Share</strong> button.</li>" +
        "<li>Scroll down and choose <strong>Add to Home Screen</strong>.</li>" +
        "<li>Tap <strong>Add</strong> to finish.</li></ol>" +
        "<p class=\"text-secondary mb-0\">iPhone installation is started manually from Safari; the automatic install prompt is not available on iOS.</p>";
    } else {
      instructions.innerHTML = "<p class=\"mb-2\">To install RoadGuard on Android:</p>" +
        "<ol class=\"mb-3\"><li>Open this site in <strong>Chrome</strong> or a supported browser.</li>" +
        "<li>Open the browser menu (three dots).</li>" +
        "<li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li></ol>" +
        "<p class=\"text-secondary mb-0\">Installation requires the deployed site to use HTTPS. The local development address is supported for testing on this computer only.</p>";
    }
    if (installDialog && typeof installDialog.showModal === "function") {
      installDialog.showModal();
    } else {
      window.alert(isIOS
        ? "In Safari, tap Share, then Add to Home Screen."
        : "Open your browser menu and choose Install app or Add to Home screen.");
    }
  }

  installButton.addEventListener("click", async function () {
    if (!deferredInstallPrompt) {
      showInstallHelp();
      return;
    }
    deferredInstallPrompt.prompt();
    try {
      const choice = await deferredInstallPrompt.userChoice;
      if (choice && choice.outcome === "accepted") installButton.hidden = true;
    } catch (error) {
      console.warn("RoadGuard install prompt was not completed:", error);
    }
    deferredInstallPrompt = null;
  });

  if (closeDialog && installDialog) {
    closeDialog.addEventListener("click", function () { installDialog.close(); });
    installDialog.addEventListener("click", function (event) {
      if (event.target === installDialog) installDialog.close();
    });
  }

  window.addEventListener("appinstalled", function () {
    installButton.hidden = true;
    deferredInstallPrompt = null;
  });
})();
