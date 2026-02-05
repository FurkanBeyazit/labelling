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

    if (frame) {
      loadFrame();
    }
  }

  let lastFrameId = null;
  $: if (frame && fabricCanvas && frame.frame_id !== lastFrameId) {
    lastFrameId = frame.frame_id;
    loadFrame();
  }

  function loadFrame() {
    if (!fabricCanvas || !frame) return;

    fabricCanvas.clear();
    selectedRect = null;
    canvasLabels = [];

    fabric.Image.fromURL(`/api/frames/${videoId}/${frame.frame_id}/image`, (img) => {
      const containerWidth = canvasContainer.clientWidth;
      const containerHeight = canvasContainer.clientHeight - 280;

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

      // Reload frame
      const frameRes = await fetch(`/api/frames/${videoId}/${frame.frame_id}`);
      const newFrame = await frameRes.json();

      lastFrameId = null;
      frame = newFrame;
      dispatch('update');
    } catch (e) {
      console.error('Auto-label failed:', e);
    }
  }

  async function saveLabels() {
    const labels = getLabelsFromCanvas();

    try {
      await fetch(`/api/frames/${videoId}/${frame.frame_id}/labels`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ labels })
      });

      // Reload frame
      const frameRes = await fetch(`/api/frames/${videoId}/${frame.frame_id}`);
      const newFrame = await frameRes.json();

      lastFrameId = null;
      frame = newFrame;
      dispatch('update');
    } catch (e) {
      console.error('Save failed:', e);
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

<div class="flex flex-col h-full gap-3" bind:this={canvasContainer}>
  <!-- Top Controls -->
  <div class="flex flex-wrap gap-2 items-center">
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
    <button class="btn btn-success btn-sm" on:click={saveLabels}>Save</button>
  </div>

  <!-- Canvas -->
  <div class="flex-1 flex items-center justify-center bg-base-300 rounded-lg overflow-hidden min-h-[250px]">
    <canvas bind:this={canvas}></canvas>
  </div>

  <!-- Labels table -->
  <div class="bg-base-100 rounded-lg overflow-hidden">
    <div class="overflow-x-auto max-h-48">
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
