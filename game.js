// --- GAME STATE INITIALIZATION ---
let currentLevel = 0;
let startTime = 0;
let lastMoveTime = 0;
let gameActive = false;
let animationFrameId;

// DOM References
const glitch = document.getElementById('glitch-target');
const levelImg = document.getElementById('level-img');
const timerBar = document.getElementById('timer-bar');
const hudSector = document.getElementById('sector-num');

// --- CORE FUNCTIONS ---
function startGame() {
    currentLevel = 0;
    gameActive = true;
    startTime = Date.now();
    // Apply the glitch texture passed from Python
    glitch.style.backgroundImage = `url('${GLITCH_ASSET}')`;
    loadLevel(0);
    gameLoop();
}

function loadLevel(idx) {
    hudSector.innerText = '0' + (idx + 1);
    levelImg.src = LEVELS[idx];
    moveGlitch();
}

function moveGlitch() {
    lastMoveTime = Date.now();
    
    // Randomize size (smaller = harder)
    // Current settings: 80px to 200px square
    let w = Math.floor(Math.random() * 120) + 80;
    let h = Math.floor(Math.random() * 120) + 80;
    
    // Randomize position within the 700x700 container
    // Ensures it never goes off the edge
    let x = Math.floor(Math.random() * (700 - w));
    let y = Math.floor(Math.random() * (700 - h));

    // Apply new styles
    glitch.style.width = w + 'px';
    glitch.style.height = h + 'px';
    glitch.style.left = x + 'px';
    glitch.style.top = y + 'px';
    glitch.style.display = 'block';
}

function hitGlitch(e) {
    if (!gameActive) return;
    e.stopPropagation(); // STOP the click from reaching the background (which would count as a miss)

    // Visual feedback (White Flash)
    let flash = document.createElement('div');
    flash.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:#fff;z-index:99999;pointer-events:none;';
    document.body.appendChild(flash);
    setTimeout(() => flash.remove(), 50);

    // Next level or Game Over
    currentLevel++;
    if (currentLevel < 9) {
        loadLevel(currentLevel);
    } else {
        endGame();
    }
}

function missClick() {
    if (gameActive) {
        // Visual feedback (Red Flash penalty)
        document.body.style.backgroundColor = '#900';
        setTimeout(() => document.body.style.backgroundColor = '#080808', 50);
        // Immediate teleport penalty
        moveGlitch();
    }
}

function endGame() {
    gameActive = false;
    cancelAnimationFrame(animationFrameId);
    // Calculate final time
    let totalTime = ((Date.now() - startTime) / 1000).toFixed(2);
    // Show Game Over screen
    document.getElementById('time-code').innerText = totalTime;
    document.getElementById('game-over-screen').style.display = 'flex';
}

// --- MAIN GAME LOOP (Runs every frame) ---
function gameLoop() {
    if (!gameActive) return;

    let elapsed = Date.now() - lastMoveTime;
    let timeLeft = MOVE_DELAY_MS - elapsed;
    
    // Update Timer Bar Visuals
    let pct = Math.max(0, (timeLeft / MOVE_DELAY_MS) * 100);
    timerBar.style.width = pct + '%';
    
    // Change color based on urgency
    if (pct < 25) timerBar.style.backgroundColor = '#f00';      // Red = Hurry!
    else if (pct < 50) timerBar.style.backgroundColor = '#ff0'; // Yellow = Warning
    else timerBar.style.backgroundColor = '#0f0';               // Green = Safe

    // Auto-teleport if time runs out
    if (elapsed > MOVE_DELAY_MS) {
        moveGlitch();
    }

    animationFrameId = requestAnimationFrame(gameLoop);
}

// --- AUTO-START ---
// Give the browser 500ms to load images before starting the timer
setTimeout(startGame, 500);

// --- EVENT LISTENERS ---
// Assign click handlers here to keep HTML clean
document.getElementById('level-img').onmousedown = missClick;
document.getElementById('glitch-target').onmousedown = hitGlitch;