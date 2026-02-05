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

  async function handleUpload(event) {
    const files = event.target.files;
    if (!files.length) return;

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        await fetch(`${API_BASE}/videos/upload`, {
          method: 'POST',
          body: formData
        });
      } catch (e) {
        console.error('Upload failed:', e);
      }
    }

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
    loadStats();
  }
</script>

<div class="grid grid-cols-12 gap-4 h-[calc(100vh-140px)]">
  <!-- Left sidebar - Video list -->
  <div class="col-span-3 flex flex-col gap-4">
    <!-- Upload section -->
    <div class="card bg-base-200 shadow-xl">
      <div class="card-body p-4">
        <h2 class="card-title text-sm">Upload Videos</h2>
        <input
          type="file"
          accept=".avi,.mp4,.mov,.mkv,.wmv"
          multiple
          on:change={handleUpload}
          class="file-input file-input-bordered file-input-sm w-full"
        />
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

  <!-- Middle - Frame grid -->
  <div class="col-span-3 flex flex-col gap-4">
    {#if selectedVideo}
      <!-- Extract controls -->
      <div class="card bg-base-200 shadow-xl">
        <div class="card-body p-4">
          <div class="flex gap-2 items-center">
            <select id="extract-interval" class="select select-bordered select-sm flex-1">
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

      <!-- Frame grid -->
      <div class="card bg-base-200 shadow-xl flex-1 overflow-hidden">
        <div class="card-body p-4">
          <h2 class="card-title text-sm">Frames ({frames.length})</h2>
          <div class="overflow-y-auto flex-1">
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

  <!-- Right - Labeling canvas -->
  <div class="col-span-6">
    <div class="card bg-base-200 shadow-xl h-full">
      <div class="card-body p-4">
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
