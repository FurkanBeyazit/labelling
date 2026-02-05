<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';

  export let frame = null;
  export let videoId = '';

  const dispatch = createEventDispatcher();

  let canvasContainer;
  let canvas;
  let fabricCanvas;
  let classes = [];
  let selectedClass = 0;
  let confidenceThreshold = 0.35;
  let isDrawing = false;
  let startX, startY;
  let currentRect;
  let selectedRect = null;
  let canvasLabels = []; // Track labels in canvas
  let saveStatus = ''; // '', 'saving', 'saved'
  let zoomLevel = 1;
  let isPanning = false;
  let lastPosX, lastPosY;

  const CLASS_COLORS = [
    '#FF0000', '#0000FF', '#FFFF00', '#00FF00', '#800080', '#FFA500',
    '#00FFFF', '#8B4513', '#CCCCCC', '#FFC0CB', '#32CD32', '#FFD700'
  ];

  onMount(async () => {
    if (!window.fabric) {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.1/fabric.min.js';
      script.onload = initCanvas;
      document.head.appendChild(script);
    } else {
      initCanvas();
    }

    try {
      const res = await fetch('/api/classes');
      classes = await res.json();
    } catch (e) {
      console.error('Failed to load classes:', e);
    }
  });

  onDestroy(() => {
    if (fabricCanvas) {
      fabricCanvas.dispose();
    }
  });

  function initCanvas() {
    fabricCanvas = new fabric.Canvas(canvas, {
      selection: false
    });

    fabricCanvas.on('mouse:down', onMouseDown);
    fabricCanvas.on('mouse:move', onMouseMove);
    fabricCanvas.on('mouse:up', onMouseUp);
    fabricCanvas.on('selection:created', onSelectionChange);
    fabricCanvas.on('selection:updated', onSelectionChange);
    fabricCanvas.on('selection:cleared', () => { selectedRect = null; });
    fabricCanvas.on('object:modified', updateCanvasLabels);
    fabricCanvas.on('object:moving', onObjectMoving);
    fabricCanvas.on('object:scaling', onObjectMoving);
    fabricCanvas.on('mouse:wheel', onMouseWheel);

    if (frame) {
      loadFrame();
    }
  }

  // Zoom with mouse wheel
  function onMouseWheel(opt) {
    const delta = opt.e.deltaY;
    let zoom = fabricCanvas.getZoom();
    zoom *= 0.999 ** delta;

    // Limit zoom
    if (zoom > 5) zoom = 5;
    if (zoom < 0.5) zoom = 0.5;

    // Zoom to mouse pointer position
    fabricCanvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom);
    zoomLevel = zoom;

    opt.e.preventDefault();
    opt.e.stopPropagation();
  }

  // Reset zoom
  function resetZoom() {
    fabricCanvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
    zoomLevel = 1;
  }

  let lastFrameId = null;
  let loadingFrameId = null; // Track which frame is currently loading

  $: if (frame && fabricCanvas && frame.frame_id !== lastFrameId) {
    lastFrameId = frame.frame_id;
    loadFrame();
  }

  function loadFrame() {
    if (!fabricCanvas || !frame) return;

    const currentFrameId = frame.frame_id;
    loadingFrameId = currentFrameId;

    // Clear canvas immediately
    fabricCanvas.clear();
    selectedRect = null;
    canvasLabels = [];

    // Reset zoom when loading new frame
    fabricCanvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
    zoomLevel = 1;

    fabric.Image.fromURL(`/api/frames/${videoId}/${frame.frame_id}/image`, (img) => {
      // Check if we're still supposed to show this frame (prevent race condition)
      if (loadingFrameId !== currentFrameId) {
        return; // Another frame started loading, abort this one
      }

      // Clear canvas again inside callback to prevent duplicates
      fabricCanvas.clear();

      const containerWidth = canvasContainer.clientWidth - 20;
      const containerHeight = canvasContainer.clientHeight - 200;

      const scale = Math.min(
        containerWidth / img.width,
        containerHeight / img.height,
        1
      );

      fabricCanvas.setWidth(img.width * scale);
      fabricCanvas.setHeight(img.height * scale);

      fabricCanvas.setBackgroundImage(img, fabricCanvas.renderAll.bind(fabricCanvas), {
        scaleX: scale,
        scaleY: scale
      });

      if (frame.labels) {
        frame.labels.forEach((label) => {
          addBboxToCanvas(label);
        });
      }
      updateCanvasLabels();
    }, { crossOrigin: 'anonymous' });
  }

  function addBboxToCanvas(label) {
    const canvasWidth = fabricCanvas.getWidth();
    const canvasHeight = fabricCanvas.getHeight();

    const left = (label.x_center - label.width / 2) * canvasWidth;
    const top = (label.y_center - label.height / 2) * canvasHeight;
    const width = label.width * canvasWidth;
    const height = label.height * canvasHeight;

    const color = CLASS_COLORS[label.class_id] || '#FF0000';

    // Create label text
    const confText = label.confidence ? ` ${Math.round(label.confidence * 100)}%` : '';
    const text = new fabric.Text(`${label.class_name}${confText}`, {
      left: left,
      top: top - 16,
      fontSize: 12,
      fill: '#fff',
      backgroundColor: color,
      padding: 2,
      selectable: false,
      evented: false
    });

    const rect = new fabric.Rect({
      left,
      top,
      width,
      height,
      fill: 'transparent',
      stroke: color,
      strokeWidth: 2,
      selectable: true,
      hasControls: true,
      cornerColor: color,
      cornerSize: 8,
      transparentCorners: false,
      labelData: { ...label },
      labelText: text
    });

    fabricCanvas.add(text);
    fabricCanvas.add(rect);
  }

  function updateCanvasLabels() {
    if (!fabricCanvas) return;

    const labels = [];
    const rects = fabricCanvas.getObjects('rect');

    rects.forEach((rect, idx) => {
      if (rect.labelData) {
        labels.push({
          index: idx,
          ...rect.labelData,
          rect: rect
        });
      }
    });

    canvasLabels = labels;
  }

  function onSelectionChange(e) {
    const obj = e.selected?.[0];
    if (obj && obj.type === 'rect' && obj.labelData) {
      selectedRect = obj;
      selectedClass = obj.labelData.class_id;
    }
    updateCanvasLabels();
  }

  function onObjectMoving(e) {
    const obj = e.target;
    if (obj && obj.type === 'rect' && obj.labelText) {
      obj.labelText.set({
        left: obj.left,
        top: obj.top - 16
      });
      fabricCanvas.renderAll();
    }
  }

  function onMouseDown(opt) {
    // Pan with Alt key or middle mouse button
    if (opt.e.altKey || opt.e.button === 1) {
      isPanning = true;
      lastPosX = opt.e.clientX;
      lastPosY = opt.e.clientY;
      fabricCanvas.selection = false;
      return;
    }

    if (opt.target) return;

    isDrawing = true;
    const pointer = fabricCanvas.getPointer(opt.e);
    startX = pointer.x;
    startY = pointer.y;

    currentRect = new fabric.Rect({
      left: startX,
      top: startY,
      width: 0,
      height: 0,
      fill: 'transparent',
      stroke: CLASS_COLORS[selectedClass],
      strokeWidth: 2,
      selectable: false
    });

    fabricCanvas.add(currentRect);
  }

  function onMouseMove(opt) {
    // Handle panning
    if (isPanning) {
      const vpt = fabricCanvas.viewportTransform;
      vpt[4] += opt.e.clientX - lastPosX;
      vpt[5] += opt.e.clientY - lastPosY;
      lastPosX = opt.e.clientX;
      lastPosY = opt.e.clientY;
      fabricCanvas.requestRenderAll();
      return;
    }

    if (!isDrawing || !currentRect) return;

    const pointer = fabricCanvas.getPointer(opt.e);
    const width = pointer.x - startX;
    const height = pointer.y - startY;

    currentRect.set({
      width: Math.abs(width),
      height: Math.abs(height),
      left: width < 0 ? pointer.x : startX,
      top: height < 0 ? pointer.y : startY
    });

    fabricCanvas.renderAll();
  }

  function onMouseUp() {
    // End panning
    if (isPanning) {
      isPanning = false;
      fabricCanvas.selection = false;
      return;
    }

    if (!isDrawing || !currentRect) return;

    isDrawing = false;

    if (currentRect.width < 10 || currentRect.height < 10) {
      fabricCanvas.remove(currentRect);
      currentRect = null;
      return;
    }

    const className = classes[selectedClass]?.class_name || `class_${selectedClass}`;
    const color = CLASS_COLORS[selectedClass];

    // Create label text for new box
    const text = new fabric.Text(className, {
      left: currentRect.left,
      top: currentRect.top - 16,
      fontSize: 12,
      fill: '#fff',
      backgroundColor: color,
      padding: 2,
      selectable: false,
      evented: false
    });

    currentRect.set({
      selectable: true,
      hasControls: true,
      cornerColor: color,
      cornerSize: 8,
      transparentCorners: false,
      labelData: {
        class_id: selectedClass,
        class_name: className,
        confidence: null,
        source: 'manual'
      },
      labelText: text
    });

    fabricCanvas.add(text);
    fabricCanvas.renderAll();
    currentRect = null;
    updateCanvasLabels();
  }

  function getLabelsFromCanvas() {
    const labels = [];
    const canvasWidth = fabricCanvas.getWidth();
    const canvasHeight = fabricCanvas.getHeight();

    fabricCanvas.getObjects('rect').forEach(rect => {
      if (!rect.labelData) return;

      const scaleX = rect.scaleX || 1;
      const scaleY = rect.scaleY || 1;

      const x_center = (rect.left + (rect.width * scaleX) / 2) / canvasWidth;
      const y_center = (rect.top + (rect.height * scaleY) / 2) / canvasHeight;
      const width = (rect.width * scaleX) / canvasWidth;
      const height = (rect.height * scaleY) / canvasHeight;

      labels.push({
        class_id: rect.labelData.class_id,
        class_name: rect.labelData.class_name,
        x_center,
        y_center,
        width,
        height,
        confidence: rect.labelData.confidence,
        source: rect.labelData.source || 'manual'
      });
    });

    return labels;
  }

  async function autoLabel() {
    try {
      await fetch(`/api/frames/${videoId}/${frame.frame_id}/auto-label`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confidence_threshold: confidenceThreshold })
      });

      // Reload frame data and canvas
      const frameRes = await fetch(`/api/frames/${videoId}/${frame.frame_id}`);
      const newFrame = await frameRes.json();

      // Update frame labels directly without triggering reactive twice
      frame.labels = newFrame.labels;

      // Force reload canvas with new labels
      lastFrameId = null;
      loadFrame();

      dispatch('update');
    } catch (e) {
      console.error('Auto-label failed:', e);
    }
  }

  async function saveLabels() {
    const labels = getLabelsFromCanvas();
    saveStatus = 'saving';

    try {
      await fetch(`/api/frames/${videoId}/${frame.frame_id}/labels`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ labels })
      });

      // Update frame labels in place (don't reload canvas - labels are already there)
      frame.labels = labels;

      // Notify parent to update frames list
      dispatch('update');

      // Show success
      saveStatus = 'saved';
      setTimeout(() => { saveStatus = ''; }, 2000);
    } catch (e) {
      console.error('Save failed:', e);
      saveStatus = '';
    }
  }

  function deleteSelected() {
    if (selectedRect) {
      if (selectedRect.labelText) {
        fabricCanvas.remove(selectedRect.labelText);
      }
      fabricCanvas.remove(selectedRect);
      selectedRect = null;
      fabricCanvas.renderAll();
      updateCanvasLabels();
    }
  }

  function clearAll() {
    if (confirm('Clear all bounding boxes?')) {
      const rects = fabricCanvas.getObjects('rect');
      rects.forEach(obj => {
        if (obj.labelText) {
          fabricCanvas.remove(obj.labelText);
        }
        fabricCanvas.remove(obj);
      });
      selectedRect = null;
      fabricCanvas.renderAll();
      updateCanvasLabels();
    }
  }

  function selectLabel(label) {
    if (label.rect) {
      fabricCanvas.setActiveObject(label.rect);
      fabricCanvas.renderAll();
      selectedRect = label.rect;
      selectedClass = label.class_id;
    }
  }

  function deleteLabel(label, event) {
    event.stopPropagation();
    if (label.rect) {
      if (label.rect.labelText) {
        fabricCanvas.remove(label.rect.labelText);
      }
      fabricCanvas.remove(label.rect);
      if (selectedRect === label.rect) {
        selectedRect = null;
      }
      fabricCanvas.renderAll();
      updateCanvasLabels();
    }
  }

  function changeClass(label, newClassId, event) {
    event.stopPropagation();
    if (label.rect && label.rect.labelData) {
      const newClass = classes[newClassId];
      const newClassName = newClass?.class_name || `class_${newClassId}`;
      const newColor = CLASS_COLORS[newClassId];

      label.rect.labelData.class_id = newClassId;
      label.rect.labelData.class_name = newClassName;

      label.rect.set({
        stroke: newColor,
        cornerColor: newColor
      });

      // Update text label
      if (label.rect.labelText) {
        const confText = label.rect.labelData.confidence
          ? ` ${Math.round(label.rect.labelData.confidence * 100)}%`
          : '';
        label.rect.labelText.set({
          text: `${newClassName}${confText}`,
          backgroundColor: newColor
        });
      }

      fabricCanvas.renderAll();
      updateCanvasLabels();
    }
  }
