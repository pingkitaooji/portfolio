const localHosts = ["127.0.0.1", "localhost"];
const isLocalDevelopment = localHosts.includes(window.location.hostname);

if (isLocalDevelopment) {
  document.querySelectorAll("[data-local-url]").forEach((link) => {
    link.href = link.dataset.localUrl;
  });
}

const slides = Array.from(document.querySelectorAll(".carousel-slide"));
const dotsContainer = document.querySelector("#carouselDots");
const prevButton = document.querySelector("#prevProject");
const nextButton = document.querySelector("#nextProject");
const carousel = document.querySelector(".project-carousel");
let activeSlide = 0;
let carouselTimer = null;

if (slides.length > 0 && dotsContainer && prevButton && nextButton) {
  slides.forEach((slide, index) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.setAttribute("aria-label", `切換到作品 ${index + 1}`);
    dot.addEventListener("click", () => {
      showSlide(index);
      restartCarousel();
    });
    dotsContainer.appendChild(dot);
  });

  prevButton.addEventListener("click", () => {
    showSlide(activeSlide - 1);
    restartCarousel();
  });

  nextButton.addEventListener("click", () => {
    showSlide(activeSlide + 1);
    restartCarousel();
  });

  carousel?.addEventListener("mouseenter", stopCarousel);
  carousel?.addEventListener("mouseleave", startCarousel);

  showSlide(0);
  startCarousel();
}

function showSlide(index) {
  activeSlide = (index + slides.length) % slides.length;
  slides.forEach((slide, slideIndex) => {
    slide.classList.toggle("active", slideIndex === activeSlide);
  });
  Array.from(dotsContainer.children).forEach((dot, dotIndex) => {
    dot.classList.toggle("active", dotIndex === activeSlide);
  });
}

function startCarousel() {
  stopCarousel();
  carouselTimer = window.setInterval(() => {
    showSlide(activeSlide + 1);
  }, 4500);
}

function stopCarousel() {
  if (carouselTimer) {
    window.clearInterval(carouselTimer);
    carouselTimer = null;
  }
}

function restartCarousel() {
  startCarousel();
}
