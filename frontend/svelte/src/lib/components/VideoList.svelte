<script>
  import { createEventDispatcher } from 'svelte';

  export let videos = [];
  export let selectedVideo = null;

  const dispatch = createEventDispatcher();

  function selectVideo(video) {
    dispatch('select', video);
  }

  async function deleteVideo(video, event) {
    event.stopPropagation();

    if (!confirm(`Delete "${video.filename}"?\n\nThis will also delete ${video.frames_count} frames and ${video.approved_count} labels.`)) {
      return;
    }

    try {
      await fetch(`/api/videos/${video.video_id}`, { method: 'DELETE' });
      dispatch('refresh');
    } catch (e) {
      console.error('Delete failed:', e);
    }
  }
</script>

<div class="space-y-2">
  {#each videos as video}
    <div
      class="card bg-base-100 cursor-pointer hover:bg-base-300 transition-colors"
      class:ring-2={selectedVideo?.video_id === video.video_id}
      class:ring-primary={selectedVideo?.video_id === video.video_id}
      on:click={() => selectVideo(video)}
      on:keypress={(e) => e.key === 'Enter' && selectVideo(video)}
      role="button"
      tabindex="0"
    >
      <div class="card-body p-3">
        <div class="flex justify-between items-start">
          <div class="flex-1 min-w-0">
            <h3 class="font-medium text-sm truncate" title={video.filename}>
              {video.filename}
            </h3>
            <div class="flex gap-2 mt-1">
              <span class="badge badge-sm badge-ghost">
                {video.frames_count} frames
              </span>
              {#if video.approved_count > 0}
                <span class="badge badge-sm badge-success">
                  {video.approved_count} labeled
                </span>
              {/if}
              {#if video.pending_count > 0}
                <span class="badge badge-sm badge-warning">
                  {video.pending_count} pending
                </span>
              {/if}
            </div>
          </div>
          <button
            class="btn btn-ghost btn-xs btn-square text-error"
            on:click={(e) => deleteVideo(video, e)}
            title="Delete video"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  {:else}
    <p class="text-center text-base-content/50 py-4">No videos uploaded</p>
  {/each}
</div>
