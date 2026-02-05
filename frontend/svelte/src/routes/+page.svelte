<script>
  import { onMount } from 'svelte';
  import VideoList from '$lib/components/VideoList.svelte';
  import FrameGrid from '$lib/components/FrameGrid.svelte';
  import LabelingCanvas from '$lib/components/LabelingCanvas.svelte';

  let videos = [];
  let selectedVideo = null;
  let frames = [];
  let selectedFrame = null;
  let stats = { total_videos: 0, total_frames: 0, approved_frames: 0 };

  const API_BASE = '/api';

  onMount(async () => {
    await loadVideos();
    await loadStats();
  });

  async function loadVideos() {
    try {
      const res = await fetch(`${API_BASE}/videos`);
      videos = await res.json();
    } catch (e) {
      console.error('Failed to load videos:', e);
    }
  }

  async function loadStats() {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      stats = await res.json();
      // Update navbar stats
      document.getElementById('stat-videos').textContent = stats.total_videos;
      document.getElementById('stat-frames').textContent = stats.total_frames;
      document.getElementById('stat-labeled').textContent = stats.approved_frames;
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  }

  async function selectVideo(video) {
    selectedVideo = video;
    selectedFrame = null;
    try {
      const res = await fetch(`${API_BASE}/videos/${video.video_id}/frames`);
      const data = await res.json();
      frames = data.frames || [];
    } catch (e) {
      console.error('Failed to load frames:', e);
      frames = [];
    }
  }

  async function selectFrame(frame) {
    try {
      const res = await fetch(`${API_BASE}/frames/${selectedVideo.video_id}/${frame.frame_id}`);
      selectedFrame = await res.json();
    } catch (e) {
      console.error('Failed to load frame:', e);
    }
  }

  let uploading = false;
  let uploadProgress = { current: 0, total: 0 };
  let customVideoName = '';

  async function handleUpload(event) {
    const files = Array.from(event.target.files).filter(f =>
      f.name.match(/\.(avi|mp4|mov|mkv|wmv)$/i)
    );
    if (!files.length) return;

    uploading = true;
    uploadProgress = { current: 0, total: files.length };

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append('file', file);

      // Use custom name only for single file upload
      if (customVideoName.trim() && files.length === 1) {
        formData.append('custom_name', customVideoName.trim());
      }

      // Get folder name from path (for folder upload)
      const pathParts = file.webkitRelativePath?.split('/');
      if (pathParts && pathParts.length > 1) {
        formData.append('folder_name', pathParts[0]);
      }

      try {
        await fetch(`${API_BASE}/videos/upload`, {
          method: 'POST',
          body: formData
        });
        uploadProgress.current++;
        uploadProgress = uploadProgress; // trigger reactivity
      } catch (e) {
        console.error('Upload failed:', e);
      }
    }

    uploading = false;
    customVideoName = ''; // Reset custom name
    await loadVideos();
    await loadStats();
    event.target.value = '';
  }

  async function handleExtract() {
    if (!selectedVideo) return;

    const interval = document.getElementById('extract-interval').value;

    try {
      const res = await fetch(`${API_BASE}/videos/${selectedVideo.video_id}/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frame_interval: parseInt(interval) })
      });
      const data = await res.json();
      alert(`Extracted ${data.frames_extracted} frames`);
      await selectVideo(selectedVideo);
      await loadStats();
    } catch (e) {
      console.error('Extract failed:', e);
    }
  }

  async function handleFrameUpdate() {
    // Refresh frame list without losing selection
    if (selectedVideo) {
      const res = await fetch(`${API_BASE}/videos/${selectedVideo.video_id}/frames`);
      const data = await res.json();
      frames = data.frames || [];
    }
    // Note: Don't re-fetch selectedFrame here - the LabelingCanvas
    // already has the updated data and will manage its own state
    loadStats();
  }
</script>

<div class="grid grid-cols-12 gap-4 h-[calc(100vh-140px)]">
  <!-- Left sidebar - Video list (scrollable) -->
  <div class="col-span-3 flex flex-col gap-4 overflow-hidden">
    <!-- Upload section -->
    <div class="card bg-base-200 shadow-xl">
      <div class="card-body p-4">
        <h2 class="card-title text-sm">Upload Videos</h2>

        {#if uploading}
          <div class="flex flex-col gap-2">
            <progress class="progress progress-primary w-full" value={uploadProgress.current} max={uploadProgress.total}></progress>
            <span class="text-xs text-center">{uploadProgress.current} / {uploadProgress.total} videos</span>
          </div>
        {:else}
          <div class="flex flex-col gap-2">
            <!-- Custom name input (optional) -->
            <input
              type="text"
              bind:value={customVideoName}
              placeholder="Custom folder name (optional)"
              class="input input-bordered input-sm w-full"
            />

            <!-- Single/Multiple files -->
            <label class="btn btn-sm btn-outline btn-primary w-full">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Select Video(s)
              <input
                type="file"
                accept=".avi,.mp4,.mov,.mkv,.wmv"
                multiple
                on:change={handleUpload}
                class="hidden"
              />
            </label>

            <!-- Folder upload -->
            <label class="btn btn-sm btn-outline btn-secondary w-full">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              Select Folder
              <input
                type="file"
                accept=".avi,.mp4,.mov,.mkv,.wmv"
                webkitdirectory
                on:change={handleUpload}
                class="hidden"
              />
            </label>
          </div>

          <p class="text-xs opacity-50 mt-1">Custom name applies to single video only</p>
        {/if}
      </div>
    </div>

    <!-- Video list -->
    <div class="card bg-base-200 shadow-xl flex-1 overflow-hidden">
      <div class="card-body p-4">
        <h2 class="card-title text-sm">Videos ({videos.length})</h2>
        <div class="overflow-y-auto flex-1">
          <VideoList
            {videos}
            {selectedVideo}
            on:select={(e) => selectVideo(e.detail)}
            on:refresh={loadVideos}
          />
        </div>
      </div>
    </div>
  </div>

  <!-- Middle - Frame grid (scrollable) -->
  <div class="col-span-3 flex flex-col gap-4 overflow-hidden">
    {#if selectedVideo}
      <!-- Extract controls -->
      <div class="card bg-base-200 shadow-xl shrink-0">
        <div class="card-body p-4">
          <div class="flex gap-2 items-center">
            <select id="extract-interval" class="select select-bordered select-sm flex-1">
              <option value="1">1 sec</option>
              <option value="5">5 sec</option>
              <option value="10" selected>10 sec</option>
              <option value="15">15 sec</option>
              <option value="30">30 sec</option>
            </select>
            <button class="btn btn-primary btn-sm" on:click={handleExtract}>
              Extract Frames
            </button>
          </div>
        </div>
      </div>

      <!-- Frame grid - scrollable -->
      <div class="card bg-base-200 shadow-xl flex-1 min-h-0">
        <div class="card-body p-4 h-full flex flex-col">
          <h2 class="card-title text-sm shrink-0">Frames ({frames.length})</h2>
          <div class="overflow-y-auto flex-1 min-h-0">
            <FrameGrid
              {frames}
              {selectedFrame}
              videoId={selectedVideo.video_id}
              on:select={(e) => selectFrame(e.detail)}
            />
          </div>
        </div>
      </div>
    {:else}
      <div class="card bg-base-200 shadow-xl flex-1">
        <div class="card-body items-center justify-center">
          <p class="text-base-content/50">Select a video to view frames</p>
        </div>
      </div>
    {/if}
  </div>

  <!-- Right - Labeling canvas (FIXED - no scroll) -->
  <div class="col-span-6 overflow-hidden">
    <div class="card bg-base-200 shadow-xl h-full">
      <div class="card-body p-4 h-full overflow-hidden">
        {#if selectedFrame}
          <LabelingCanvas
            frame={selectedFrame}
            videoId={selectedVideo.video_id}
            on:update={handleFrameUpdate}
          />
        {:else}
          <div class="flex items-center justify-center h-full">
            <p class="text-base-content/50">Select a frame to start labeling</p>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>
