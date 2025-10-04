class MapInterface {
  constructor() {
    this.canvas = document.getElementById("mapCanvas");
    this.ctx = this.canvas.getContext("2d");
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;

    // Map state
    this.playerPosition = { x: 0, y: 0 };
    this.objects = [];
    this.statusValues = [];
    this.showGrid = true;
    this.statusPanelCollapsed = true;

    // View state
    this.scale = 1.5;
    this.offsetX = 0;
    this.offsetY = 0;
    this.isDragging = false;
    this.lastMouseX = 0;
    this.lastMouseY = 0;

    // Touch state
    this.touches = {};
    this.lastTouchDistance = 0;

    // Map settings
    this.gridSize = 50;
    this.cellSize = 30;

    // Route state
    this.routeActive = false;
    this.routeData = []; // массив точек маршрута {x, y}

    this.setupCanvas();
    this.setupEventListeners();
    this.initializeUI();
    this.connect();
    this.startRenderLoop();
  }

  setupCanvas() {
    this.resizeCanvas();
    window.addEventListener("resize", () => this.resizeCanvas());
    window.addEventListener("orientationchange", () => {
      // Delay resize to allow orientation change to complete
      setTimeout(() => this.resizeCanvas(), 100);
    });
  }

  resizeCanvas() {
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = window.innerWidth * dpr;
    this.canvas.height = window.innerHeight * dpr;
    this.canvas.style.width = window.innerWidth + "px";
    this.canvas.style.height = window.innerHeight + "px";
    this.ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset transform
    this.ctx.scale(dpr, dpr);
    this.centerView();
  }

  centerView() {
    this.offsetX =
      this.canvas.width / 2 -
      this.playerPosition.x * this.cellSize * this.scale;
    this.offsetY =
      this.canvas.height / 2 -
      this.playerPosition.y * this.cellSize * this.scale;
  }

  initializeUI() {
    // Initialize status panel as collapsed
    const panel = document.getElementById("statusPanel");
    if (this.statusPanelCollapsed) {
      panel.classList.add("collapsed");
    }
  }

  setupEventListeners() {
    // Mouse events for panning and zooming
    this.canvas.addEventListener("mousedown", (e) => {
      this.isDragging = true;
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
    });

    this.canvas.addEventListener("mousemove", (e) => {
      if (this.isDragging) {
        const deltaX = e.clientX - this.lastMouseX;
        const deltaY = e.clientY - this.lastMouseY;
        this.offsetX += deltaX;
        this.offsetY += deltaY;
        this.lastMouseX = e.clientX;
        this.lastMouseY = e.clientY;
      }
    });

    this.canvas.addEventListener("mouseup", () => {
      this.isDragging = false;
    });

    this.canvas.addEventListener("mouseleave", () => {
      this.isDragging = false;
    });

    // Touch events for mobile devices
    this.canvas.addEventListener("touchstart", (e) => {
      e.preventDefault();
      const touches = e.touches;

      if (touches.length === 1) {
        // Single touch - start panning
        this.isDragging = true;
        this.lastMouseX = touches[0].clientX;
        this.lastMouseY = touches[0].clientY;
      } else if (touches.length === 2) {
        // Two fingers - start zooming
        this.isDragging = false;
        const touch1 = touches[0];
        const touch2 = touches[1];
        this.lastTouchDistance = this.getTouchDistance(touch1, touch2);

        // Store touch positions for zoom center calculation
        this.touches.centerX = (touch1.clientX + touch2.clientX) / 2;
        this.touches.centerY = (touch1.clientY + touch2.clientY) / 2;
      }
    });

    this.canvas.addEventListener("touchmove", (e) => {
      e.preventDefault();
      const touches = e.touches;

      if (touches.length === 1 && this.isDragging) {
        // Single touch - panning
        const deltaX = touches[0].clientX - this.lastMouseX;
        const deltaY = touches[0].clientY - this.lastMouseY;
        this.offsetX += deltaX;
        this.offsetY += deltaY;
        this.lastMouseX = touches[0].clientX;
        this.lastMouseY = touches[0].clientY;
      } else if (touches.length === 2) {
        // Two fingers - zooming
        const touch1 = touches[0];
        const touch2 = touches[1];
        const currentDistance = this.getTouchDistance(touch1, touch2);

        if (this.lastTouchDistance > 0) {
          const zoomFactor = currentDistance / this.lastTouchDistance;
          const centerX = this.touches.centerX;
          const centerY = this.touches.centerY;

          // Calculate world position before zoom
          const worldX = (centerX - this.offsetX) / this.scale;
          const worldY = (centerY - this.offsetY) / this.scale;

          // Apply zoom with constraints
          this.scale = Math.max(0.1, Math.min(3, this.scale * zoomFactor));

          // Adjust offset to keep zoom center stable
          this.offsetX = centerX - worldX * this.scale;
          this.offsetY = centerY - worldY * this.scale;
        }

        this.lastTouchDistance = currentDistance;
      }
    });

    this.canvas.addEventListener("touchend", (e) => {
      e.preventDefault();
      this.isDragging = false;
      this.lastTouchDistance = 0;
      this.touches = {};
    });

    this.canvas.addEventListener("touchcancel", (e) => {
      e.preventDefault();
      this.isDragging = false;
      this.lastTouchDistance = 0;
      this.touches = {};
    });

    // Zoom with mouse wheel
    this.canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = 0.1;
      const mouseX = e.clientX;
      const mouseY = e.clientY;

      // Calculate world position before zoom
      const worldX = (mouseX - this.offsetX) / this.scale;
      const worldY = (mouseY - this.offsetY) / this.scale;

      if (e.deltaY < 0) {
        this.scale = Math.min(this.scale * (1 + zoomFactor), 3);
      } else {
        this.scale = Math.max(this.scale * (1 - zoomFactor), 0.1);
      }

      // Adjust offset to keep mouse position stable
      this.offsetX = mouseX - worldX * this.scale;
      this.offsetY = mouseY - worldY * this.scale;
    });

    // Keyboard controls
    document.addEventListener("keydown", (e) => {
      switch (e.key.toLowerCase()) {
        case "g":
          this.toggleGrid();
          break;
        case "s":
          this.toggleStatusPanel();
          break;
      }
    });

    // File upload functionality
    const fileInput = document.getElementById("fileInput");
    const uploadButton = document.getElementById("uploadButton");

    uploadButton.addEventListener("click", () => {
      fileInput.click();
    });

    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        this.uploadFile(file);
      }
    });

    // Status panel toggle
    document
      .getElementById("connectionStatus")
      .addEventListener("click", () => {
        this.toggleStatusPanel();
      });
    
    // Route button
    const routeButton = document.getElementById("routeButton");
    routeButton.addEventListener("click", () => {
      this.toggleRoute();
    });
  }

  toggleRoute() {
    if (!this.routeActive) {
      this.startRoute();
    } else {
      this.finishRoute();
    }
  }


