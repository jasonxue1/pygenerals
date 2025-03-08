let socket;
let username;
let room;
let currentState = null;
// 初始选中格子，默认为左上角
let selectedCell = { row: 0, col: 0 };

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
    drawGame();
  });
  socket.on("connect", () => {
    socket.emit("join", { username, room });
  });
  document.getElementById("login").style.display = "none";
  document.getElementById("game").style.display = "block";
  // 初始选中格子设为 (0, 0)
  selectedCell = { row: 0, col: 0 };
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
      // 根据地形绘制背景色
      if (cell.type === 1) {
        ctx.fillStyle = "#666666"; // 山
      } else if (cell.type === 3) {
        ctx.fillStyle = "#FFD700"; // 塔（金色）
      } else {
        ctx.fillStyle = "#ffffff"; // 空地
      }
      ctx.fillRect(c * cellSize, r * cellSize, cellSize, cellSize);
      // 若格子被占领，用半透明色覆盖（自己绿色，其他红色）
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
  // 绘制选中格子边框（蓝色）
  ctx.strokeStyle = "#0000ff";
  ctx.lineWidth = 2;
  ctx.strokeRect(
    selectedCell.col * cellSize,
    selectedCell.row * cellSize,
    cellSize,
    cellSize,
  );
}

document.addEventListener("keydown", (e) => {
  if (!currentState) return;
  const key = e.key;
  // 使用 hjkl 键移动选中格子
  if (key === "h") {
    // 左
    selectedCell.col = Math.max(0, selectedCell.col - 1);
    drawGame();
  } else if (key === "l") {
    // 右
    selectedCell.col = Math.min(currentState.width - 1, selectedCell.col + 1);
    drawGame();
  } else if (key === "k") {
    // 上
    selectedCell.row = Math.max(0, selectedCell.row - 1);
    drawGame();
  } else if (key === "j") {
    // 下
    selectedCell.row = Math.min(currentState.height - 1, selectedCell.row + 1);
    drawGame();
  }
  // 使用 wasp 键发出移动指令（w:上, a:左, s:下, p:右）
  else if (key === "w" || key === "a" || key === "s" || key === "p") {
    socket.emit("move", {
      username,
      from: [selectedCell.row, selectedCell.col],
      direction: key,
    });
  }
});
