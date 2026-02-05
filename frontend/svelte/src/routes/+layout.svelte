<script>
  import '../app.css';

  let currentTheme = 'nord';

  function toggleTheme() {
    currentTheme = currentTheme === 'nord' ? 'dark' : 'nord';
    document.documentElement.setAttribute('data-theme', currentTheme);
  }
</script>

<div class="min-h-screen bg-base-100">
  <!-- Navbar -->
  <div class="navbar bg-base-200 shadow-lg">
    <div class="flex-1">
      <a href="/svelte" class="btn btn-ghost text-xl font-bold">
        Labeling Tool
      </a>
    </div>
    <div class="flex-none gap-2">
      <!-- Stats -->
      <div class="stats stats-horizontal shadow bg-base-100">
        <div class="stat py-2 px-4">
          <div class="stat-title text-xs">Videos</div>
          <div class="stat-value text-lg" id="stat-videos">-</div>
        </div>
        <div class="stat py-2 px-4">
          <div class="stat-title text-xs">Frames</div>
          <div class="stat-value text-lg" id="stat-frames">-</div>
        </div>
        <div class="stat py-2 px-4">
          <div class="stat-title text-xs">Labeled</div>
          <div class="stat-value text-lg text-success" id="stat-labeled">-</div>
        </div>
      </div>

      <!-- Theme toggle -->
      <button class="btn btn-ghost btn-circle" on:click={toggleTheme}>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      </button>
    </div>
  </div>

  <!-- Main content -->
  <main class="container mx-auto p-4">
    <slot />
  </main>
</div>