// Модифицируйте метод startRoute
startRoute() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const message = {
            type: "start_route",
        };

        this.ws.send(JSON.stringify(message));
        this.routeActive = true;
        this.routeData = [];
        this.updateRouteButton();
        this.showNotification("Маршрут начат!");

        console.log("Начало маршрута:", message);
    } else {
        this.showNotification("Нет подключения к серверу", true);
    }
}

  finishRoute() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: "finish_route",
      };

      this.ws.send(JSON.stringify(message));
      this.routeActive = false;
      this.updateRouteButton();
      this.showNotification("Маршрут завершен!");

      console.log("Завершение маршрута:", message);
    } else {
      this.showNotification("Нет подключения к серверу", true);
    }
  }

  updateRouteButton() {
    const routeButton = document.getElementById("routeButton");
    if (routeButton) {
      if (this.routeActive) {
        routeButton.textContent = "Закончить";
        routeButton.classList.add("active");
      } else {
        routeButton.textContent = "Начать маршрут";
        routeButton.classList.remove("active");
      }
    }
  }

  addRoutePoint(x, y) {
    if (this.routeActive) {
      this.routeData.push({ x, y });
    }
  }

  drawRoute() {
    if (!this.routeData || this.routeData.length < 2) return;

    this.ctx.strokeStyle = "#a824c9";
    this.ctx.lineWidth = 4 * this.scale;
    this.ctx.lineJoin = "round";
    this.ctx.lineCap = "round";
    this.ctx.setLineDash([]); 
    
    this.ctx.beginPath();
    
    const firstPoint = this.scalePos(this.routeData[0].x, this.routeData[0].y);
    this.ctx.moveTo(firstPoint.x, firstPoint.y);
    
    for (let i = 1; i < this.routeData.length; i++) {
      const point = this.scalePos(this.routeData[i].x, this.routeData[i].y);
      this.ctx.lineTo(point.x, point.y);
    }
    
    this.ctx.stroke();

    if (this.routeData.length > 0) {
      const startPoint = this.scalePos(this.routeData[0].x, this.routeData[0].y);
      this.ctx.fillStyle = "#2ecc71"; 
      this.ctx.beginPath();
      this.ctx.arc(startPoint.x, startPoint.y, 5 * this.scale, 0, Math.PI * 2);
      this.ctx.fill();
      
    }

    // Рисуем конечную точку другим цветом
    if (this.routeData.length > 1) {
      const endPoint = this.scalePos(
        this.routeData[this.routeData.length - 1].x, 
        this.routeData[this.routeData.length - 1].y
      );
      this.ctx.fillStyle = "#e74c3c"; // красный для финиша
      this.ctx.beginPath();
      this.ctx.arc(endPoint.x, endPoint.y, 5 * this.scale, 0, Math.PI * 2);
      this.ctx.fill();
      
    }
  }

  toggleGrid() {
    this.showGrid = !this.showGrid;
  }

  toggleStatusPanel() {
    this.statusPanelCollapsed = !this.statusPanelCollapsed;
    const panel = document.getElementById("statusPanel");
    if (this.statusPanelCollapsed) {
      panel.classList.add("collapsed");
    } else {
      panel.classList.remove("collapsed");
    }
  }

  uploadFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const fileData = e.target.result;
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const message = {
          type: "file_upload",
          content: fileData,
        };
        this.ws.send(JSON.stringify(message));
        console.log(`File uploaded: ${file.name} (${file.size} bytes)`);

        // Show feedback to user
        const uploadButton = document.getElementById("uploadButton");
        const originalText = uploadButton.textContent;
        uploadButton.textContent = "Загружено!";
        uploadButton.style.backgroundColor = "#27ae60";

        setTimeout(() => {
          uploadButton.textContent = originalText;
          uploadButton.style.backgroundColor = "#e67e22";
        }, 2000);
      } else {
        console.error("WebSocket connection is not open");
        alert("Нет подключения к серверу!");
      }
    };

    reader.onerror = () => {
      console.error("Error reading file");
      alert("Ошибка при чтении файла!");
    };

    reader.readAsText(file);
  }

  getTouchDistance(touch1, touch2) {
    const dx = touch1.clientX - touch2.clientX;
    const dy = touch1.clientY - touch2.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  connect() {
    try {
      this.ws = new WebSocket(`ws://${window.location.hostname}:3030`);

      this.ws.onopen = () => {
        console.log("Connected to WebSocket server");
        this.updateConnectionStatus(true);
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (error) {
          console.error("Error parsing message:", error);
        }
      };

      this.ws.onclose = () => {
        console.log("Disconnected from WebSocket server");
        this.updateConnectionStatus(false);

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(
            `Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`
          );
          setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
        }
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    } catch (error) {
      console.error("Failed to connect to WebSocket:", error);
      this.updateConnectionStatus(false);
    }
  }

  handleMessage(data) {
    if (data.type === "file") {
      if (data.filename && data.content) {
        const blob = new Blob([data.content], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } else if (data.playerPosition && data.objects) {
      // Full map data format
      const prevX = this.playerPosition.x;
      const prevY = this.playerPosition.y;
      
      this.playerPosition = data.playerPosition;
      this.objects = data.objects;
      this.statusValues = data.statusValues || [];

      // Автоматически добавляем точку в маршрут при движении
      if (this.routeActive) {
        const distance = Math.sqrt(
          Math.pow(this.playerPosition.x - prevX, 2) + 
          Math.pow(this.playerPosition.y - prevY, 2)
        );
        
        // Добавляем точку только если перемещение значительное
        if (distance > 0.1) {
          this.addRoutePoint(this.playerPosition.x, this.playerPosition.y);
        }
      }

      const messageLine = document.getElementById("messageLine");
      if (data.messageLine) {
        messageLine.textContent = data.messageLine;
      } else {
        messageLine.textContent = "Маячки";
      }
    } else if (data.x !== undefined && data.y !== undefined) {
      // Simple position update
      const prevX = this.playerPosition.x;
      const prevY = this.playerPosition.y;
      
      this.playerPosition = { x: data.x, y: data.y };
      
      // Автоматически добавляем точку в маршрут при движении
      if (this.routeActive) {
        const distance = Math.sqrt(
          Math.pow(this.playerPosition.x - prevX, 2) + 
          Math.pow(this.playerPosition.y - prevY, 2)
        );
        
        // Добавляем точку только если перемещение значительное
        if (distance > 0.5) {
          this.addRoutePoint(this.playerPosition.x, this.playerPosition.y);
        }
      }
    } else if (data.type === "error") {
      console.error("Ошибка сервера:", data.message);
      this.showNotification("Ошибка: " + data.message, true);
    }

    this.updateUI();
  }

  showNotification(message, isError = false) {
    const notification = document.createElement("div");
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: ${isError ? "#e74c3c" : "#27ae60"};
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        z-index: 10000;
        font-family: Arial;
        font-size: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 3000);
  }

  updateConnectionStatus(connected) {
    const statusEl = document.getElementById("connectionStatus");
    if (connected) {
      statusEl.textContent = "Подключен";
      statusEl.className = "connection-status connected";
    } else {
      statusEl.textContent = "Отключен";
      statusEl.className = "connection-status disconnected";
    }
  }

  updateUI() {
    // Update status values panel
    const statusContainer = document.getElementById("statusValues");
    if (this.statusValues.length > 0) {
      statusContainer.innerHTML = this.statusValues
        .map(
          (item) =>
            `<div class="status-item">
          <span class="status-name">${this.escapeHtml(item.name)}</span>
          <span class="status-value">${this.escapeHtml(item.value)}</span>
        </div>`
        )
        .join("");
    } else {
      statusContainer.innerHTML =
        '<div class="status-item"><span>Нет данных</span></div>';
    }

    // Update player info
    document.getElementById(
      "playerPos"
    ).textContent = `(${this.playerPosition.x.toFixed(
      1
    )}, ${this.playerPosition.y.toFixed(1)})`;
    document.getElementById("objectCount").textContent = this.objects.length;
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  startRenderLoop() {
    const render = () => {
      this.draw();
      requestAnimationFrame(render);
    };
    render();
  }

  draw() {
    // Clear canvas
    this.ctx.fillStyle = "#34495e";
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw grid
    if (this.showGrid) {
      this.drawGrid();
    }

    // Draw route (добавляем эту строку)
    this.drawRoute();

    // Draw objects
    this.drawObjects();

    // Draw player
    this.drawPlayer();
  }

  // No context scaling, manually scale positions
  scalePos(x, y) {
    return {
      x: x * this.cellSize * this.scale + this.offsetX,
      y: -y * this.cellSize * this.scale + this.offsetY,
    };
  }

  drawGrid() {
    this.ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    this.ctx.lineWidth = 1;

    const scaledCell = this.cellSize * this.scale;

    // Calculate the first grid line to draw (left/top of canvas)
    const startX = Math.floor(
      this.offsetX % scaledCell === 0 ? 0 : this.offsetX % scaledCell
    );
    const endX = this.canvas.width;
    const startY = Math.floor(
      this.offsetY % scaledCell === 0 ? 0 : this.offsetY % scaledCell
    );
    const endY = this.canvas.height;

    // Vertical lines
    for (let x = startX; x <= endX; x += scaledCell) {
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, this.canvas.height);
      this.ctx.stroke();
    }

    // Horizontal lines
    for (let y = startY; y <= endY; y += scaledCell) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(this.canvas.width, y);
      this.ctx.stroke();
    }
  }

  drawPlayer() {
    const { x, y } = this.scalePos(
      this.playerPosition.x,
      this.playerPosition.y
    );
    const radius = 12 * this.scale;

    // Player circle
    this.ctx.fillStyle = "#e74c3c";
    this.ctx.strokeStyle = "#c0392b";
    this.ctx.lineWidth = 2;
    this.ctx.beginPath();
    this.ctx.arc(x, y, radius, 0, Math.PI * 2);
    this.ctx.fill();
    this.ctx.stroke();

    // Player label
    this.ctx.fillStyle = "#fff";
    this.ctx.font = `${16 * this.scale}px Arial`;
    this.ctx.textAlign = "center";
    this.ctx.fillText("Я", x, y - radius - 10 * this.scale);
    this.ctx.font = `${14 * this.scale}px Arial`;
    this.ctx.fillText(
      `(${this.playerPosition.x.toFixed(1)}, ${this.playerPosition.y.toFixed(
        1
      )})`,
      x,
      y + radius + 14 * this.scale
    );
  }

  drawObjects() {
    const n = this.objects.length;
    this.objects.forEach((obj, i) => {
      const { x, y } = this.scalePos(obj.x, obj.y);
      const radius = 10 * this.scale;

      // HSV rainbow color
      const hue = Math.round((i / Math.max(n, 1)) * 360);
      this.ctx.strokeStyle = `hsl(${hue}, 80%, 35%)`;
      this.ctx.lineWidth = 1;

      // Object name
      this.ctx.fillStyle = "#fff";
      this.ctx.font = `${16 * this.scale}px Arial`;
      this.ctx.textAlign = "center";
      const name = obj.name || "Unknown";
      this.ctx.fillText(name, x, y - radius - 20 * this.scale);

      // Show RSSI if available
      if (obj.rssi !== undefined) {
        this.ctx.font = `${13 * this.scale}px Arial`;
        this.ctx.fillText(
          `${obj.rssi.toFixed(1)}`,
          x,
          y - radius - 5 * this.scale
        );
      }

      // Object circle
      this.ctx.fillStyle = `hsl(${hue}, 80%, 55%)`;
      this.ctx.beginPath();
      this.ctx.arc(x, y, radius, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.stroke();

      // Object position
      this.ctx.fillStyle = "#fff";
      this.ctx.font = `${14 * this.scale}px Arial`;
      this.ctx.fillText(
        `(${obj.x.toFixed(1)}, ${obj.y.toFixed(1)})`,
        x,
        y + radius + 14 * this.scale
      );
    });
  }
}

// Initialize the map interface when the page loads
window.addEventListener("load", () => {
  window.mapInterface = new MapInterface();
});

// Reconnect when page becomes visible again
document.addEventListener("visibilitychange", function () {
  if (
    !document.hidden &&
    window.mapInterface &&
    (!window.mapInterface.ws ||
      window.mapInterface.ws.readyState === WebSocket.CLOSED)
  ) {
    window.mapInterface.connect();
  }
});