<script>
  import { createEventDispatcher } from 'svelte';

  export let frames = [];
  export let selectedFrame = null;
  export let videoId = '';

  const dispatch = createEventDispatcher();

  function selectFrame(frame) {
    dispatch('select', frame);
  }
</script>

<div class="grid grid-cols-2 gap-2">
  {#each frames as frame}
    <div
      class="relative cursor-pointer group rounded-lg overflow-hidden"
      class:ring-2={selectedFrame?.frame_id === frame.frame_id}
      class:ring-primary={selectedFrame?.frame_id === frame.frame_id}
      on:click={() => selectFrame(frame)}
      on:keypress={(e) => e.key === 'Enter' && selectFrame(frame)}
      role="button"
      tabindex="0"
    >
      <img
        src="/api/frames/{videoId}/{frame.frame_id}/image"
        alt="Frame {frame.frame_number}"
        class="w-full aspect-video object-cover bg-base-300"
        loading="lazy"
      />

      <!-- Status badge -->
      <div class="absolute top-1 right-1">
        {#if frame.has_label}
          <span class="badge badge-success badge-xs">Labeled</span>
        {:else}
          <span class="badge badge-warning badge-xs">Pending</span>
        {/if}
      </div>

      <!-- Frame number overlay -->
      <div class="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-xs px-2 py-1">
        Frame {frame.frame_number}
      </div>

      <!-- Hover overlay -->
      <div class="absolute inset-0 bg-primary/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
    </div>
  {:else}
    <p class="col-span-2 text-center text-base-content/50 py-4">
      No frames extracted
    </p>
  {/each}
</div>
