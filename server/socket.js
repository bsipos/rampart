const fs = require('fs')
const modifyConfig = require("./config").modifyConfig;
const { verbose, log, warn } = require("./utils");
const { timerStart, timerEnd } = require('./timers');
const { getData } = require("./transformResults");
const { startUp } = require("./startUp");

/**
 * Collect all data (from global.datastore) and send to client
 */
const sendData = () => {
  timerStart("sendData");
  verbose("[sendData]")
  global.io.emit('data', getData());
  timerEnd("sendData");
}

/**
 * Send config over the socket
 */
const sendConfig = () => {
  verbose("[sendConfig]")
  global.io.emit("config", global.config);
}

/**
 * client has just connected
 */
const initialConnection = (socket) => {
  if (!global.config.basecalledPath) {
    verbose("[noBasecalledPath]")
    return socket.emit("noBasecalledPath")
  }
  sendConfig();
  sendData();
}

const setUpIOListeners = (socket) => {
  verbose("[setUpIOListeners]")
  socket.on('config', (newConfig) => {
    try {
      modifyConfig(newConfig);
    } catch (err) {
      console.log(err.message);
      warn("setting of new config FAILED")
      return;
    }
    sendData(); /* as the barcode -> names may have changed */
    sendConfig();
  });
  socket.on('basecalledAndDemuxedPaths', async (clientData) => {
    verbose("[basecalledAndDemuxedPaths]")
    global.config.basecalledPath = clientData.basecalledPath;
    global.config.demuxedPath = clientData.demuxedPath;
    const success = await startUp({emptyDemuxed: true}); // TODO
    if (success) {
      verbose("[basecalledAndDemuxedPaths] success")
      sendConfig();
    } else {
      verbose("[basecalledAndDemuxedPaths] failed")
      setTimeout(() => socket.emit("noBasecalledPath"), 100);
    }
  })
  socket.on("doesPathExist", (data) => {
    return socket.emit("doesPathExist", {
      path: data.path,
      exists: fs.existsSync(data.path)
    });
  });
}

const datastoreUpdated = () => {
  verbose("[datastoreUpdated]");
  sendData();
}
global.TMP_DATASTORE_UPDATED_FUNC = datastoreUpdated;

module.exports = {
  initialConnection,
  setUpIOListeners,
  datastoreUpdated
};
