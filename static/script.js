let socket;
let username;
let room;
let currentState = null;
// 初始选中格子（默认设为 (0,0)），以及一个标志记录是否已设置家位置
let selectedCell = { row: 0, col: 0 };
let initialHomeSet = false;

function joinGame() {
  username = document.getElementById("username").value;
  room = document.getElementById("room").value;
  if (!username || !room) {
    alert("Please enter username and room!");
    return;
  }
  socket = io();
  socket.on("state", (data) => {
    currentState = data;
    // 初始时设置光标在家的位置（仅一次）
    if (!initialHomeSet) {
      for (let r = 0; r < currentState.height; r++) {
        for (let c = 0; c < currentState.width; c++) {
          let cell = currentState.cells[r][c];
          if (cell.owner === username && cell.is_home) {
            selectedCell = { row: r, col: c };
            initialHomeSet = true;
            break;
          }
        }
        if (initialHomeSet) break;
      }
    }
    drawGame();
  });
  socket.on("connect", () => {
    socket.emit("join", { username, room });
  });
  document.getElementById("login").style.display = "none";
  document.getElementById("game").style.display = "block";
}

function drawGame() {
  if (!currentState) return;
  document.getElementById("turn-info").textContent =
    `Turn: ${currentState.turn}`;
  const canvas = document.getElementById("gameCanvas");
  const ctx = canvas.getContext("2d");
  const cellSize = 20;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 绘制所有格子
  for (let r = 0; r < currentState.height; r++) {
    for (let c = 0; c < currentState.width; c++) {
      const cell = currentState.cells[r][c];
      // 根据地形绘制背景：山、塔、空地
      if (cell.type === 1) {
        ctx.fillStyle = "#666666"; // 山
      } else if (cell.type === 3) {
        ctx.fillStyle = "#FFD700"; // 塔
      } else {
        ctx.fillStyle = "#ffffff"; // 空地
      }
      ctx.fillRect(c * cellSize, r * cellSize, cellSize, cellSize);

      // 如果格子被占领，用半透明色覆盖（己方绿色，敌方红色）
      if (cell.owner) {
        ctx.fillStyle =
          cell.owner === username ? "rgba(0,128,0,0.5)" : "rgba(128,0,0,0.5)";
        ctx.fillRect(c * cellSize, r * cellSize, cellSize, cellSize);
      }

      // 绘制兵力数字
      ctx.fillStyle = "#000000";
      ctx.font = "12px Arial";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(
        cell.army,
        c * cellSize + cellSize / 2,
        r * cellSize + cellSize / 2,
      );

      // 绘制网格边框
      ctx.strokeStyle = "#cccccc";
      ctx.strokeRect(c * cellSize, r * cellSize, cellSize, cellSize);
    }
  }

  // 绘制选中框（蓝色边框）
  ctx.strokeStyle = "#0000ff";
  ctx.lineWidth = 2;
  ctx.strokeRect(
    selectedCell.col * cellSize,
    selectedCell.row * cellSize,
    cellSize,
    cellSize,
  );
}

// 鼠标点击时更新光标位置
document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("gameCanvas");
  canvas.addEventListener("click", (e) => {
    if (!currentState) return;
    const rect = canvas.getBoundingClientRect();
    const cellSize = 20;
    const col = Math.floor((e.clientX - rect.left) / cellSize);
    const row = Math.floor((e.clientY - rect.top) / cellSize);
    selectedCell = { row, col };
    drawGame();
  });
});

document.addEventListener("keydown", (e) => {
  if (!currentState) return;
  const key = e.key.toLowerCase();

  // 使用 IJKL 键仅用于移动光标，不发送移动命令（允许光标移动到山上）
  if (["i", "j", "k", "l"].includes(key)) {
    let newRow = selectedCell.row;
    let newCol = selectedCell.col;
    if (key === "i") {
      newRow = Math.max(0, selectedCell.row - 1);
    } else if (key === "j") {
      newCol = Math.max(0, selectedCell.col - 1);
    } else if (key === "k") {
      newRow = Math.min(currentState.height - 1, selectedCell.row + 1);
    } else if (key === "l") {
      newCol = Math.min(currentState.width - 1, selectedCell.col + 1);
    }
    selectedCell = { row: newRow, col: newCol };
    drawGame();
  }
  // 使用 WASD 键发出移动命令，并更新光标位置（目标为山时不发送命令）
  else if (["w", "a", "s", "d"].includes(key)) {
    let newRow = selectedCell.row;
    let newCol = selectedCell.col;
    if (key === "w") {
      newRow = Math.max(0, selectedCell.row - 1);
    } else if (key === "a") {
      newCol = Math.max(0, selectedCell.col - 1);
    } else if (key === "s") {
      newRow = Math.min(currentState.height - 1, selectedCell.row + 1);
    } else if (key === "d") {
      newCol = Math.min(currentState.width - 1, selectedCell.col + 1);
    }
    // 如果目标为山，则不发送移动指令，也不更新光标位置
    if (currentState.cells[newRow][newCol].type === 1) {
      return;
    }
    socket.emit("move", {
      username,
      from: [selectedCell.row, selectedCell.col],
      direction: key,
    });
    selectedCell = { row: newRow, col: newCol };
    drawGame();
  }
});
