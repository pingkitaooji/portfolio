const localHosts = ["127.0.0.1", "localhost"];
const isLocalDevelopment = localHosts.includes(window.location.hostname);

if (isLocalDevelopment) {
  document.querySelectorAll("[data-local-url]").forEach((link) => {
    link.href = link.dataset.localUrl;
  });
}