</script>

<div class="flex flex-col h-full gap-2 overflow-hidden" bind:this={canvasContainer}>
  <!-- Top Controls - fixed -->
  <div class="flex flex-wrap gap-2 items-center shrink-0">
    <!-- Class selector for new boxes -->
    <div class="join">
      <span class="join-item btn btn-sm no-animation">New Class:</span>
      <select class="select select-bordered select-sm join-item" bind:value={selectedClass}>
        {#each classes as cls}
          <option value={cls.class_id}>{cls.class_name}</option>
        {/each}
      </select>
    </div>

    <!-- Confidence slider -->
    <div class="flex items-center gap-2 bg-base-100 px-3 py-1 rounded-lg">
      <span class="text-xs opacity-70">Conf:</span>
      <input
        type="range"
        min="0.1"
        max="0.9"
        step="0.05"
        bind:value={confidenceThreshold}
        class="range range-xs range-primary w-20"
      />
      <span class="text-xs font-mono w-8">{Math.round(confidenceThreshold * 100)}%</span>
    </div>

    <div class="flex-1"></div>

    <!-- Action buttons -->
    <button class="btn btn-primary btn-sm" on:click={autoLabel}>Auto Label</button>
    <button class="btn btn-error btn-sm" on:click={deleteSelected} disabled={!selectedRect}>Delete</button>
    <button class="btn btn-warning btn-sm" on:click={clearAll}>Clear All</button>
    <button class="btn btn-success btn-sm" on:click={saveLabels} disabled={saveStatus === 'saving'}>
      {#if saveStatus === 'saving'}
        Saving...
      {:else}
        Save
      {/if}
    </button>
    {#if saveStatus === 'saved'}
      <span class="badge badge-success gap-1 animate-pulse">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        Saved!
      </span>
    {/if}
  </div>

  <!-- Canvas - takes remaining space -->
  <div class="flex-1 flex items-center justify-center bg-base-300 rounded-lg overflow-hidden min-h-0 relative">
    <canvas bind:this={canvas}></canvas>

    <!-- Zoom controls overlay -->
    {#if zoomLevel !== 1}
      <div class="absolute bottom-2 left-2 flex items-center gap-2 bg-base-100/90 rounded-lg px-2 py-1 shadow">
        <span class="text-xs font-mono">{Math.round(zoomLevel * 100)}%</span>
        <button class="btn btn-xs btn-ghost" on:click={resetZoom} title="Reset zoom (back to 100%)">
          Reset
        </button>
      </div>
    {/if}

    <!-- Zoom/Pan hint -->
    <div class="absolute bottom-2 right-2 text-xs opacity-50 bg-base-100/70 rounded px-2 py-1">
      Scroll: Zoom | Alt+Drag: Pan
    </div>
  </div>

  <!-- Labels table - fixed height -->
  <div class="bg-base-100 rounded-lg overflow-hidden shrink-0">
    <div class="overflow-x-auto max-h-32">
      <table class="table table-xs table-zebra w-full">
        <thead class="sticky top-0 bg-base-200 z-10">
          <tr>
            <th class="w-8">#</th>
            <th>Class</th>
            <th>Confidence</th>
            <th>Source</th>
            <th class="w-24">Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each canvasLabels as label, i (label.index)}
            <tr
              class="cursor-pointer hover:bg-base-200"
              class:bg-primary={selectedRect === label.rect}
              class:bg-opacity-20={selectedRect === label.rect}
              on:click={() => selectLabel(label)}
            >
              <td>{i + 1}</td>
              <td>
                <select
                  class="select select-xs select-bordered w-full max-w-[120px]"
                  value={label.class_id}
                  on:change={(e) => changeClass(label, parseInt(e.target.value), e)}
                  on:click|stopPropagation
                >
                  {#each classes as cls}
                    <option value={cls.class_id}>{cls.class_name}</option>
                  {/each}
                </select>
              </td>
              <td>
                {#if label.confidence}
                  <span class="badge badge-sm badge-ghost">{Math.round(label.confidence * 100)}%</span>
                {:else}
                  <span class="opacity-50">-</span>
                {/if}
              </td>
              <td>
                <span class="badge badge-xs" class:badge-info={label.source === 'auto'} class:badge-ghost={label.source !== 'auto'}>
                  {label.source || 'manual'}
                </span>
              </td>
              <td>
                <button
                  class="btn btn-ghost btn-xs text-error"
                  on:click={(e) => deleteLabel(label, e)}
                  title="Delete this label"
                >
                  Delete
                </button>
              </td>
            </tr>
          {:else}
            <tr>
              <td colspan="5" class="text-center opacity-50 py-6">
                No labels. Draw boxes or click Auto Label.
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    {#if canvasLabels.length > 0}
      <div class="px-3 py-2 bg-base-200 text-xs flex justify-between">
        <span>Total: {canvasLabels.length} label(s)</span>
        <span class="opacity-70">Click row to select, change class from dropdown</span>
      </div>
    {/if}
  </div>
</div>
