<div class="scanlines" aria-hidden="true"></div>

<style>
  .scanlines {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 10;
    pointer-events: none;

    background-image: linear-gradient(
      to bottom,
      oklch(0 0 0 / 0.12) 1px,
      transparent 1px
    );
    background-size: 100% 2px;
  }
</style>
