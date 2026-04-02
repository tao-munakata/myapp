import fs from "node:fs";
import path from "node:path";

const rootDir = process.cwd();
const argv = process.argv.slice(2);
const command = argv[0];
const options = parseArgs(argv.slice(1));
const bridgeDir = path.resolve(rootDir, options.dir ?? ".smux-bridge");
const eventsFile = path.join(bridgeDir, "events.jsonl");
const stateFile = path.join(bridgeDir, "state.json");
const cursorsDir = path.join(bridgeDir, "cursors");
const lockDir = path.join(bridgeDir, ".lock");

try {
  switch (command) {
    case "init":
      initBridge();
      break;
    case "send":
      sendMessage();
      break;
    case "read":
      readMessages();
      break;
    case "status":
      printStatus();
      break;
    case "reset":
      resetBridge();
      break;
    default:
      printHelp(1);
  }
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}

function parseArgs(values) {
  const parsed = {};

  for (let index = 0; index < values.length; index += 1) {
    const value = values[index];

    if (!value.startsWith("--")) {
      continue;
    }

    const key = value.slice(2);
    const nextValue = values[index + 1];

    if (nextValue && !nextValue.startsWith("--")) {
      parsed[key] = nextValue;
      index += 1;
      continue;
    }

    parsed[key] = "true";
  }

  return parsed;
}

function initBridge() {
  ensureBridgeFiles();

  console.log(`initialized ${bridgeDir}`);
}

function sendMessage() {
  ensureBridgeFiles();
  const from = requiredOption("from");
  const text = requiredOption("text");
  const to = options.to ?? "all";

  withLock(() => {
    const state = readState();
    const event = {
      id: state.nextId,
      from,
      to,
      text,
      createdAt: new Date().toISOString(),
    };

    fs.appendFileSync(eventsFile, `${JSON.stringify(event)}\n`, "utf8");
    writeState({ nextId: state.nextId + 1 });

    console.log(`sent #${event.id} ${from} -> ${to}`);
  });
}

function readMessages() {
  ensureBridgeFiles();

  const agent = requiredOption("agent");
  const limit = Number.parseInt(options.limit ?? "20", 10);
  const markRead = options["mark-read"] !== "false";
  const cursorFile = path.join(cursorsDir, `${agent}.txt`);
  const currentCursor = readCursor(cursorFile);
  const events = readEvents().filter((event) => {
    if (event.id <= currentCursor) {
      return false;
    }

    if (event.from === agent) {
      return false;
    }

    return event.to === "all" || event.to === agent;
  });
  const selected = events.slice(0, limit);

  if (selected.length === 0) {
    console.log("no unread messages");
    return;
  }

  for (const event of selected) {
    console.log(`#${event.id} ${event.createdAt} ${event.from} -> ${event.to}`);
    console.log(event.text);
    console.log("");
  }

  if (markRead) {
    fs.writeFileSync(cursorFile, String(selected.at(-1).id), "utf8");
  }
}

function printStatus() {
  ensureBridgeFiles();

  const state = readState();
  const events = readEvents();
  const agents = new Set();

  for (const event of events) {
    agents.add(event.from);
    if (event.to !== "all") {
      agents.add(event.to);
    }
  }

  console.log(`bridge: ${bridgeDir}`);
  console.log(`messages: ${events.length}`);
  console.log(`nextId: ${state.nextId}`);

  if (agents.size === 0) {
    console.log("agents: none yet");
    return;
  }

  for (const agent of Array.from(agents).sort()) {
    const cursor = readCursor(path.join(cursorsDir, `${agent}.txt`));
    const unread = events.filter((event) => {
      if (event.id <= cursor || event.from === agent) {
        return false;
      }

      return event.to === "all" || event.to === agent;
    }).length;

    console.log(`${agent}: cursor=${cursor} unread=${unread}`);
  }
}

function resetBridge() {
  fs.rmSync(bridgeDir, { recursive: true, force: true });
  initBridge();
}

function ensureBridgeFiles() {
  fs.mkdirSync(cursorsDir, { recursive: true });

  if (!fs.existsSync(stateFile)) {
    writeState({ nextId: 1 });
  }

  if (!fs.existsSync(eventsFile)) {
    fs.writeFileSync(eventsFile, "", "utf8");
  }
}

function withLock(task) {
  const startedAt = Date.now();

  while (true) {
    try {
      fs.mkdirSync(lockDir);
      break;
    } catch (error) {
      if (!(error instanceof Error) || error.code !== "EEXIST") {
        throw error;
      }

      if (Date.now() - startedAt > 5_000) {
        throw new Error(`timed out waiting for lock ${lockDir}`);
      }

      sleep(25);
    }
  }

  try {
    return task();
  } finally {
    fs.rmSync(lockDir, { recursive: true, force: true });
  }
}

function readState() {
  return JSON.parse(fs.readFileSync(stateFile, "utf8"));
}

function writeState(state) {
  fs.writeFileSync(stateFile, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}

function readEvents() {
  if (!fs.existsSync(eventsFile)) {
    return [];
  }

  const lines = fs
    .readFileSync(eventsFile, "utf8")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  return lines.map((line) => JSON.parse(line));
}

function readCursor(cursorFile) {
  if (!fs.existsSync(cursorFile)) {
    return 0;
  }

  return Number.parseInt(fs.readFileSync(cursorFile, "utf8"), 10) || 0;
}

function requiredOption(name) {
  const value = options[name];

  if (!value) {
    throw new Error(`missing --${name}`);
  }

  return value;
}

function sleep(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

function printHelp(exitCode = 0) {
  console.log(`Usage:
  node scripts/agent-bridge.mjs init [--dir .smux-bridge]
  node scripts/agent-bridge.mjs send --from codex --to claude --text "hello"
  node scripts/agent-bridge.mjs read --agent codex [--mark-read true]
  node scripts/agent-bridge.mjs status
  node scripts/agent-bridge.mjs reset
`);
  process.exit(exitCode);
}
